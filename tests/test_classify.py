import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
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


@patch("vasooli.classify.llm_classifier.Groq")
def test_ambiguous_reason_code_falls_through_to_llm_tier_success(mock_groq, monkeypatch):
    """Verify successful classification using Groq mock."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    
    # Configure mock Groq client response
    mock_client = MagicMock()
    mock_groq.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({
        "cause": "bank_downtime",
        "reason": "Temporary gateway response failure from NPCI PSP",
        "confidence": 0.85
    })
    mock_client.chat.completions.create.return_value.choices = [mock_choice]

    event = make_event(reason_code="unclassified_bank_response")
    root_cause, reason, confidence, source = classify(event)

    assert source == "llm"
    assert root_cause == RootCause.BANK_DOWNTIME
    assert confidence == 0.85
    assert "NPCI PSP" in reason


@patch("vasooli.classify.llm_classifier.Groq")
def test_llm_low_confidence_classification(mock_groq, monkeypatch):
    """Verify that low-confidence results are handled correctly."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    
    mock_client = MagicMock()
    mock_groq.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({
        "cause": "insufficient_funds",
        "reason": "Weak signal on balance check failure",
        "confidence": 0.45
    })
    mock_client.chat.completions.create.return_value.choices = [mock_choice]

    event = make_event(reason_code="unclassified_bank_response")
    root_cause, reason, confidence, source = classify(event)

    assert source == "llm"
    assert root_cause == RootCause.INSUFFICIENT_FUNDS
    assert confidence == 0.45
    assert "below threshold" in reason


@patch("vasooli.classify.llm_classifier.Groq")
def test_llm_malformed_json_fallback(mock_groq, monkeypatch):
    """Verify that malformed JSON from the LLM fails open gracefully."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    
    mock_client = MagicMock()
    mock_groq.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = "This is not a JSON object at all."
    mock_client.chat.completions.create.return_value.choices = [mock_choice]

    event = make_event(reason_code="unclassified_bank_response")
    root_cause, reason, confidence, source = classify(event)

    assert source == "llm"
    assert root_cause == RootCause.UNKNOWN
    assert confidence == 0.0
    assert "Parsing failed" in reason


@patch("vasooli.classify.llm_classifier.Groq")
def test_llm_api_error_fallback(mock_groq, monkeypatch):
    """Verify that a Groq API exception fails open gracefully."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    
    mock_client = MagicMock()
    mock_groq.return_value = mock_client
    mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")

    event = make_event(reason_code="unclassified_bank_response")
    root_cause, reason, confidence, source = classify(event)

    assert source == "llm"
    assert root_cause == RootCause.UNKNOWN
    assert confidence == 0.0
    assert "API call failed" in reason


def test_llm_missing_api_key_fallback(monkeypatch):
    """Verify that missing GROQ_API_KEY fails open immediately without making a call."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    event = make_event(reason_code="unclassified_bank_response")
    root_cause, reason, confidence, source = classify(event)

    assert source == "llm"
    assert root_cause == RootCause.UNKNOWN
    assert confidence == 0.0
    assert "missing" in reason
