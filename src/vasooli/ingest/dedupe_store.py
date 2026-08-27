"""
STATUS: stub, Day 6. Razorpay delivers webhooks at-least-once, retrying failed deliveries
with exponential backoff for 24 hours — so the same event WILL arrive more than once under
normal operation, not just as an edge case. Dedupe on Razorpay's event ID before any
downstream processing, or a slow response under load causes duplicate WhatsApp sends or
duplicate voice calls to the same customer.

Real implementation: Redis SETNX with a short TTL (a few days covers the 24h retry window
with margin), or a DB unique constraint on event_id if you don't want a Redis dependency yet.

    import redis
    r = redis.Redis()

    def already_processed(event_id: str) -> bool:
        return not r.set(f"seen:{event_id}", "1", nx=True, ex=60 * 60 * 24 * 3)  # 3-day TTL
"""

_seen_in_memory = set()  # placeholder only — not durable, not shared across processes


def already_processed(event_id: str) -> bool:
    return event_id in _seen_in_memory


def mark_processed(event_id: str) -> None:
    _seen_in_memory.add(event_id)
