"""
The rules engine. Loads config/rules_table.yaml and evaluates it for any event that made it
past the guard clauses (guard_clauses.py) unresolved. This file contains no policy numbers
of its own — every threshold it uses comes from the YAML, so tuning behavior is a config
change, not a code deploy. See config/rules_table.yaml for what's actually encoded and why
the NPCI ceiling and DND check are deliberately absent from it.
"""
from pathlib import Path
import yaml
from ..models import FailureEvent, Decision, RootCause, Tier

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "rules_table.yaml"

_cache: dict | None = None


def load_rules(path: Path = CONFIG_PATH) -> dict:
    global _cache
    if _cache is None:
        _cache = yaml.safe_load(path.read_text())
    return _cache


def evaluate(event: FailureEvent, root_cause: RootCause) -> Decision:
    """Called only for events that passed the guard clauses. Looks up root_cause in the
    rules table and builds the Decision; evaluates voice escalation if the matched rule
    calls for it.
    """
    config = load_rules()
    rule = _find_rule(config, root_cause)

    if rule["action"]["tier"] == "retry":
        delays = rule["action"]["retry_delay_minutes_by_attempt"]
        idx = min(event.retry_count_so_far, len(delays) - 1)
        return Decision(
            record_id=event.record_id,
            root_cause=root_cause,
            tier=Tier.RETRY,
            reason=rule["action"]["reason_template"] + f" (attempt {event.retry_count_so_far + 1})",
            retry_after_minutes=delays[idx],
        )

    if rule["action"]["tier"] == "human_handoff":
        return Decision(
            record_id=event.record_id,
            root_cause=root_cause,
            tier=Tier.HUMAN_HANDOFF,
            reason=rule["action"]["reason_template"],
            blocked_by="risk_block_requires_human_review",
        )

    # tier == whatsapp, possibly escalating to voice
    decision = Decision(
        record_id=event.record_id,
        root_cause=root_cause,
        tier=Tier.WHATSAPP,
        reason=rule["action"]["reason_template"],
    )
    if rule["action"].get("then_evaluate_voice_escalation"):
        escalate, escalation_reason, expected_recovery = evaluate_voice_escalation(event, root_cause, config)
        decision.reason += " " + escalation_reason
        if escalate:
            decision.tier = Tier.VOICE
            decision.expected_recovery_inr = expected_recovery
    return decision


def evaluate_voice_escalation(event: FailureEvent, root_cause: RootCause, config: dict | None = None):
    """
    Voice eligibility. Gate order is deliberate:
      1. DND — hard stop, checked first (guard_clauses.check_dnd), no exceptions, not
         config-driven either — see that module's docstring.
      2. Risk tier / amount thresholds — from config, tunable.
      3. Cost gate — expected recovery vs. assumed call cost, from config, tunable.
    Returns (should_escalate: bool, human_reason: str, expected_recovery_inr: float | None).
    """
    from .guard_clauses import check_dnd
    from .cost_gate import assumed_cost_inr

    config = config or load_rules()
    v = config["voice_escalation"]

    if not check_dnd(event):
        return False, (
            "Voice blocked: customer has an active DND/consent flag — hard stop, checked "
            "before the cost gate, not config-driven, no exceptions."
        ), None

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


def _find_rule(config: dict, root_cause: RootCause) -> dict:
    for rule in config["rules"]:
        if rule["match"]["root_cause"] == root_cause.value:
            return rule
    # Falls back to the 'unknown' rule if a root cause has no explicit entry — fail toward
    # the safest generic path (WhatsApp + voice-eligibility check) rather than raising.
    for rule in config["rules"]:
        if rule["match"]["root_cause"] == "unknown":
            return rule
    raise KeyError(f"No rule for root_cause={root_cause.value} and no 'unknown' fallback in config")
