import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from vasooli.execute.whatsapp_adapter import WhatsAppAdapter
from vasooli.models import RootCause, Decision, Tier
from .conftest_helpers import make_event


def test_whatsapp_adapter_simulation_fallback_when_credentials_missing(monkeypatch):
    """Verify that absent Twilio credentials run the simulation fallback."""
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_WHATSAPP_FROM", raising=False)
    monkeypatch.delenv("TWILIO_WHATSAPP_TO", raising=False)
    monkeypatch.delenv("TWILIO_SANDBOX_NUMBER", raising=False)
    monkeypatch.delenv("TEST_NUMBER", raising=False)

    adapter = WhatsAppAdapter()
    event = make_event(amount_inr=500.0)
    decision = Decision(
        record_id=event.record_id,
        root_cause=RootCause.INSUFFICIENT_FUNDS,
        tier=Tier.WHATSAPP,
        reason="test"
    )

    res = adapter.send(event, decision)
    assert res["channel"] == "whatsapp"
    assert "detail" in res
    assert "simulation" in res["detail"]


@patch("vasooli.execute.whatsapp_adapter.Client")
def test_whatsapp_adapter_real_send_success(mock_twilio_client, monkeypatch):
    """Verify that valid credentials send a real message via Twilio."""
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxxx")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenxxxx")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    monkeypatch.setenv("TWILIO_WHATSAPP_TO", "whatsapp:+919999999999")
    monkeypatch.delenv("TWILIO_CONTENT_SID", raising=False)
    monkeypatch.delenv("TWILIO_SANDBOX_NUMBER", raising=False)
    monkeypatch.delenv("TEST_NUMBER", raising=False)

    mock_instance = MagicMock()
    mock_twilio_client.return_value = mock_instance
    mock_msg = MagicMock()
    mock_msg.sid = "SMxxxx"
    mock_instance.messages.create.return_value = mock_msg

    adapter = WhatsAppAdapter()
    event = make_event(amount_inr=500.0)
    decision = Decision(
        record_id=event.record_id,
        root_cause=RootCause.INSUFFICIENT_FUNDS,
        tier=Tier.WHATSAPP,
        reason="test"
    )

    res = adapter.send(event, decision)
    assert res["channel"] == "whatsapp"
    assert res["succeeded"] is True
    assert "SMxxxx" in res["detail"]
    assert res["amount_recovered_inr"] == 0.0

    mock_instance.messages.create.assert_called_once_with(
        from_="whatsapp:+14155238886",
        to="whatsapp:+919999999999",
        body="Hi, your payment of ₹500 to merchant_test didn't go through. Tap to retry or update your payment method: rzp.io/r/xxxx"
    )


@patch("vasooli.execute.whatsapp_adapter.Client")
@patch("vasooli.execute.whatsapp_adapter.dlq_write")
def test_whatsapp_adapter_real_send_api_failure(mock_dlq_write, mock_twilio_client, monkeypatch):
    """Verify that Twilio API exceptions are caught, logged to DLQ, and fail-opened to simulation."""
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxxx")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenxxxx")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    monkeypatch.setenv("TWILIO_WHATSAPP_TO", "whatsapp:+919999999999")
    monkeypatch.delenv("TWILIO_CONTENT_SID", raising=False)
    monkeypatch.delenv("TWILIO_SANDBOX_NUMBER", raising=False)
    monkeypatch.delenv("TEST_NUMBER", raising=False)

    mock_instance = MagicMock()
    mock_twilio_client.return_value = mock_instance
    mock_instance.messages.create.side_effect = Exception("Twilio API rate limit exceeded")

    adapter = WhatsAppAdapter()
    event = make_event(amount_inr=500.0)
    decision = Decision(
        record_id=event.record_id,
        root_cause=RootCause.INSUFFICIENT_FUNDS,
        tier=Tier.WHATSAPP,
        reason="test"
    )

    res = adapter.send(event, decision)
    assert res["channel"] == "whatsapp"
    assert "simulation" in res["detail"]
    mock_dlq_write.assert_called_once_with(
        record_id=event.record_id,
        stage="execute",
        error="Failed to send WhatsApp message via Twilio: Twilio API rate limit exceeded"
    )
