from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from typing import Optional

from ..deps import get_db
from ..models import RecoveryEvent, PromiseToPay, AuditLog

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

def is_promise(text: str) -> bool:
    """Simple keyword-based promise detection.
    In production, this would be replaced by an LLM classifier.
    """
    keywords = ["pay", "promise", "will pay", "settle", "clear"]
    return any(kw in text.lower() for kw in keywords)

@router.post("/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    SmsSid: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio Webhook for incoming WhatsApp messages.
    Identifies the customer by phone number and captures PTP commitments.
    """
    # 1. Normalize Phone Number
    phone_number = From.replace("whatsapp:", "") if From.startswith("whatsapp:") else From

    # 2. Identify the most recent Recovery Event for this number
    query = select(RecoveryEvent).where(RecoveryEvent.phone_number == phone_number).order_by(desc(RecoveryEvent.created_at))
    result = await db.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        # Respond with a polite failure message if no record is found
        twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>Thank you for contacting Vasooli. We couldn\'t find an active record for your number. Please contact support.</Message></Response>'
        return Response(content=twiml, media_type="text/xml")

    # 3. Detect Promise to Pay
    if is_promise(Body):
        # Update RecoveryEvent
        event.promise_captured = True

        # Create PromiseToPay record
        # Default: Promised amount = event amount, date = 7 days from now
        promise = PromiseToPay(
            record_id=event.record_id,
            customer_id=event.customer_id,
            promised_amount=event.amount_inr,
            promised_date=datetime.now().date() + timedelta(days=7),
            status="pending"
        )
        db.add(promise)

        # Record in Audit Log
        audit = AuditLog(
            record_id=event.record_id,
            step="webhook:whatsapp",
            detail=f"Captured PTP promise via WhatsApp: \"{Body}\""
        )
        db.add(audit)

        await db.commit()

        twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>Thank you! We\'ve recorded your promise to pay. We will notify you shortly regarding the next steps.</Message></Response>'
    else:
        # Just acknowledge the message
        twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>Thank you for your message. Our team has been notified and will get back to you soon.</Message></Response>'

    return Response(content=twiml, media_type="text/xml")
