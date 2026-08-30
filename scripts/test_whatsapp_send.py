import sys
from pathlib import Path

# Add src to path so we can import vasooli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.models import FailureEvent, PaymentMethod, Category
from vasooli.orchestrator import run_one
from vasooli.audit.audit_log import AuditLog
from vasooli.enrichment.account_history import record_bounce, get_history

def test_whatsapp_delivery():
    customer_id = "cust_test_whatsapp_456"

    # 1. SETUP: Force the customer to be a "Chronic Bouncer" in the DB
    print(f"Setting up Chronic Bouncer history for {customer_id}...")
    for _ in range(3):
        record_bounce(customer_id, "insufficient_funds")

    # Verify DB state immediately
    history = get_history(customer_id)
    print(f"Verified DB state: past_bounce_count = {history['past_bounce_count']}")

    # 2. Construct the event
    event = FailureEvent(
        record_id="test_whatsapp_real_001",
        merchant_id="merchant_test_123",
        customer_id=customer_id,
        payment_method=PaymentMethod.UPI_AUTOPAY,
        category=Category.SUBSCRIPTION,
        amount_inr=500.0,
        webhook_event="payment.failed",
        reason_code="insufficient_funds",
        retry_count_so_far=0,
        customer_risk_tier="standard",
        dnd_flag=False,
        past_bounce_count=3,
    )

    # 3. Initialize an audit log
    audit = AuditLog()

    print("\n🚀 Starting Full Pipeline Test: Chronic Bouncer -> WhatsApp Send")
    print(f"Event ID: {event.record_id}")
    print("-" * 50)

    try:
        # 4. Run the full pipeline
        result = run_one(event, audit)

        print("\n✅ Pipeline Execution Complete!")
        print(f"Channel Used: {result['channel']}")
        print(f"Execution Detail: {result['detail']}")

        # Print the audit trail to see the decision logic
        print("\n--- Decision Audit Trail ---")
        for entry in audit.for_record(event.record_id):
            print(f"[{entry['step']}] {entry['detail']}")
        print("-" * 50)

        if result['channel'] == 'whatsapp':
            print("\n📱 Result: The system attempted to send a real WhatsApp message!")
            if "SID:" in result['detail']:
                print("✨ SUCCESS: Twilio API accepted the request. Check your phone!")
            else:
                print("⚠️  The system chose WhatsApp, but the API call might have failed (check logs).")
        else:
            print(f"❌ Unexpected Channel: {result['channel']}. The condition was not met.")

    except Exception as e:
        print(f"\n❌ Pipeline crashed: {e}")

if __name__ == "__main__":
    test_whatsapp_delivery()
