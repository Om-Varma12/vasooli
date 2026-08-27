"""
STATUS: stub, Day 6. Sketch of the real Razorpay webhook handler — verify, dedupe, enqueue,
return fast. Nothing here runs yet; this is the shape to fill in when real Razorpay
test-mode credentials are wired.

Real version (FastAPI sketch — add fastapi/uvicorn to requirements.txt when you build this):

    from fastapi import FastAPI, Request, HTTPException
    from .signature import verify_signature
    from .dedupe_store import already_processed, mark_processed
    from .queue import enqueue

    app = FastAPI()

    @app.post("/webhooks/razorpay")
    async def receive(request: Request):
        body = await request.body()
        sig = request.headers.get("X-Razorpay-Signature", "")
        if not verify_signature(body, sig):
            raise HTTPException(status_code=400, detail="invalid signature")

        payload = await request.json()
        event_id = payload.get("event_id") or payload.get("id")
        if already_processed(event_id):
            return {"status": "duplicate, ignored"}   # still 2xx — do NOT reprocess

        mark_processed(event_id)
        enqueue(payload)          # hand off, don't classify/decide/execute inline
        return {"status": "queued"}

Handler does exactly three things and nothing else: verify, dedupe, enqueue. Everything
downstream (classify/decide/execute) happens in worker.py, off the request path, so this
handler stays fast regardless of what an LLM call or a slow channel API is doing.
"""
