import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..models import RecoveryEvent, PromiseToPay, AuditLog

logger = logging.getLogger("vasooli.services.voice")

class VoiceService:
    """Handles the business logic for voice-based Promise to Pay (PTP) capture."""

    @staticmethod
    async def capture_promise(db: AsyncSession, record_id: str, customer_id: str, amount: float, promised_text: str = None) -> bool:
        """
        Records a payment promise captured during a voice call.
        """
        try:
            # 1. Update RecoveryEvent to mark promise as captured
            stmt = update(RecoveryEvent).where(RecoveryEvent.record_id == record_id).values(promise_captured=True)
            await db.execute(stmt)

            # 2. Create PromiseToPay record
            # Default: Promised date is 7 days from now unless parsed from text
            promised_date = datetime.now().date() + timedelta(days=7)

            promise = PromiseToPay(
                record_id=record_id,
                customer_id=customer_id,
                promised_amount=amount,
                promised_date=promised_date,
                status="pending"
            )
            db.add(promise)

            # 3. Log to Audit Trail
            audit = AuditLog(
                record_id=record_id,
                step="voice:ptp_captured",
                detail=f"PTP captured via voice. Input: {promised_text or 'DTMF 1'}"
            )
            db.add(audit)

            await db.commit()
            logger.info(f"Successfully captured PTP for record {record_id}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error capturing voice promise for {record_id}: {e}")
            return False
