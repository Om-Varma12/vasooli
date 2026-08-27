# Razorpay webhook events this project is shaped against

Reference only — confirm exact payload fields against your Razorpay dashboard/docs before
wiring the real listener on Day 6, since Razorpay does version these.

## Payments
- `payment.authorized` — payment authorized, not yet captured
- `payment.captured` — payment successfully captured
- `payment.failed` — payment attempt failed or timed out. Not fired if failure happens during
  the very first authorisation attempt on some flows — don't assume this is the only failure
  signal.

## Subscriptions
- `subscription.authenticated` — mandate registered
- `subscription.charged` — a recurring charge succeeded
- `subscription.pending` — a charge attempt failed; subscription is in retry/pending state
- `subscription.halted` — retries exhausted (Razorpay's own subscriptions halt **after 3 retry
  attempts** post the original failure — this is the number our `policy_engine.py` retry
  ceiling mirrors, not an arbitrary choice)
- `subscription.paused` / `subscription.resumed`
- `subscription.cancelled`

## Invoices (used for the B2B receivables direction)
- `invoice.paid`
- `invoice.partially_paid`
- `invoice.expired`

## Notes for the ingest layer (Day 6)
- Webhook delivery is at-least-once with retries on non-2xx responses — the ingest layer must
  be idempotent on `event_id`, or a redelivered `payment.failed` will double-count in the
  report and could double-fire a WhatsApp/voice escalation. This is one of the Day 7 "Failure
  Recovery" scenarios to demo on purpose.
- Signature validation is mandatory before trusting any payload — don't skip this even in a
  demo, it's a five-minute add and "we validate webhook signatures" is a good line in the
  video.
