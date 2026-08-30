import sys
from pathlib import Path

# Add src to path so we can import vasooli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.models import FailureEvent, PaymentMethod, Category, RootCause
from vasooli.decide.guard_clauses import check_chronic_bouncer

def main():
    # Construct a FailureEvent directly with past_bounce_count = 3 to trigger the guard
    event = FailureEvent(
        record_id="rec_chronic_test_0001",
        merchant_id="merchant_ott_101",
        customer_id="cust_9999",
        payment_method=PaymentMethod.UPI_AUTOPAY,
        category=Category.SUBSCRIPTION,
        amount_inr=999.0,
        webhook_event="payment.failed",
        reason_code="insufficient_funds",
        retry_count_so_far=0,          # deliberately below RETRY_CEILING
        customer_risk_tier="standard",
        dnd_flag=False,
        past_bounce_count=3,           # <-- the trigger condition
    )

    print("Testing Chronic Bouncer Guard Clause...")
    print(f"Event: {event.record_id}, Past Bounces: {event.past_bounce_count}, Reason: {event.reason_code}")

    decision = check_chronic_bouncer(event, RootCause.INSUFFICIENT_FUNDS)

    if decision:
        print("\n✅ SUCCESS: Guard clause fired!")
        print(f"Decision Tier: {decision.tier}")
        print(f"Reason: {decision.reason}")
        print(f"Blocked By: {decision.blocked_by}")
    else:
        print("\n❌ FAILURE: Guard clause did not fire.")

if __name__ == "__main__":
    main()
