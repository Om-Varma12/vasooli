from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json
import logging
import redis

from ..deps import get_db
from ..models import RecoveryEvent
from ..services.voice_service import VoiceService

router = APIRouter(prefix="/voice", tags=["Voice Recovery"])
logger = logging.getLogger("vasooli.api.voice")

# Redis config for session management
# In production, this would be in settings.py
import os
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def get_session_context(token: str) -> Optional[dict]:
    """Fetches recovery event context from Redis using the call token."""
    data = redis_client.get(f"voice:session:{token}")
    if not data:
        return None
    return json.loads(data)

@router.post("/init")
async def voice_init(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio Voice Initiation endpoint.
    Provides the first TwiML prompt in Hinglish.
    """
    context = get_session_context(token)
    if not context:
        # Polite failure: session expired or invalid token
        twiml = '<Response><Say voice="Polly.Aditi" language="hi-IN">Kshama karein, session timeout ho gaya hai. Hum aapko baad mein call karenge.</Say><Hangup/></Response>'
        return Response(content=twiml, media_type="text/xml")

    merchant_name = context.get("merchant_id", "Vasooli")
    amount = context.get("amount_inr", 0.0)

    # Prompt in Hinglish using Polly Aditi
    # We use <Gather> to capture either speech or DTMF digits
    twiml = f'''
    <Response>
        <Gather input="speech" timeout="5" numDigits="1" language="hi-IN" action="/voice/handle-response?token={token}">
            <Say voice="Polly.Aditi" language="hi-IN">
                Namaste! Ye {merchant_name} se call hai. Aapka payment of {amount:.0f} rupees process nahi ho paya.
                Kya aap ise pay karne ka vaada karte hain? Promise karne ke liye 1 dabayein ya bolkar batayein.
            </Say>
        </Gather>
        <Say voice="Polly.Aditi" language="hi-IN">Humne koi response nahi paya. Dhanyawad.</Say>
        <Hangup/>
    </Response>
    '''
    return Response(content=twiml, media_type="text/xml")

@router.post("/handle-response")
async def voice_handle_response(
    token: str,
    Digits: Optional[str] = Form(None),
    SpeechResult: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handles the response from the <Gather> block.
    Processes DTMF digits or STT transcription to capture a PTP.
    """
    context = get_session_context(token)
    if not context:
        twiml = '<Response><Say voice="Polly.Aditi" language="hi-IN">Kshama karein, session error. Dhanyawad.</Say><Hangup/></Response>'
        return Response(content=twiml, media_type="text/xml")

    record_id = context["record_id"]
    customer_id = context["customer_id"]
    amount = context["amount_inr"]

    is_promise = False
    promise_text = None

    # 1. Check DTMF (Digits)
    if Digits == "1":
        is_promise = True
        promise_text = "User pressed 1 (Confirm PTP)"

    # 2. Check Speech Result (STT)
    elif SpeechResult:
        # Simple keyword detection for Hinglish promises
        # In production, this would use an LLM a la the WhatsApp PTP handler
        keywords = ["pay", "promise", "vaada", "karunga", "karungi", "settle", "clear"]
        if any(kw in SpeechResult.lower() for kw in keywords):
            is_promise = True
            promise_text = f"User spoke: {SpeechResult}"

    if is_promise:
        success = await VoiceService.capture_promise(
            db=db,
            record_id=record_id,
            customer_id=customer_id,
            amount=amount,
            promised_text=promise_text
        )
        if success:
            twiml = '<Response><Say voice="Polly.Aditi" language="hi-IN">Dhanyawad! Humne aapka promise record kar liya hai. Aapko jald hi payment link mil jayega.</Say><Hangup/></Response>'
        else:
            twiml = '<Response><Say voice="Polly.Aditi" language="hi-IN">Kshama karein, database error. Hum aapko baad mein call karenge.</Say><Hangup/></Response>'
    else:
        twiml = '<Response><Say voice="Polly.Aditi" language="hi-IN">Kshama karein, hum samajh nahi paye. Hum aapko baad mein contact karenge.</Say><Hangup/></Response>'

    return Response(content=twiml, media_type="text/xml")
