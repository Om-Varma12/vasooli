"""
STATUS: stub, Day 6. Real implementation calls Razorpay's Fetch Payment / Fetch
Subscription API for the full entity, falling back to whatever the webhook payload already
provided if the call fails or times out — never drop the event over a network hiccup.

    def enrich(webhook_payload: dict, razorpay_client) -> dict:
        entity_id = webhook_payload["payload"]["payment"]["entity"]["id"]
        try:
            full_entity = razorpay_client.payment.fetch(entity_id)
            return {**webhook_payload, "enriched": full_entity}
        except Exception as e:
            # Degrade, don't drop. Log to dead_letter with stage="enrich" so it's visible,
            # but still let the event proceed with what the webhook payload already gave us.
            from ..audit.dead_letter import write as dlq_write
            dlq_write(record_id=entity_id, stage="enrich", error=str(e))
            return webhook_payload
"""
