"""
Real integration point: telephony provider (outbound call) + STT/TTS + an LLM-driven
Hinglish conversation. `_mock_hinglish_transcript` is a scripted stand-in so the demo has
something concrete before real voice infra is wired (Day 4).
"""
import random
import os
import uuid
import logging
from dotenv import load_dotenv
from .base_adapter import ChannelAdapter
from .promise_to_pay import track_promise_to_pay
from ..decide.rules_engine import load_rules

# Load environment variables
load_dotenv()
logger = logging.getLogger("vasooli.execute.voice")

class VoiceAdapter(ChannelAdapter):
    channel_name = "voice"

    def send(self, event, decision) -> dict:
        transcript = _mock_hinglish_transcript(event)

        # 1. Handle Real Call if credentials are set
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_VOICE_FROM")
        base_url = os.environ.get("VOICE_BASE_URL")

        # We use a demo override for the phone number since synthetic data lacks them
        to_number = os.environ.get("TEST_NUMBER")

        if account_sid and auth_token and from_number and base_url and to_number:
            try:
                from twilio.rest import Client
                import redis
                import json

                # Create unique call ID and store transcript in Redis for the TwiML endpoint
                call_id = str(uuid.uuid4())
                redis_client = redis.Redis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)
                redis_client.set(f"voice:transcript:{call_id}", transcript, ex=3600)

                # Trigger Twilio Call
                client = Client(account_sid, auth_token)

                # Determine the call URL. If it's a Twilio template URL, use it directly.
                # Otherwise, construct the TwiML endpoint URL.
                if "webhooks.twilio.com" in base_url:
                    call_url = base_url
                else:
                    call_url = f"{base_url}/voice/twiml?call_id={call_id}"

                call = client.calls.create(
                    url=call_url,
                    to=to_number,
                    from_=from_number
                )

                logger.info(f"Real voice call triggered. SID: {call.sid}, CallID: {call_id}")
                call_detail = f"Real voice call placed. SID: {call.sid}"
            except Exception as e:
                logger.error(f"Failed to place real voice call: {e}")
                call_detail = f"Call failed: {e}"

        else:
            logger.warning("Twilio voice credentials not fully set. Running in simulation mode.")
            call_detail = "Voice call simulated."

        # 2. Maintain simulated outcomes (as required)
        probs = load_rules()["voice_escalation"]["recovery_probability_by_cause"]
        success_prob = probs.get(decision.root_cause.value, 0.2) * 1.3
        succeeded = random.random() < min(success_prob, 0.9)
        promise_captured = succeeded or random.random() < 0.2

        if promise_captured and not succeeded:
            track_promise_to_pay(event, promised=True)

        return {
            "channel": self.channel_name,
            "succeeded": succeeded,
            "amount_recovered_inr": event.amount_inr if succeeded else 0.0,
            "promise_to_pay": promise_captured and not succeeded,
            "transcript": transcript,
            "detail": f"{call_detail} | { 'Voice call completed — see transcript.' if not call_detail.startswith('Call failed') else 'Execution failed'}",
        }


def _mock_hinglish_transcript(event) -> str:
    return (
        f"Agent: Namaste! Ye {event.merchant_id} se call hai. Aapka payment of ₹"
        f"{event.amount_inr:,.0f} process nahi ho paya. Kya main aapki madad kar sakta hoon?\n"
        f"Customer: Haan, thoda issue tha, but ab theek hai.\n"
        f"Agent: Perfect. Toh main abhi ek retry link bhej deta hoon WhatsApp par — 2 minute "
        f"mein confirm kar dijiyega. Dhanyawad!"
    )
