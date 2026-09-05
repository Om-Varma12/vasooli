"""
Voice escalation policy. Handles DND checks, risk-tier gating, and cost-benefit analysis
to decide if a WhatsApp nudge should be escalated to a voice call.
"""
from ..models import FailureEvent, RootCause
from .cost_gate import assumed_cost_inr

def check_dnd(event: FailureEvent) -> bool:
    """Hard boolean check for DND/consent flags.
    True = voice is allowed to be considered.
    """
    return not event.dnd_flag

def evaluate_voice_escalation(event: FailureEvent, root_cause: RootCause, config: dict):
    """
    Voice eligibility. Gate order is deliberate:
      1. DND — hard stop, checked first, no exceptions.
      2. Risk tier / amount thresholds — from config, tunable.
      3. Cost gate — expected recovery vs. assumed call cost, from config, tunable.
    Returns (should_escalate: bool, human_reason: str, expected_recovery_inr: float | None).
    """
    if not check_dnd(event):
        return False, (
            "Voice blocked: customer has an active DND/consent flag — hard stop, checked "
            "before the cost gate, not config-driven, no exceptions."
        ), None

    # Check historical response rate to avoid spamming voice when it has zero response history
    voice_attempts = event.channel_response_rates.get("voice_attempts", 0)
    voice_successes = event.channel_response_rates.get("voice_successes", 0)
    if voice_attempts >= 2 and voice_successes == 0:
        return False, (
            f"Voice not offered: historical voice response rate is 0% over {voice_attempts} attempts. "
            "Blocking voice to avoid telephony cost with zero expected recovery."
        ), None

    v = config["voice_escalation"]

    if event.customer_risk_tier not in v["eligible_risk_tiers"]:
        return False, (
            f"Voice not offered: customer_risk_tier='{event.customer_risk_tier}' below the "
            f"{v['eligible_risk_tiers']} threshold."
        ), None

    if event.amount_inr < v["min_amount_inr"]:
        return False, (
            f"Voice not offered: amount ₹{event.amount_inr:.0f} below "
            f"₹{v['min_amount_inr']:.0f} minimum ticket size for a call."
        ), None

    prob = v["recovery_probability_by_cause"].get(root_cause.value, 0.0)
    expected_recovery = event.amount_inr * prob
    call_cost = assumed_cost_inr("voice")
    if expected_recovery <= call_cost:
        return False, (
            f"Voice not offered: expected recovery ₹{expected_recovery:.2f} does not clear "
            f"assumed call cost ₹{call_cost:.2f} — cost gate failed."
        ), None

    return True, (
        f"Escalating to Hinglish voice call: expected recovery ₹{expected_recovery:.2f} "
        f"clears call cost, customer is high-value, DND clear."
    ), round(expected_recovery, 2)
