import sys
from pathlib import Path

# Add src to path so we can import vasooli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.models import FailureEvent, PaymentMethod, Category
from vasooli.orchestrator import run_one
from vasooli.audit.audit_log import AuditLog

def test_voice_delivery():
    # To trigger a Voice call, we need:
    # 1. A root cause that allows voice escalation (e.g., mandate_expired)
    # 2. High risk tier (high_value)
    # 3. Amount >= 3000
    # 4. DND flag = False

    event = FailureEvent(
        record_id="test_voice_chronic_001",
        merchant_id="merchant_test_123",
        customer_id="cust_voice_chronic_999", # New ID to avoid bad history
        payment_method=PaymentMethod.UPI_AUTOPAY,
        category=Category.SUBSCRIPTION,
        amount_inr=10000.0,              # High amount
        webhook_event="payment.failed",
        reason_code="insufficient_funds", # Chronic bouncer trigger
        retry_count_so_far=0,
        customer_risk_tier="high_value",
        dnd_flag=False,
        past_bounce_count=41,           # Chronic bouncer!
    )

    # Initialize an audit log
    audit = AuditLog()

    print("🚀 Starting Full Pipeline Test: High Value Mandate Expiry -> Voice Call")
    print(f"Event ID: {event.record_id}")
    print(f"Condition: Amount=₹{event.amount_inr}, Tier={event.customer_risk_tier}, Reason={event.reason_code}")
    print("-" * 50)

    try:
        # Run the full pipeline: Classify -> Decide -> Execute
        result = run_one(event, audit)

        print("\n✅ Pipeline Execution Complete!")
        print(f"Channel Used: {result['channel']}")
        print(f"Execution Detail: {result['detail']}")

        # Print the audit trail to see the decision logic
        print("\n--- Decision Audit Trail ---")
        for entry in audit.for_record(event.record_id):
            print(f"[{entry['step']}] {entry['detail']}")
        print("-" * 50)

        if result['channel'] == 'voice':
            print("\n📞 Result: The system attempted to place a real voice call!")
            if "SID:" in result['detail']:
                print("✨ SUCCESS: Twilio API accepted the call request. Your phone should ring!")
            else:
                print("⚠️  The system chose Voice, but the API call might have failed (check logs).")
        else:
            print(f"❌ Unexpected Channel: {result['channel']}. The voice escalation criteria were not met.")

    except Exception as e:
        print(f"\n❌ Pipeline crashed: {e}")

if __name__ == "__main__":
    test_voice_delivery()
