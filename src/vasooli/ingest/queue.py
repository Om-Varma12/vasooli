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

class InMemoryRedis:
    def __init__(self):
        self._store = {}
        self._lists = {}

    def ping(self):
        return True

    def rpush(self, name, value):
        if name not in self._lists:
            self._lists[name] = []
        self._lists[name].append(value)

    def lpop(self, name):
        if name in self._lists and self._lists[name]:
            return self._lists[name].pop(0)
        return None

    def blpop(self, name, timeout=0):
        val = self.lpop(name)
        if val is not None:
            return (name, val)
        if timeout > 0:
            import time
            time.sleep(timeout)
        return None

    def exists(self, name):
        return name in self._store

    def set(self, name, value, ex=None):
        self._store[name] = value

    def get(self, name):
        return self._store.get(name)

_in_memory_client = InMemoryRedis()

def get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not REDIS_URL:
        logging.warning("[queue] REDIS_URL not set. Falling back to in-memory queue.")
        _redis_client = _in_memory_client
        return _redis_client

    try:
        import redis
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as e:
        logging.warning(f"[queue] Could not connect to Redis at {REDIS_URL}: {e}. Falling back to in-memory queue.")
        _redis_client = _in_memory_client
        return _redis_client

def _get_client():
    return get_redis_client()

def enqueue(payload: dict) -> None:
    """Pushes a webhook payload to the Redis list.
    If Redis is down, writes to the Dead Letter Queue (DLQ) to prevent event loss.
    """
    client = _get_client()
    try:
        client.rpush(QUEUE_NAME, json.dumps(payload))
    except Exception as e:
        logging.error(f"Redis enqueue failed: {e}. Writing to DLQ.")
        try:
            from ..audit.dead_letter import write as dlq_write
            # Use a fallback record_id for DLQ if available, else 'system_error'
            record_id = payload.get("id") or payload.get("event_id") or "system_error"
            dlq_write(record_id=record_id, stage="enqueue", error=str(e))
        except Exception as dlq_e:
            logging.error(f"DLQ write also failed: {dlq_e}")
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
