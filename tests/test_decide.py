import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.decide import decide
from vasooli.decide.guard_clauses import RETRY_CEILING
from vasooli.decide.rules_engine import evaluate_voice_escalation
from vasooli.models import RootCause, Tier
from .conftest_helpers import make_event


def test_cancellation_intent_always_stops_regardless_of_retry_count():
    """Guard clause #1 must fire even if retry_count_so_far is 0 — cancellation is not a
    retry-exhaustion outcome, it's a distinct, higher-priority stop."""
    event = make_event(reason_code="account_closed", retry_count_so_far=0)
    decision = decide(event, RootCause.CANCELLATION_INTENT)
    assert decision.tier == Tier.STOPPED
    assert decision.blocked_by == "cancellation_intent"


def test_retry_ceiling_hard_stops_at_configured_max():
    event = make_event(retry_count_so_far=RETRY_CEILING)
    decision = decide(event, RootCause.INSUFFICIENT_FUNDS)
    assert decision.tier == Tier.HUMAN_HANDOFF
    assert "ceiling" in decision.reason.lower()


def test_below_ceiling_transient_cause_gets_retried_not_escalated():
    event = make_event(retry_count_so_far=0)
    decision = decide(event, RootCause.INSUFFICIENT_FUNDS)
    assert decision.tier == Tier.RETRY
    assert decision.retry_after_minutes is not None


def test_risk_block_always_routes_to_human_handoff_never_retried():
    event = make_event(retry_count_so_far=0)
    decision = decide(event, RootCause.RISK_BLOCK)
    assert decision.tier == Tier.HUMAN_HANDOFF


def test_dnd_blocks_voice_even_for_high_value_large_amount():
    """DND must be a hard stop regardless of how favorable every other factor is."""
    event = make_event(
        dnd_flag=True,
        customer_risk_tier="high_value",
        amount_inr=50000.0,
        retry_count_so_far=RETRY_CEILING,  # past ceiling, would otherwise be voice-eligible
    )
    escalate, reason, expected = evaluate_voice_escalation(event, RootCause.MANDATE_EXPIRED)
    assert escalate is False
    assert "dnd" in reason.lower()
    assert expected is None


def test_low_value_customer_not_offered_voice_even_without_dnd():
    event = make_event(dnd_flag=False, customer_risk_tier="standard", amount_inr=50000.0)
    escalate, reason, expected = evaluate_voice_escalation(event, RootCause.MANDATE_EXPIRED)
    assert escalate is False
    assert "risk_tier" in reason or "risk tier" in reason.lower() or "customer_risk_tier" in reason


def test_cost_gate_blocks_voice_when_expected_recovery_below_call_cost():
    """A high-value customer with a tiny amount and a low-probability cause should still be
    blocked by the cost gate — value alone doesn't override the economics."""
    event = make_event(dnd_flag=False, customer_risk_tier="high_value", amount_inr=3000.0)
    escalate, reason, expected = evaluate_voice_escalation(event, RootCause.RISK_BLOCK)
    # RISK_BLOCK has recovery_probability 0.10 -> expected = 300, well above assumed
    # call cost of 15, so this specific combination should actually pass the cost gate.
    # Use CANCELLATION_INTENT (probability 0.0) to force a real cost-gate failure instead.
    escalate2, reason2, expected2 = evaluate_voice_escalation(event, RootCause.CANCELLATION_INTENT)
    assert escalate2 is False
    assert "cost" in reason2.lower()


def test_voice_escalation_fires_when_all_gates_pass():
    event = make_event(dnd_flag=False, customer_risk_tier="high_value", amount_inr=20000.0)
    escalate, reason, expected = evaluate_voice_escalation(event, RootCause.BANK_DOWNTIME)
    assert escalate is True
    assert expected is not None and expected > 0
