import pytest
from unittest.mock import patch, MagicMock
from vasooli.models import FailureEvent, PaymentMethod, Category, RootCause
from vasooli.execute.voice_adapter import VoiceAdapter

def test_voice_adapter_simulation_mode():
    """
    Test that VoiceAdapter falls back to simulation mode when credentials are missing.
    """
    # Mock os.environ to ensure credentials are missing
    with patch("os.environ.get", return_value=None):
        adapter = VoiceAdapter()
        event = FailureEvent(
            record_id="test_sim_001",
            merchant_id="m1",
            customer_id="c1",
            payment_method=PaymentMethod.UPI_AUTOPAY,
            category=Category.SUBSCRIPTION,
            amount_inr=100.0,
            webhook_event="payment.failed",
            reason_code="insufficient_funds",
            retry_count_so_far=0,
            customer_risk_tier="standard",
            dnd_flag=False,
        )

        # We need to mock load_rules because it reads from a YAML file
        with patch("vasooli.execute.voice_adapter.load_rules") as mock_rules:
            mock_rules.return_value = {
                "voice_escalation": {
                    "recovery_probability_by_cause": {"insufficient_funds": 0.5}
                }
            }

            result = adapter.send(event, MagicMock(root_cause=RootCause.INSUFFICIENT_FUNDS))

            # Check that it didn't crash and returned a simulated outcome
            assert "simulation" in result["detail"]
            assert "channel" in result
            assert result["channel"] == "voice"

def test_voice_adapter_real_call_mocked():
    """
    Test that the real call logic is triggered when credentials are set,
    but the Twilio client is mocked to avoid real charges.
    """
    env_vars = {
        "TWILIO_ACCOUNT_SID": "ACxxx",
        "TWILIO_AUTH_TOKEN": "token",
        "TWILIO_VOICE_FROM": "+123456789",
        "VOICE_BASE_URL": "https://test.zrok.io",
        "TEST_NUMBER": "+919876543210",
        "REDIS_URL": "redis://localhost:6379"
    }

    with patch("os.environ.get", side_effect=lambda k, default=None: env_vars.get(k, default)):
        with patch("twilio.rest.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            with patch("redis.Redis.from_url") as mock_redis_url:
                mock_redis = MagicMock()
                mock_redis_url.return_value = mock_redis

                adapter = VoiceAdapter()
                event = FailureEvent(
                    record_id="test_real_001",
                    merchant_id="m1",
                    customer_id="c1",
                    payment_method=PaymentMethod.UPI_AUTOPAY,
                    category=Category.SUBSCRIPTION,
                    amount_inr=100.0,
                    webhook_event="payment.failed",
                    reason_code="insufficient_funds",
                    retry_count_so_far=0,
                    customer_risk_tier="standard",
                    dnd_flag=False,
                )

                with patch("vasooli.execute.voice_adapter.load_rules") as mock_rules:
                    mock_rules.return_value = {
                        "voice_escalation": {
                            "recovery_probability_by_cause": {"insufficient_funds": 0.5}
                        }
                    }

                    result = adapter.send(event, MagicMock(root_cause=RootCause.INSUFFICIENT_FUNDS))

                    # Verify Twilio call was created
                    mock_client.calls.create.assert_called_once()
                    args, kwargs = mock_client.calls.create.call_args
                    assert "url" in kwargs
                    assert "to" in kwargs
                    assert "from_" in kwargs
                    assert "whatsapp" not in kwargs["to"] # Voice call, not WhatsApp
