"""Real integration point: a ledger table (SQLite is enough to start) + a scheduled
follow-up job checking promised dates against actual payment status (Day 3)."""


def track_promise_to_pay(event, promised: bool) -> dict:
    if not promised:
        return {"tracked": False}
    return {
        "tracked": True,
        "record_id": event.record_id,
        "follow_up_note": "Follow-up check scheduled — replace with real cron/queue on Day 3.",
    }


class HumanHandoffAdapter:
    """Not a money-moving channel — writes the case to a human queue. This IS the outcome
    for STOPPED/HUMAN_HANDOFF tiers, not a failure of the pipeline."""
    channel_name = "human_handoff"

    def send(self, event, decision) -> dict:
        return {
            "channel": self.channel_name,
            "succeeded": False,
            "amount_recovered_inr": 0.0,
            "detail": f"Case {event.record_id} routed to human collections/risk queue. "
                      f"Reason: {decision.reason}",
        }
