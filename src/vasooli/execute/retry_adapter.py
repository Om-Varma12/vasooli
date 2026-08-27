"""Real integration point: Razorpay Subscriptions 'create subsequent payment' / order retry."""
import random
from .base_adapter import ChannelAdapter
from ..decide.rules_engine import load_rules


class RetryAdapter(ChannelAdapter):
    channel_name = "retry"

    def send(self, event, decision) -> dict:
        probs = load_rules()["voice_escalation"]["recovery_probability_by_cause"]
        success_prob = probs.get(decision.root_cause.value, 0.2)
        succeeded = random.random() < success_prob
        return {
            "channel": self.channel_name,
            "succeeded": succeeded,
            "amount_recovered_inr": event.amount_inr if succeeded else 0.0,
            "detail": f"Scheduled retry in {decision.retry_after_minutes}min "
                      f"({'succeeded' if succeeded else 'no response'} in simulation).",
        }
