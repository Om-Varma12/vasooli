"""
Real integration point: telephony provider (outbound call) + STT/TTS + an LLM-driven
Hinglish conversation. `_mock_hinglish_transcript` is a scripted stand-in so the demo has
something concrete before real voice infra is wired (Day 4).
"""
import random
from .base_adapter import ChannelAdapter
from .promise_to_pay import track_promise_to_pay
from ..decide.rules_engine import load_rules


class VoiceAdapter(ChannelAdapter):
    channel_name = "voice"

    def send(self, event, decision) -> dict:
        transcript = _mock_hinglish_transcript(event)
        probs = load_rules()["voice_escalation"]["recovery_probability_by_cause"]
        success_prob = probs.get(decision.root_cause.value, 0.2) * 1.3  # voice lifts recovery
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
            "detail": "Voice call completed — see transcript.",
        }


def _mock_hinglish_transcript(event) -> str:
    return (
        f"Agent: Namaste! Ye {event.merchant_id} se call hai. Aapka payment of ₹"
        f"{event.amount_inr:,.0f} process nahi ho paya. Kya main aapki madad kar sakta hoon?\n"
        f"Customer: Haan, thoda issue tha, but ab theek hai.\n"
        f"Agent: Perfect. Toh main abhi ek retry link bhej deta hoon WhatsApp par — 2 minute "
        f"mein confirm kar dijiyega. Dhanyawad!"
    )
