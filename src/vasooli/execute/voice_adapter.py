"""
Real integration point: telephony provider (outbound call) + STT/TTS + an LLM-driven
Hinglish conversation.
"""
import os
import uuid
import logging
import json
import redis
from dotenv import load_dotenv
from twilio.rest import Client

from .base_adapter import ChannelAdapter

# Load environment variables
load_dotenv()
logger = logging.getLogger("vasooli.execute.voice")

class VoiceAdapter(ChannelAdapter):
    channel_name = "voice"

    def send(self, event, decision) -> dict:
        """
        Triggers a real Twilio outbound call and sets up the session context in Redis.
        """
        # 1. Setup environment and credentials
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_VOICE_FROM")
        base_url = os.environ.get("VOICE_BASE_URL")
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

        # Use event phone number, fallback to test number
        to_number = getattr(event, "phone_number", os.environ.get("TEST_NUMBER"))

        if not all([account_sid, auth_token, from_number, base_url, to_number]):
            logger.warning("Twilio voice credentials not fully set. Call cannot be placed.")
            return {
                "channel": self.channel_name,
                "succeeded": False,
                "amount_recovered_inr": 0.0,
                "promise_to_pay": False,
                "transcript": "Credentials missing: Call not placed.",
                "detail": "Voice execution failed: Missing environment variables."
            }

        try:
            # 2. Create a unique session token for this call
            call_token = str(uuid.uuid4())

            # 3. Store session context in Redis
            # This context is used by the /voice/init and /voice/handle-response endpoints
            redis_client = redis.from_url(redis_url, decode_responses=True)
            session_context = {
                "record_id": event.record_id,
                "customer_id": event.customer_id,
                "amount_inr": event.amount_inr,
                "merchant_id": getattr(event, "merchant_id", "Vasooli"),
            }
            # Expire session after 1 hour
            redis_client.set(f"voice:session:{call_token}", json.dumps(session_context), ex=3600)

            # 4. Trigger the Twilio call
            client = Client(account_sid, auth_token)

            # The call URL directs Twilio to our /voice/init endpoint
            call_url = f"{base_url}/voice/init?token={call_token}"

            call = client.calls.create(
                to=to_number,
                from_=from_number,
                url=call_url,
            )

            logger.info(f"Real voice call triggered. SID: {call.sid}, Token: {call_token}")

            return {
                "channel": self.channel_name,
                "succeeded": False, # Set to False because payment hasn't happened yet
                "amount_recovered_inr": 0.0,
                "promise_to_pay": False, # Will be updated by the webhook /voice/handle-response
                "transcript": f"Call initiated via Twilio. SID: {call.sid}",
                "detail": f"Real voice call placed successfully. SID: {call.sid}",
            }

        except Exception as e:
            logger.error(f"Failed to place real voice call for record {event.record_id}: {e}")
            return {
                "channel": self.channel_name,
                "succeeded": False,
                "amount_recovered_inr": 0.0,
                "promise_to_pay": False,
                "transcript": f"Error: {str(e)}",
                "detail": f"Call failed: {str(e)}",
            }
