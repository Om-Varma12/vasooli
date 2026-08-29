"""
FastAPI Webhook Receiver for Razorpay Webhooks.
Verifies payload signature, deduplicates incoming events, and enqueues them for worker processing.
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from .signature import verify_signature
from .dedupe_store import already_processed, mark_processed
from .queue import enqueue

# Load .env so RAZORPAY_WEBHOOK_SECRET and other vars are available even when
# the server is started directly with uvicorn (not via a shell that already exports them).
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("vasooli.ingest")

app = FastAPI(title="Vasooli Ingest API")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/webhooks/razorpay")
async def receive(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    if secret:
        if not verify_signature(body, signature, secret):
            logger.error(f"Webhook signature verification failed. secret={secret}, signature={signature}")
            raise HTTPException(status_code=400, detail="invalid signature")
    else:
        print(
            "WARNING: RAZORPAY_WEBHOOK_SECRET is not configured in env. Signature verification is bypassed.",
            file=sys.stderr,
        )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        raise HTTPException(status_code=400, detail="invalid json payload")

    # Razorpay's real webhook format does NOT have a top-level "id".
    # The entity ID is nested inside payload -> payment/subscription/invoice -> entity -> id.
    # We build a stable dedup key from multiple fallback locations.
    inner = payload.get("payload", {})
    entity_id = None
    entity_type = None
    entity_data = {}
    for key in ("payment", "subscription", "invoice", "order"):
        candidate = inner.get(key, {}).get("entity", {})
        if candidate.get("id"):
            entity_id = candidate["id"]
            entity_type = key
            entity_data = candidate
            break

    event_id = payload.get("id") or payload.get("event_id")
    if not event_id:
        logger.error(f"Missing event identifier (id or event_id) in payload: {payload}")
        raise HTTPException(status_code=400, detail="missing event identifier")

    if already_processed(event_id):
        logger.info(json.dumps({
            "vasooli_event": "duplicate_ignored",
            "event_type": payload.get("event"),
            "event_id": event_id,
            "account_id": payload.get("account_id"),
        }, indent=2))
        return {"status": "duplicate, ignored"}

    # ── Structured transaction log ────────────────────────────────────────────
    log_entry = {
        "vasooli_event":   "webhook_received",
        "received_at":     datetime.now(timezone.utc).isoformat(),
        "event_type":      payload.get("event"),
        "account_id":      payload.get("account_id"),
        "entity_type":     entity_type,
        "entity_id":       entity_id,
        "amount_inr":      round(entity_data.get("amount", 0) / 100, 2) if entity_data.get("amount") else None,
        "currency":        entity_data.get("currency"),
        "status":          entity_data.get("status"),
        "method":          entity_data.get("method"),
        "error_code":      entity_data.get("error_code"),
        "error_desc":      entity_data.get("error_description"),
        "customer_id":     entity_data.get("customer_id"),
        "contact":         entity_data.get("contact"),
        "email":           entity_data.get("email"),
        "description":     entity_data.get("description"),
        "created_at_unix": payload.get("created_at"),
    }
    logger.info("\n" + json.dumps({k: v for k, v in log_entry.items() if v is not None}, indent=2))
    # ─────────────────────────────────────────────────────────────────────────

    mark_processed(event_id)
    enqueue(payload)

    return {"status": "queued"}

