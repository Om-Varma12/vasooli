"""
Real integration point: WhatsApp Business API via Twilio Sandbox.
Falls back to simulated output if Twilio credentials are not set in env.
"""
import os
import random
import logging
from dotenv import load_dotenv
from twilio.rest import Client

from .base_adapter import ChannelAdapter
from ..decide.rules_engine import load_rules
from ..audit.dead_letter import write as dlq_write

# Load environment variables at module load
load_dotenv()

WHATSAPP_TEMPLATE = (
    "Hi, your payment of ₹{amount} to {merchant} didn't go through. Tap to retry or update "
    "your payment method: {link}"
)

logger = logging.getLogger("vasooli.execute.whatsapp")


class WhatsAppAdapter(ChannelAdapter):
    channel_name = "whatsapp"

    def send(self, event, decision) -> dict:
        message = WHATSAPP_TEMPLATE.format(
            amount=f"{event.amount_inr:,.0f}",
            merchant=event.merchant_id,
            link="rzp.io/r/xxxx"
        )

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        content_sid = os.environ.get("TWILIO_CONTENT_SID")

        raw_from = os.environ.get("TWILIO_WHATSAPP_FROM") or os.environ.get("TWILIO_SANDBOX_NUMBER", "")
        raw_to = os.environ.get("TWILIO_WHATSAPP_TO") or os.environ.get("TEST_NUMBER", "")

        from_number = raw_from if raw_from.startswith("whatsapp:") else f"whatsapp:{raw_from}" if raw_from else None
        to_number = raw_to if raw_to.startswith("whatsapp:") else f"whatsapp:{raw_to}" if raw_to else None

        # Check if Twilio configuration is present
        if account_sid and auth_token and from_number and to_number:
            try:
                import json
                client = Client(account_sid, auth_token)

                # Use Content API if ContentSid is available
                if content_sid:
                    msg = client.messages.create(
                        from_=from_number,
                        to=to_number,
                        content_sid=content_sid,
                        content_variables=json.dumps({
                            "1": f"{event.amount_inr:,.0f}",
                            "2": event.merchant_id,
                            "3": "rzp.io/r/xxxx"
                        })
                    )
                else:
                    # Fallback to plain body (only works for active sessions)
                    msg = client.messages.create(
                        from_=from_number,
                        to=to_number,
                        body=message
                    )

                logger.info(f"WhatsApp notification sent successfully via Twilio. SID: {msg.sid}")
                return {
                    "channel": self.channel_name,
                    "succeeded": True,
                    "amount_recovered_inr": 0.0,
                    "detail": f"Sent real WhatsApp notification via Twilio Sandbox. SID: {msg.sid}",
                    "message": message,
                }
            except Exception as e:
                err_msg = f"Failed to send WhatsApp message via Twilio: {e}"
                logger.error(err_msg)
                dlq_write(record_id=event.record_id, stage="execute", error=err_msg)
                logger.warning("Failing open: falling back to simulated recovery path.")
        else:
            logger.warning("Twilio credentials not fully set in environment. Running WhatsApp adapter in simulation mode.")

        # Simulation fallback
        probs = load_rules()["voice_escalation"]["recovery_probability_by_cause"]
        success_prob = probs.get(decision.root_cause.value, 0.2) * 0.6
        succeeded = random.random() < success_prob
        return {
            "channel": self.channel_name,
            "succeeded": succeeded,
            "amount_recovered_inr": event.amount_inr if succeeded else 0.0,
            "detail": f"Sent templated nudge: \"{message}\" "
                      f"({'recovered' if succeeded else 'no click-through'} in simulation).",
            "message": message,
        }
