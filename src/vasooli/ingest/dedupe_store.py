"""
STATUS: stub, Day 6. Razorpay delivers webhooks at-least-once, retrying failed deliveries
with exponential backoff for 24 hours — so the same event WILL arrive more than once under
normal operation, not just as an edge case. Dedupe on Razorpay's event ID before any
downstream processing, or a slow response under load causes duplicate WhatsApp sends or
duplicate voice calls to the same customer.

Real implementation: Redis SETNX with a short TTL (a few days covers the 24h retry window
with margin), or a DB unique constraint on event_id if you don't want a Redis dependency yet.

    import redis
    r = redis.Redis()

    def already_processed(event_id: str) -> bool:
        return not r.set(f"seen:{event_id}", "1", nx=True, ex=60 * 60 * 24 * 3)  # 3-day TTL
"""

import os
import logging
from threading import Lock

REDIS_URL = os.environ.get("REDIS_URL")
_redis_client = None

if REDIS_URL:
    try:
        import redis
        _redis_client = redis.Redis.from_url(REDIS_URL)
        _redis_client.ping()
    except Exception as e:
        logging.warning(f"Failed to connect to Redis at {REDIS_URL}, falling back to in-memory: {e}")
        _redis_client = None

_seen_in_memory = set()
_lock = Lock()


def already_processed(event_id: str) -> bool:
    if not event_id:
        return False
    if _redis_client:
        try:
            return bool(_redis_client.exists(f"seen:{event_id}"))
        except Exception as e:
            logging.error(f"Redis check failed: {e}. Falling back to in-memory check.")
    
    with _lock:
        return event_id in _seen_in_memory


def mark_processed(event_id: str) -> None:
    if not event_id:
        return
    if _redis_client:
        try:
            _redis_client.set(f"seen:{event_id}", "1", ex=60 * 60 * 24 * 3)  # 3-day TTL
            return
        except Exception as e:
            logging.error(f"Redis mark failed: {e}. Falling back to in-memory mark.")
            
    with _lock:
        _seen_in_memory.add(event_id)

