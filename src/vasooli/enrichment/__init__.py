"""
STATUS: stub package, Day 2/6 work.

entity_fetch.py: calls Razorpay's Fetch Payment/Subscription API to get the full entity
(error_reason, error_source, etc.) beyond what the webhook payload alone carries. Falls back
to the webhook payload as-is if the API call fails or times out — degrade gracefully rather
than dropping the event.

account_history.py: a lightweight store keyed by customer/mandate ID tracking past bounce
count, past bounce reasons, last successful charge date, and per-channel response rate
(did WhatsApp ever work for this person, or only voice). Turns "diagnose this one event"
into "diagnose this event in context" — a first bounce and a fifth bounce on the same
mandate should not get the same treatment.
"""
