"""
STATUS: stub, Day 6. Abstraction over whatever queue backs the async handoff between
webhook_receiver.py (producer) and worker.py (consumer) — Redis list, SQS, or Celery are all
fine choices; keep this interface stable so swapping the backend later doesn't touch the
handler or the worker.
"""


import os
import json
import logging
import queue

REDIS_URL = os.environ.get("REDIS_URL")
_redis_client = None
QUEUE_NAME = "vasooli_webhook_queue"

if REDIS_URL:
    try:
        import redis
        _redis_client = redis.Redis.from_url(REDIS_URL)
        _redis_client.ping()
    except Exception as e:
        logging.warning(f"Failed to connect to Redis at {REDIS_URL} for queue, falling back to local Queue: {e}")
        _redis_client = None

_local_queue = queue.Queue()


def enqueue(payload: dict) -> None:
    if _redis_client:
        try:
            _redis_client.rpush(QUEUE_NAME, json.dumps(payload))
            return
        except Exception as e:
            logging.error(f"Redis enqueue failed: {e}. Falling back to local Queue.")
    
    _local_queue.put(payload)


def dequeue() -> dict | None:
    if _redis_client:
        try:
            data = _redis_client.lpop(QUEUE_NAME)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logging.error(f"Redis dequeue failed: {e}. Falling back to local Queue.")
    
    try:
        return _local_queue.get_nowait()
    except queue.Empty:
        return None

