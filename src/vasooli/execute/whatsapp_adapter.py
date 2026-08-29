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
        from_number = os.environ.get("TWILIO_WHATSAPP_FROM")
        to_number = os.environ.get("TWILIO_WHATSAPP_TO")

        # Check if Twilio configuration is present
        if account_sid and auth_token and from_number and to_number:
            try:
                # Initialize Twilio Client
                client = Client(account_sid, auth_token)
                
                # Send message via Sandbox
                msg = client.messages.create(
                    from_=from_number,
                    to=to_number,
                    body=message
                )
                
                logger.info(f"WhatsApp notification sent successfully via Twilio. SID: {msg.sid}")
                return {
                    "channel": self.channel_name,
                    "succeeded": True,
                    "amount_recovered_inr": 0.0,  # Real recovery is async, handled via captured webhooks
                    "detail": f"Sent real WhatsApp notification via Twilio Sandbox. SID: {msg.sid}",
                }
            except Exception as e:
                err_msg = f"Failed to send WhatsApp message via Twilio: {e}"
                logger.error(err_msg)
                # Write failure to DLQ
                dlq_write(record_id=event.record_id, stage="execute", error=err_msg)
                
                # Fail open: degrade to simulated recovery behavior on error
                logger.warning("Failing open: falling back to simulated recovery path.")
        else:
            logger.warning("Twilio credentials not fully set in environment. Running WhatsApp adapter in simulation mode.")

        # Simulation fallback (used when credentials are missing or call fails)
        probs = load_rules()["voice_escalation"]["recovery_probability_by_cause"]
        success_prob = probs.get(decision.root_cause.value, 0.2) * 0.6  # lower lift than a call
        succeeded = random.random() < success_prob
        return {
            "channel": self.channel_name,
            "succeeded": succeeded,
            "amount_recovered_inr": event.amount_inr if succeeded else 0.0,
            "detail": f"Sent templated nudge: \"{message}\" "
                      f"({'recovered' if succeeded else 'no click-through'} in simulation).",
        }
