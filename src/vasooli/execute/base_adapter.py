"""
The channel adapter interface. Every executor implements `.send(event, decision) -> dict`
with the same outcome shape. This is the standard reason this matters: adding SMS or email
as a fallback channel, or swapping the voice vendor, means adding one adapter — never
touching classify/decide logic, and never scattering channel-specific code through the
pipeline.

Outcome shape (all adapters return this):
    {
        "channel": str,
        "succeeded": bool,
        "amount_recovered_inr": float,
        "detail": str,
        ...channel-specific extra fields (e.g. "transcript" for voice)...
    }
"""
from abc import ABC, abstractmethod


class ChannelAdapter(ABC):
    channel_name: str

    @abstractmethod
    def send(self, event, decision) -> dict:
        ...
