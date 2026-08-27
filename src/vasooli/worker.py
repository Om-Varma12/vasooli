"""
Vasooli Queue Worker.
Continuously dequeues Razorpay webhooks, parses them, and routes them to orchestrator.run_one().
"""
import time
import logging
from .ingest.queue import dequeue
from .orchestrator import run_one
from .audit.audit_log import AuditLog
from .models import FailureEvent, Category, PaymentMethod


def parse_webhook_to_event(payload: dict) -> FailureEvent:
    """
    Parses a nested Razorpay webhook payload (or a flat dictionary) into a FailureEvent.
    """
    event_id = payload.get("id") or payload.get("event_id") or "rec_unknown"
    event_name = payload.get("event") or payload.get("webhook_event") or "payment.failed"
    account_id = payload.get("account_id") or payload.get("merchant_id") or "merchant_default"

    inner_payload = payload.get("payload", {})
    entity = {}
    category = Category.SUBSCRIPTION
    payment_method = PaymentMethod.UPI_AUTOPAY
    amount = 0.0
    reason_code = "unknown"
    customer_id = "cust_unknown"
    retry_count = 0
    days_overdue = 0

    if "subscription" in inner_payload:
        entity = inner_payload["subscription"].get("entity", {})
        category = Category.SUBSCRIPTION
        amount = float(entity.get("amount", 0)) / 100.0
        customer_id = entity.get("customer_id", "cust_unknown")
        if event_name == "subscription.halted":
            retry_count = 3
        else:
            retry_count = entity.get("current_start", 0)
    elif "payment" in inner_payload:
        entity = inner_payload["payment"].get("entity", {})
        category = Category.SUBSCRIPTION
        amount = float(entity.get("amount", 0)) / 100.0
        customer_id = entity.get("customer_id") or entity.get("email") or "cust_unknown"
        reason_code = entity.get("error_code") or entity.get("error_description") or "unknown"
        method = entity.get("method", "")
        if "upi" in method:
            payment_method = PaymentMethod.UPI_AUTOPAY
        elif "card" in method:
            payment_method = PaymentMethod.CARD
        else:
            payment_method = PaymentMethod.ENACH
    elif "invoice" in inner_payload:
        entity = inner_payload["invoice"].get("entity", {})
        category = Category.B2B_RECEIVABLE
        amount = float(entity.get("amount", 0)) / 100.0
        customer_id = entity.get("customer_id", "cust_unknown")
        payment_method = PaymentMethod.ENACH
        reason_code = "invoice_expired"
        days_overdue = 30
    else:
        # Fallback to direct mapping from flat dictionary (useful for testing & synthetic data)
        amount = float(payload.get("amount_inr") or payload.get("amount", 0))
        if amount > 1000 and payload.get("amount") and not payload.get("amount_inr"):
            amount = amount / 100.0
        category_val = payload.get("category")
        category = Category(category_val) if category_val in [c.value for c in Category] else Category.SUBSCRIPTION
        method_val = payload.get("payment_method")
        payment_method = PaymentMethod(method_val) if method_val in [p.value for p in PaymentMethod] else PaymentMethod.UPI_AUTOPAY
        reason_code = payload.get("reason_code") or payload.get("error_code") or "unknown"
        customer_id = payload.get("customer_id", "cust_unknown")
        retry_count = int(payload.get("retry_count_so_far", 0))
        days_overdue = int(payload.get("days_overdue", 0))
        account_id = payload.get("merchant_id", account_id)

    notes = entity.get("notes", {})
    if isinstance(notes, dict):
        risk_tier = notes.get("customer_risk_tier") or payload.get("customer_risk_tier") or "standard"
        dnd_flag = notes.get("dnd_flag") or payload.get("dnd_flag") or False
    else:
        risk_tier = payload.get("customer_risk_tier") or "standard"
        dnd_flag = payload.get("dnd_flag") or False

    if isinstance(reason_code, str):
        reason_code_lower = reason_code.lower()
        if "insufficient" in reason_code_lower or "balance" in reason_code_lower:
            reason_code = "insufficient_funds"
        elif "downtime" in reason_code_lower:
            reason_code = "bank_downtime"
        elif "expired" in reason_code_lower:
            reason_code = "mandate_expired"
        elif "block" in reason_code_lower or "risk" in reason_code_lower:
            reason_code = "risk_block"
        elif "cancelled" in reason_code_lower:
            reason_code = "mandate_cancelled_by_user"
        elif "closed" in reason_code_lower:
            reason_code = "account_closed"
        elif "timeout" in reason_code_lower:
            reason_code = "otp_timeout"

    return FailureEvent(
        record_id=event_id,
        merchant_id=account_id,
        customer_id=customer_id,
        payment_method=payment_method,
        category=category,
        amount_inr=amount,
        webhook_event=event_name,
        reason_code=reason_code,
        retry_count_so_far=retry_count,
        customer_risk_tier=risk_tier,
        dnd_flag=bool(dnd_flag),
        days_overdue=days_overdue,
    )


def process_next_event(audit: AuditLog) -> bool:
    """
    Pulls next event from queue and processes it.
    Returns True if an event was processed, False if queue is empty.
    """
    payload = dequeue()
    if payload is None:
        return False
    
    try:
        event = parse_webhook_to_event(payload)
        run_one(event, audit)
    except Exception as e:
        logging.error(f"Error processing event {payload.get('id', 'unknown')}: {e}")
        # Routing to dead letter stub
        try:
            from .audit.dead_letter import write as dlq_write
            dlq_write(record_id=payload.get("id", "unknown"), stage="worker", error=str(e))
        except Exception:
            pass
            
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting Vasooli Queue Worker...")
    audit = AuditLog()
    
    try:
        while True:
            processed = process_next_event(audit)
            if not processed:
                time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping worker...")


if __name__ == "__main__":
    main()
