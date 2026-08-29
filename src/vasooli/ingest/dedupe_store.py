"""
Redis-backed deduplication store.
Razorpay delivers webhooks at-least-once; we use Redis SETNX with a short TTL
to ensure a single event is not processed multiple times across multiple receiver instances.
"""

import os
import logging
from dotenv import load_dotenv

# Load .env to ensure REDIS_URL is available
load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL")
_redis_client = None

def _get_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not REDIS_URL:
        raise RuntimeError(
            "REDIS_URL environment variable is not set. "
            "Vasooli requires Redis for cross-process deduplication."
        )

    try:
        import redis
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as e:
        raise RuntimeError(f"Could not connect to Redis at {REDIS_URL}: {e}")

def already_processed(event_id: str) -> bool:
    """Checks if an event has already been processed using Redis."""
    if not event_id:
        return False

    client = _get_client()
    try:
        # If the key exists, it's already been processed
        return bool(client.exists(f"seen:{event_id}"))
    except Exception as e:
        logging.error(f"Redis dedupe check failed: {e}")
        # In a real production system, you might decide whether to fail-open or fail-closed.
        # Here we log the error and return False to avoid blocking genuine events.
        return False

def mark_processed(event_id: str) -> None:
    """Marks an event as processed in Redis with a 3-day TTL."""
    if not event_id:
        return

    client = _get_client()
    try:
        # Set key with 3-day TTL (60*60*24*3)
        client.set(f"seen:{event_id}", "1", ex=60 * 60 * 24 * 3)
    except Exception as e:
        logging.error(f"Redis dedupe mark failed: {e}")
