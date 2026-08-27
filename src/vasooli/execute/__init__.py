"""
Public entrypoint for the execute layer: dispatches to the right channel adapter by tier,
gated by a per-channel token-bucket rate limiter.

Rate-limit behaviour: if a channel's bucket is empty, the event is NOT silently dropped.
Instead it is logged and written to the Dead Letter Queue with stage='execute' and
reason='rate_limit_exceeded:<channel>'. This makes rate-limit pressure visible in the DLQ
report rather than silently disappearing from metrics.
"""
import logging
from ..models import Tier
from .retry_adapter import RetryAdapter
from .whatsapp_adapter import WhatsAppAdapter
from .voice_adapter import VoiceAdapter
from .promise_to_pay import HumanHandoffAdapter
from .rate_limiter import make_limiters

_ADAPTERS = {
    Tier.RETRY: RetryAdapter(),
    Tier.WHATSAPP: WhatsAppAdapter(),
    Tier.VOICE: VoiceAdapter(),
    Tier.HUMAN_HANDOFF: HumanHandoffAdapter(),
    Tier.STOPPED: HumanHandoffAdapter(),
}

# One rate limiter per channel, shared across all calls (module-level singleton).
# human_handoff and stopped don't hit external APIs so they bypass the limiter check below.
_RATE_LIMITERS = make_limiters()
_BYPASS_RATE_LIMIT = {Tier.HUMAN_HANDOFF, Tier.STOPPED}


def execute(event, decision) -> dict:
    adapter = _ADAPTERS.get(decision.tier)
    if adapter is None:
        return {
            "channel": "none",
            "succeeded": False,
            "amount_recovered_inr": 0.0,
            "detail": f"Unhandled tier '{decision.tier}' — should not happen, flag this.",
        }

    # Rate-limit check — skip for human_handoff/stopped tiers (no external API call).
    if decision.tier not in _BYPASS_RATE_LIMIT:
        limiter = _RATE_LIMITERS.get(adapter.channel_name)
        if limiter is not None and not limiter.acquire():
            logging.warning(
                f"[rate_limiter] channel={adapter.channel_name} bucket empty "
                f"for record={event.record_id} — routing to DLQ."
            )
            _write_rate_limit_dlq(event, adapter.channel_name)
            return {
                "channel": adapter.channel_name,
                "succeeded": False,
                "amount_recovered_inr": 0.0,
                "detail": (
                    f"Rate limit exceeded for channel '{adapter.channel_name}'. "
                    "Event written to DLQ — retry when bucket refills."
                ),
            }

    return adapter.send(event, decision)


def _write_rate_limit_dlq(event, channel_name: str) -> None:
    """Route a rate-limited event to the Dead Letter Queue without crashing the caller."""
    try:
        from ..audit.dead_letter import write as dlq_write
        dlq_write(
            record_id=event.record_id,
            stage="execute",
            error=f"rate_limit_exceeded:{channel_name}",
        )
    except Exception as exc:
        logging.error(f"[rate_limiter] failed to write DLQ entry: {exc}")
