"""
FastAPI Webhook Receiver for Razorpay Webhooks.
Verifies payload signature, deduplicates incoming events, and enqueues them for worker processing.
"""
import os
import sys
from fastapi import FastAPI, Request, HTTPException
from .signature import verify_signature
from .dedupe_store import already_processed, mark_processed
from .queue import enqueue

app = FastAPI(title="Vasooli Ingest API")


@app.post("/webhooks/razorpay")
async def receive(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    if secret:
        if not verify_signature(body, signature, secret):
            raise HTTPException(status_code=400, detail="invalid signature")
    else:
        print(
            "WARNING: RAZORPAY_WEBHOOK_SECRET is not configured in env. Signature verification is bypassed.",
            file=sys.stderr,
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json payload")

    # Razorpay's real webhook format does NOT have a top-level "id".
    # The entity ID is nested inside payload -> payment/subscription/invoice -> entity -> id.
    # We build a stable dedup key from multiple fallback locations.
    inner = payload.get("payload", {})
    entity_id = None
    for key in ("payment", "subscription", "invoice", "order"):
        entity_id = inner.get(key, {}).get("entity", {}).get("id")
        if entity_id:
            break

    event_id = (
        entity_id
        or payload.get("id")
        or payload.get("event_id")
        or f"{payload.get('event','unknown')}_{payload.get('account_id','')}_{payload.get('created_at','')}"
    )

    if already_processed(event_id):
        return {"status": "duplicate, ignored"}

    mark_processed(event_id)
    enqueue(payload)

    return {"status": "queued", "event": payload.get("event"), "entity_id": entity_id}

