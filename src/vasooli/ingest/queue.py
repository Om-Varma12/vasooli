"""
STATUS: stub, Day 6. Abstraction over whatever queue backs the async handoff between
webhook_receiver.py (producer) and worker.py (consumer) — Redis list, SQS, or Celery are all
fine choices; keep this interface stable so swapping the backend later doesn't touch the
handler or the worker.
"""


def enqueue(payload: dict) -> None:
    raise NotImplementedError("Queue not yet wired — see module docstring.")


def dequeue() -> dict | None:
    raise NotImplementedError("Queue not yet wired — see module docstring.")
