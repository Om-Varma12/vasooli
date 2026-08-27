import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.classify import classify, is_cancellation_intent
from vasooli.classify.rules_classifier import classify_by_rule
from vasooli.models import RootCause
from .conftest_helpers import make_event


def test_cancellation_gate_catches_cancelled_by_user():
    event = make_event(reason_code="mandate_cancelled_by_user")
    assert is_cancellation_intent(event) is True


def test_cancellation_gate_catches_account_closed():
    event = make_event(reason_code="account_closed")
    assert is_cancellation_intent(event) is True


def test_cancellation_gate_does_not_false_positive_on_insufficient_funds():
    event = make_event(reason_code="insufficient_funds")
    assert is_cancellation_intent(event) is False


def test_classify_routes_cancellation_before_rules():
    """A cancellation reason_code must return CANCELLATION_INTENT even though it's not in
    the rule map at all — proves the gate runs first, not as a rule-map entry."""
    event = make_event(reason_code="account_closed")
    root_cause, reason, confidence, source = classify(event)
    assert root_cause == RootCause.CANCELLATION_INTENT
    assert source == "gate"
    assert confidence == 1.0


def test_rule_tier_covers_known_reason_codes():
    known = {
        "insufficient_funds": RootCause.INSUFFICIENT_FUNDS,
        "bank_downtime": RootCause.BANK_DOWNTIME,
        "mandate_expired": RootCause.MANDATE_EXPIRED,
        "risk_block": RootCause.RISK_BLOCK,
        "otp_timeout": RootCause.INSUFFICIENT_FUNDS,
    }
    for reason_code, expected_cause in known.items():
        event = make_event(reason_code=reason_code)
        result = classify_by_rule(event)
        assert result is not None, f"expected a rule match for {reason_code}"
        cause, _ = result
        assert cause == expected_cause


def test_ambiguous_reason_code_falls_through_to_llm_tier():
    event = make_event(reason_code="unclassified_bank_response")
    root_cause, reason, confidence, source = classify(event)
    assert source == "llm"
    # current stub always returns UNKNOWN with 0 confidence — this test documents that,
    # so it FAILS loudly (on purpose) once a real LLM call is wired in, forcing this
    # assertion to be updated rather than silently going stale.
    assert root_cause == RootCause.UNKNOWN
    assert confidence == 0.0
