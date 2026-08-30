"""
Real implementation: Calls Razorpay's APIs to fetch full entity details.
Provides fallback to the original webhook payload if API calls fail.
"""
import os
import logging
from dotenv import load_dotenv
from ..audit.dead_letter import write as dlq_write

load_dotenv()
logger = logging.getLogger("vasooli.enrichment")

def get_razorpay_client():
    """Returns an initialized Razorpay client using env credentials."""
    try:
        import razorpay
        api_key = os.environ.get("RAZORPAY_API_KEY")
        api_secret = os.environ.get("RAZORPAY_KEY_SECRET")
        if not api_key or not api_secret:
            raise ValueError("RAZORPAY_API_KEY or RAZORPAY_KEY_SECRET not set in environment.")
        return razorpay.Client(auth=(api_key, api_secret))
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay client: {e}")
        return None

def enrich(payload: dict) -> dict:
    """
    Fetches full entity details from Razorpay API based on the webhook payload.
    Returns a dictionary containing the original payload and any enriched data.
    """
    inner = payload.get("payload", {})
    entity_id = None
    entity_type = None

    # Identify the entity type and ID
    for key in ("payment", "subscription", "invoice", "order"):
        candidate = inner.get(key, {}).get("entity", {})
        if candidate.get("id"):
            entity_id = candidate["id"]
            entity_type = key
            break

    if not entity_id:
        # Nothing to enrich, return as is
        return payload

    client = get_razorpay_client()
    if not client:
        # Fail open: proceed with existing payload
        return payload

    try:
        if entity_type == "payment":
            full_entity = client.payment.fetch(entity_id)
        elif entity_type == "subscription":
            full_entity = client.subscription.fetch(entity_id)
        elif entity_type == "invoice":
            # Razorpay's Python SDK might have different methods for invoices
            # Fallback to raw request if necessary, but try .invoice.fetch first
            full_entity = client.invoice.fetch(entity_id)
        else:
            # Unsupported entity type for enrichment
            return payload

        # Return the original payload with the enriched entity added/updated
        enriched_payload = payload.copy()
        if "enriched" not in enriched_payload:
            enriched_payload["enriched"] = {}

        enriched_payload["enriched"][entity_type] = full_entity
        return enriched_payload

    except Exception as e:
        err_msg = f"Enrichment failed for {entity_type}:{entity_id}: {e}"
        logger.error(err_msg)
        # Write to DLQ but let the event proceed (degrade gracefully)
        dlq_write(record_id=entity_id, stage="enrich", error=err_msg)
        return payload
