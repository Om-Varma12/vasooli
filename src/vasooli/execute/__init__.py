"""Public entrypoint for the execute layer: dispatches to the right channel adapter by tier."""
from ..models import Tier
from .retry_adapter import RetryAdapter
from .whatsapp_adapter import WhatsAppAdapter
from .voice_adapter import VoiceAdapter
from .promise_to_pay import HumanHandoffAdapter

_ADAPTERS = {
    Tier.RETRY: RetryAdapter(),
    Tier.WHATSAPP: WhatsAppAdapter(),
    Tier.VOICE: VoiceAdapter(),
    Tier.HUMAN_HANDOFF: HumanHandoffAdapter(),
    Tier.STOPPED: HumanHandoffAdapter(),
}


def execute(event, decision) -> dict:
    adapter = _ADAPTERS.get(decision.tier)
    if adapter is None:
        return {"channel": "none", "succeeded": False, "amount_recovered_inr": 0.0,
                 "detail": f"Unhandled tier '{decision.tier}' — should not happen, flag this."}
    return adapter.send(event, decision)
