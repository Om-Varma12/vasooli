import sys
import uuid
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import psycopg2
from vasooli.enrichment.account_history import (
    init_db,
    get_history,
    record_bounce,
    record_outcome,
    get_conn,
    DB_URL
)
from vasooli.models import FailureEvent, PaymentMethod, Category, RootCause, Tier
from vasooli.orchestrator import run_one
from vasooli.audit.audit_log import AuditLog
from .conftest_helpers import make_event


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    """Ensure the database is initialized before testing and clean up test data afterwards."""
    if not DB_URL:
        pytest.skip("DATABASE_URL env var not set. Skipping live DB tests.")

    # Initialize schema
    init_db()

    yield

    # Clean up all test customers
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM account_history WHERE customer_id LIKE 'test_cust_%'")
            conn.commit()
    except Exception as e:
        print(f"Error during test database teardown: {e}")


def test_database_crud_operations():
    """Verify that we can write and read historical data for a test customer."""
    customer_id = f"test_cust_{uuid.uuid4().hex[:8]}"

    # Fetching history for a new customer should return default (zeroed) values
    history = get_history(customer_id)
    assert history["past_bounce_count"] == 0
    assert len(history["past_bounce_reasons"]) == 0
    assert history["last_successful_charge_date"] is None
    assert history["channel_response_rates"]["whatsapp_attempts"] == 0

    # Record first bounce
    record_bounce(customer_id, "insufficient_funds")
    history = get_history(customer_id)
    assert history["past_bounce_count"] == 1
    assert history["past_bounce_reasons"] == ["insufficient_funds"]

    # Record second bounce
    record_bounce(customer_id, "otp_timeout")
    history = get_history(customer_id)
    assert history["past_bounce_count"] == 2
    assert history["past_bounce_reasons"] == ["insufficient_funds", "otp_timeout"]

    # Record channel outcomes
    record_outcome(customer_id, "whatsapp", succeeded=False)
    history = get_history(customer_id)
    assert history["channel_response_rates"]["whatsapp_attempts"] == 1
    assert history["channel_response_rates"]["whatsapp_successes"] == 0

    record_outcome(customer_id, "whatsapp", succeeded=True)
    history = get_history(customer_id)
    assert history["channel_response_rates"]["whatsapp_attempts"] == 2
    assert history["channel_response_rates"]["whatsapp_successes"] == 1
    assert history["last_successful_charge_date"] is not None


def test_chronic_bouncer_retry_guard():
    """Verify that a customer with >= 3 past bounces is escalated straight to WhatsApp instead of retried."""
    customer_id = f"test_cust_{uuid.uuid4().hex[:8]}"

    # Set up 3 bounces in the database
    for _ in range(3):
        record_bounce(customer_id, "insufficient_funds")

    audit = AuditLog()
    event = make_event(
        customer_id=customer_id,
        reason_code="insufficient_funds",
        retry_count_so_far=0,  # normally would trigger retry
        customer_risk_tier="high_value"
    )

    result = run_one(event, audit)

    # Should bypass RETRY and go straight to WHATSAPP due to chronic bouncer status
    assert result["tier"] == "whatsapp"

    # Verify the logged policy decision
    entries = audit.for_record(event.record_id)
    policy_detail = next(e["detail"] for e in entries if e["step"] == "policy")
    assert "chronic bouncer" in policy_detail.lower()

    # Test the policy decision object directly to verify blocked_by metadata
    from vasooli.decide import decide
    decision = decide(event, RootCause.INSUFFICIENT_FUNDS)
    assert decision.tier == Tier.WHATSAPP
    assert decision.blocked_by == "chronic_bouncer_escalation"



def test_voice_escalation_blocked_by_zero_recovery_history():
    """Verify that voice escalation is blocked if a customer has 0% recovery history over >= 2 voice attempts."""
    customer_id = f"test_cust_{uuid.uuid4().hex[:8]}"

    # Set up voice attempts with zero successes in the database
    record_outcome(customer_id, "voice", succeeded=False)
    record_outcome(customer_id, "voice", succeeded=False)

    # Set up one bounce so they bypass the chronic bouncer guard (needs 3 to trigger guard)
    record_bounce(customer_id, "mandate_expired")

    audit = AuditLog()
    # High value & high amount to trigger voice escalation under normal circumstances
    event = make_event(
        customer_id=customer_id,
        reason_code="mandate_expired",
        retry_count_so_far=0,
        amount_inr=5000.0,
        customer_risk_tier="high_value",
        dnd_flag=False
    )

    result = run_one(event, audit)

    # Should normally escalate to VOICE, but should default to WHATSAPP because voice is blocked by 0% history
    assert result["tier"] == "whatsapp"

    # Verify the logged policy decision
    entries = audit.for_record(event.record_id)
    policy_detail = next(e["detail"] for e in entries if e["step"] == "policy")
    assert "voice not offered" in policy_detail.lower()
    assert "historical voice response rate is 0%" in policy_detail.lower()


def test_voice_escalation_allowed_with_successful_history():
    """Verify that voice escalation is allowed if a customer has successful voice history."""
    customer_id = f"test_cust_{uuid.uuid4().hex[:8]}"

    # Set up voice attempts with a success
    record_outcome(customer_id, "voice", succeeded=False)
    record_outcome(customer_id, "voice", succeeded=True)

    # Set up one bounce
    record_bounce(customer_id, "mandate_expired")

    audit = AuditLog()
    # High value & high amount to trigger voice escalation
    event = make_event(
        customer_id=customer_id,
        reason_code="mandate_expired",
        retry_count_so_far=0,
        amount_inr=5000.0,
        customer_risk_tier="high_value",
        dnd_flag=False
    )

    result = run_one(event, audit)

    # Should successfully escalate to VOICE
    assert result["tier"] == "voice"

    # Verify the logged policy decision
    entries = audit.for_record(event.record_id)
    policy_detail = next(e["detail"] for e in entries if e["step"] == "policy")
    assert "escalating to hinglish voice call" in policy_detail.lower()

