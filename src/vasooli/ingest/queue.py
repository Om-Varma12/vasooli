"""
Redis-backed queue for async handoff between webhook_receiver.py (producer) and worker.py (consumer).
This ensures that multiple processes (Receiver and Worker) can communicate via a shared broker.
"""

import os
import json
import logging
from dotenv import load_dotenv

# Load .env to ensure REDIS_URL is available
load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL")
QUEUE_NAME = "vasooli_webhook_queue"
_redis_client = None

def _get_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not REDIS_URL:
        raise RuntimeError(
            "REDIS_URL environment variable is not set. "
            "Vasooli requires Redis for cross-process communication between Receiver and Worker."
        )

    try:
        import redis
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as e:
        raise RuntimeError(f"Could not connect to Redis at {REDIS_URL}: {e}")

def enqueue(payload: dict) -> None:
    """Pushes a webhook payload to the Redis list."""
    client = _get_client()
    try:
        client.rpush(QUEUE_NAME, json.dumps(payload))
    except Exception as e:
        logging.error(f"Redis enqueue failed: {e}")
        raise

def dequeue(timeout: int = 5) -> dict | None:
    """
    Pops the next event from the Redis list.
    Uses BLPOP for efficient blocking wait.
    """
    client = _get_client()
    try:
        if timeout == 0:
            data = client.lpop(QUEUE_NAME)
            return json.loads(data) if data else None

        # blpop returns (key, value)
        res = client.blpop(QUEUE_NAME, timeout=timeout)
        if res:
            _, data = res
            return json.loads(data)
        return None
    except Exception as e:
        logging.error(f"Redis dequeue failed: {e}")
        return None
