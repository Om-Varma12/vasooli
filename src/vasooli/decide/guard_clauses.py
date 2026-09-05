"""
Guard clauses. These run BEFORE the rules table (rules_engine.py) is even consulted, and
they are Python constants, not config file values, on purpose.

This is the actual compliance story, and it's worth stating precisely: the claim is not
"the rules table usually respects the NPCI retry ceiling." The claim is "the ceiling is
structurally impossible to violate, because it is checked before any config-driven logic
runs at all, in code that a rules-table edit cannot touch." If you ever feel tempted to move
RETRY_CEILING or the DND check into config/rules_table.yaml for consistency — don't. That
consistency would cost you the one sentence that actually matters to a compliance reviewer.

Both guard clauses return a Decision directly (short-circuiting) when they fire, or None
when the event should proceed to the rules table.
"""
from ..models import FailureEvent, Decision, RootCause, Tier

# Mirrors Razorpay's own subscription.halted trigger point (1 original attempt + 3 retries).
# See docs/razorpay_webhook_events.md. Not sourced from config/rules_table.yaml — see module
# docstring for why.
RETRY_CEILING = 3


def check_cancellation(event: FailureEvent, root_cause: RootCause) -> Decision | None:
    """Guard clause #1. Re-checks what the classify-layer cancellation gate already caught —
    intentional duplication, defense in depth for the one decision that must never be wrong.
    """
    if root_cause != RootCause.CANCELLATION_INTENT:
        return None
    return Decision(
        record_id=event.record_id,
        root_cause=root_cause,
        tier=Tier.STOPPED,
        reason=(
            f"Cancellation intent (reason_code='{event.reason_code}'). Routing to human "
            "collections queue instead of retrying or contacting — retrying a customer who "
            "already left is the failure mode this gate exists to prevent."
        ),
        blocked_by="cancellation_intent",
    )


def check_retry_ceiling(event: FailureEvent, root_cause: RootCause) -> Decision | None:
    """Guard clause #2. Hard stop at RETRY_CEILING, unconditionally."""
    if event.retry_count_so_far < RETRY_CEILING:
        return None
    return Decision(
        record_id=event.record_id,
        root_cause=root_cause,
        tier=Tier.HUMAN_HANDOFF,
        reason=(
            f"Retry ceiling reached ({event.retry_count_so_far}/{RETRY_CEILING}), matching "
            "NPCI/Razorpay subscription.halted point. Will not auto-retry a 4th time — "
            "escalating to WhatsApp/voice per the rules table instead."
        ),
    )




def run_guard_clauses(event: FailureEvent, root_cause: RootCause) -> Decision | None:
    """Runs all short-circuiting guard clauses in order. Returns a Decision if one fires,
    else None (meaning: proceed to the rules table).
    """
    for guard in (check_cancellation, check_retry_ceiling, check_chronic_bouncer):
        result = guard(event, root_cause)
        if result is not None:
            return result
    return None


def check_chronic_bouncer(event: FailureEvent, root_cause: RootCause) -> Decision | None:
    """Guard clause #3. Bypasses auto-retry for chronic bouncers (past_bounce_count >= 3)
    to prevent transaction fee waste, but still allows voice escalation if eligible.
    """
    if event.past_bounce_count < 3:
        return None

    if root_cause in (RootCause.INSUFFICIENT_FUNDS, RootCause.BANK_DOWNTIME):
        # We must bypass auto-retry, but we can still escalate to voice
        from .voice_policy import evaluate_voice_escalation
        from .rules_engine import load_rules

        config = load_rules()
        escalate, escalation_reason, expected_recovery = evaluate_voice_escalation(event, root_cause, config)

        tier = Tier.VOICE if escalate else Tier.WHATSAPP
        reason = (
            f"Chronic bouncer (past_bounce_count={event.past_bounce_count} >= 3) with transient cause "
            f"'{root_cause.value}'. Bypassing auto-retry to prevent transaction costs. "
            f"{escalation_reason}"
        )

        return Decision(
            record_id=event.record_id,
            root_cause=root_cause,
            tier=tier,
            reason=reason,
            expected_recovery_inr=expected_recovery if escalate else None,
            blocked_by="chronic_bouncer_escalation",
        )
    return None

