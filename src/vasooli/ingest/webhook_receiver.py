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

    event_id = payload.get("id") or payload.get("event_id")
    if not event_id:
        raise HTTPException(status_code=400, detail="missing event identifier")

    if already_processed(event_id):
        return {"status": "duplicate, ignored"}

    mark_processed(event_id)
    enqueue(payload)
    
    return {"status": "queued"}
