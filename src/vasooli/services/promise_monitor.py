import logging
from datetime import datetime, date
from typing import List, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.models import PromiseToPay, RecoveryEvent, AuditLog
from ..orchestrator import run_one
from ..models import FailureEvent

logger = logging.getLogger("vasooli.services.promise_monitor")

class PromiseMonitor:
    """
    Monitors PTP records and triggers re-entry into the recovery pipeline
    when a promised date passes without payment.
    """

    @staticmethod
    async def check_broken_promises(db: AsyncSession):
        """
        Finds all pending promises where the date has passed and the payment
        has not been recovered.
        """
        try:
            # 1. Find pending promises where date <= today
            today = datetime.now().date()
            query = select(PromiseToPay).where(
                PromiseToPay.status == "pending",
                PromiseToPay.promised_date <= today
            )
            result = await db.execute(query)
            broken_promises = result.scalars().all()

            if not broken_promises:
                return 0

            logger.info(f"Found {len(broken_promises)} potentially broken promises.")
            count = 0

            for promise in broken_promises:
                # 2. Check if payment was actually recovered for this record
                # We check the RecoveryEvent table for recovered status
                event_query = select(RecoveryEvent).where(RecoveryEvent.record_id == promise.record_id)
                event_res = await db.execute(event_query)
                event = event_res.scalar_one_or_none()

                if event and event.status == "recovered":
                    # Payment happened! Mark promise as kept
                    promise.status = "kept"
                    logger.info(f"Promise kept for {promise.record_id}")
                else:
                    # Payment NOT happened -> Broken Promise
                    promise.status = "broken"

                    # 3. Re-enter the pipeline as a "broken_promise" root cause
                    # We create a FailureEvent to feed into the orchestrator
                    failure_event = FailureEvent(
                        record_id=promise.record_id,
                        merchant_id=event.merchant_id if event else "unknown",
                        customer_id=promise.customer_id,
                        amount_inr=float(promise.promised_amount),
                        reason_code="broken_promise", # This is the key signal
                        retry_count_so_far=event.retry_count if event else 0,
                        # a simple dummy for other required fields
                        category="SUBSCRIPTION" if event else "SUBSCRIPTION",
                        payment_method="UPI_AUTOPAY" if event else "UPI_AUTOPAY",
                        phone_number=event.phone_number if event else None,
                        raw_payload={"signal": "broken_promise_monitor"}
                    )

                    # Note: orchestrator.run_one requires an AuditLog object
                    from .audit.audit_log import AuditLog
                    audit = AuditLog()

                    # Run through the pipeline
                    run_one(failure_event, audit)
                    count += 1

            await db.commit()
            return count

        except Exception as e:
            logger.error(f"Error in promise monitor: {e}")
            await db.rollback()
            return 0
