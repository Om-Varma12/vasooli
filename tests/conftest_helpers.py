import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.models import FailureEvent, Category, PaymentMethod


def make_event(**overrides) -> FailureEvent:
    """Builds a FailureEvent with sane defaults, overridable per test."""
    defaults = dict(
        record_id="rec_test_0001",
        merchant_id="merchant_test",
        customer_id="cust_test",
        payment_method=PaymentMethod.UPI_AUTOPAY,
        category=Category.SUBSCRIPTION,
        amount_inr=999.0,
        webhook_event="payment.failed",
        reason_code="insufficient_funds",
        retry_count_so_far=0,
        customer_risk_tier="standard",
        dnd_flag=False,
        days_overdue=0,
    )
    defaults.update(overrides)
    return FailureEvent(**defaults)
