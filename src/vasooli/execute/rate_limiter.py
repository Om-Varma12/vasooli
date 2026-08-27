"""
STATUS: stub, deferred, lowest priority of the deferred items (see PROJECT_PLAN.md).

Real WhatsApp Business API and voice/telephony providers have their own throughput limits,
independent of whether your own decision logic is correct. A burst of decisions (e.g. a
batch of mandates all hitting their retry window in the same hour) needs to queue against
the channel's real limits, not just get fired all at once.

Not implemented because a 60-record synthetic batch never gets close to a real provider's
throughput ceiling — this matters for a production deployment, not for the buildathon demo.
Implement as a token-bucket per channel_name when real provider integrations land (Day 6+).
"""


class RateLimiter:
    def __init__(self, channel_name: str, max_per_minute: int):
        self.channel_name = channel_name
        self.max_per_minute = max_per_minute

    def acquire(self) -> bool:
        raise NotImplementedError("Rate limiting deferred — see module docstring.")
