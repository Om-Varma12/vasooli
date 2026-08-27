"""
STATUS: stub package, Day 6 work. Currently `scripts/run_demo.py` reads a static synthetic
batch directly — this package is where that gets replaced with a real Razorpay test-mode
webhook listener, WITHOUT changing anything downstream (classify/decide/execute don't know
or care whether an event came from a JSON file or a live webhook — both produce the same
FailureEvent shape defined in models.py). That's the point of ingest being its own layer.

Design, per the feature review (points 1-3):
  1. webhook_receiver.py — the HTTP handler. Verifies signature (signature.py) first,
     dedupes on Razorpay's event ID (dedupe_store.py) second, pushes onto a queue
     (queue.py) third, returns 2xx immediately. Does NOT classify/decide/execute inline —
     Razorpay expects a fast response (5-second window) and a blocking LLM call in the
     handler will cause Razorpay to mark deliveries as failed and retry them, which under
     dedupe compounds rather than resolves the problem.
  2. A worker (src/vasooli/worker.py, also a stub) pulls off the queue and runs the
     classify -> decide -> execute -> audit pipeline per event, async from the HTTP handler.
"""
