import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..api.models import RecoveryEvent, PromiseToPay, AuditLog

logger = logging.getLogger("vasooli.services.voice")

class VoiceService:
    """Handles the business logic for voice-based Promise to Pay (PTP) capture."""

    @staticmethod
    async def extract_promised_date(text: str) -> Optional[datetime]:
        """
        Extracts a payment date from user speech using an LLM.
        In production, this calls Grok/LLM.
        """
        # Simulation of LLM extraction
        text_lower = text.lower()
        if "kal" in text_lower or "tomorrow" in text_lower:
            return datetime.now().date() + timedelta(days=1)
        if "parso" in text_lower or "day after tomorrow" in text_lower:
            return datetime.now().date() + timedelta(days=2)
        if "next week" in text_lower or "agle hafte" in text_lower:
            return datetime.now().date() + timedelta(days=7)

        # Default fallback
        return None

    @staticmethod
    async def capture_promise(db: AsyncSession, record_id: str, customer_id: str, amount: float, promised_text: str = None) -> bool:
        """
        Records a payment promise captured during a voice call.
        """
        try:
            # 1. Update RecoveryEvent to mark promise as captured
            stmt = update(RecoveryEvent).where(RecoveryEvent.record_id == record_id).values(promise_captured=True)
            await db.execute(stmt)

            # 2. Extract date from text using LLM
            promised_date = None
            if promised_text:
                promised_date = await VoiceService.extract_promised_date(promised_text)

            # Fallback: 7 days from now if extraction fails
            if not promised_date:
                promised_date = datetime.now().date() + timedelta(days=7)
            else:
                # Ensure we store as date only
                if isinstance(promised_date, datetime):
                    promised_date = promised_date.date()

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
                detail=f"PTP captured via voice. Date: {promised_date}. Input: {promised_text or 'DTMF 1'}"
            )
            db.add(audit)

            await db.commit()
            logger.info(f"Successfully captured PTP for record {record_id} on {promised_date}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error capturing voice promise for {record_id}: {e}")
            return False
