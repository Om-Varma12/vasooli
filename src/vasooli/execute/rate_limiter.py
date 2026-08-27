"""
Thread-safe token-bucket rate limiter, one instance per channel.

Why a token bucket instead of a simple counter?
  A plain "max N per minute" counter resets hard at every 60-second boundary,
  which means 2N requests can legally fire in two seconds straddling a reset.
  A token bucket smooths this: tokens accumulate at a constant rate (capacity /
  window), so a burst can use the full bucket but then must wait for refill —
  much closer to what real provider APIs actually measure.

Usage:
    limiter = RateLimiter("whatsapp", max_per_minute=60)
    if limiter.acquire():
        adapter.send(event, decision)
    else:
        # caller should back off or route to DLQ

Per-channel defaults are set in CHANNEL_LIMITS below. These are conservative
starting points — tune them to the actual vendor contract once real API
credentials are wired.
"""
import time
import threading


# Conservative defaults — real limits:
#   WhatsApp Business API: 80 msg/sec per phone number (Meta docs)
#   Voice/telephony (Exotel/Twilio): 1–5 CPS depending on tier
#   Retry (Razorpay API): ~100 req/min per key in test mode
CHANNEL_LIMITS: dict[str, int] = {
    "whatsapp": 60,       # per minute — deliberately below Meta's hard cap
    "voice": 10,           # per minute — conservative for telephony CPS limits
    "retry": 60,           # per minute — Razorpay subscription retry endpoint
    "human_handoff": 120,  # effectively unlimited for our volumes; still tracked
}


class RateLimiter:
    """
    Token-bucket rate limiter. Thread-safe via a single Lock.

    tokens      — current token count (float to allow fractional refill)
    capacity    — max tokens (= max_per_minute)
    refill_rate — tokens added per second (= max_per_minute / 60)
    last_refill — monotonic timestamp of last acquire() call, used to
                  calculate how many tokens to add before each check
    """

    def __init__(self, channel_name: str, max_per_minute: int):
        self.channel_name = channel_name
        self.max_per_minute = max_per_minute
        self.capacity = float(max_per_minute)
        self.tokens = self.capacity          # start full
        self.refill_rate = max_per_minute / 60.0   # tokens per second
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens for time elapsed since last call. Called inside the lock."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def acquire(self) -> bool:
        """
        Attempt to consume one token.
        Returns True  — token consumed, caller may proceed.
        Returns False — bucket empty, caller must back off.
        Non-blocking: never sleeps.
        """
        with self._lock:
            self._refill()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    def available(self) -> float:
        """Current token count (informational, for logging/metrics)."""
        with self._lock:
            self._refill()
            return self.tokens

    def __repr__(self) -> str:
        return (
            f"RateLimiter(channel={self.channel_name!r}, "
            f"max_per_minute={self.max_per_minute}, "
            f"available={self.available():.1f})"
        )


def make_limiters() -> dict[str, "RateLimiter"]:
    """Return one RateLimiter per channel, keyed by channel_name."""
    return {name: RateLimiter(name, rpm) for name, rpm in CHANNEL_LIMITS.items()}
