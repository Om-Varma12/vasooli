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
from .voice_policy import evaluate_voice_escalation

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
