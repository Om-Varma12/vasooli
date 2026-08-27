"""
Real integration point: WhatsApp Business API (Meta) send-template call.

WhatsApp Business API requires pre-approved message templates for commerce/utility
messages — you cannot send arbitrary free text. WHATSAPP_TEMPLATE below stands in for that
constraint: "personalization" means filling {amount}/{merchant}/{link} slots in an
already-approved template, never free generation. Keep it that way when you wire the real
API — an LLM should never be writing the WhatsApp message body from scratch.
"""
import random
from .base_adapter import ChannelAdapter
from ..decide.rules_engine import load_rules

WHATSAPP_TEMPLATE = (
    "Hi, your payment of ₹{amount} to {merchant} didn't go through. Tap to retry or update "
    "your payment method: {link}"
)


class WhatsAppAdapter(ChannelAdapter):
    channel_name = "whatsapp"

    def send(self, event, decision) -> dict:
        message = WHATSAPP_TEMPLATE.format(
            amount=f"{event.amount_inr:,.0f}", merchant=event.merchant_id, link="rzp.io/r/xxxx"
        )
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
