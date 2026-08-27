import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from vasooli.execute.rate_limiter import RateLimiter, make_limiters, CHANNEL_LIMITS
from vasooli.execute import execute, _RATE_LIMITERS
from vasooli.audit.dead_letter import write as dlq_write, read, read_by_stage
from vasooli.models import Tier
from .conftest_helpers import make_event


# ── Rate Limiter unit tests ─────────────────────────────────────────────────

def test_rate_limiter_full_bucket_allows_acquire():
    rl = RateLimiter("test_channel", max_per_minute=60)
    assert rl.acquire() is True


def test_rate_limiter_empty_bucket_blocks():
    # Set capacity to 1 and drain it
    rl = RateLimiter("test_channel", max_per_minute=60)
    rl.tokens = 0.0
    assert rl.acquire() is False


def test_rate_limiter_refills_over_time():
    # Set to 60 rpm = 1 token/sec. Drain then wait ~1.1s
    rl = RateLimiter("test_channel", max_per_minute=60)
    rl.tokens = 0.0
    rl.last_refill = time.monotonic()
    time.sleep(1.1)
    assert rl.acquire() is True   # should have at least 1 token now


def test_rate_limiter_available_tracks_tokens():
    rl = RateLimiter("test_channel", max_per_minute=30)
    initial = rl.available()
    assert initial == 30.0
    rl.acquire()
    assert rl.available() < 30.0


def test_rate_limiter_thread_safe(tmp_path):
    """Hammer the limiter from multiple threads — must never go negative."""
    import threading
    rl = RateLimiter("test_thread", max_per_minute=100)
    results = []

    def worker():
        for _ in range(20):
            results.append(rl.acquire())

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # tokens must be >= 0 (never over-spent)
    assert rl.tokens >= 0.0
    # At most capacity (100) of the 200 acquire() calls should have succeeded
    assert sum(results) <= 100


def test_make_limiters_creates_one_per_channel():
    limiters = make_limiters()
    for channel in CHANNEL_LIMITS:
        assert channel in limiters
        assert isinstance(limiters[channel], RateLimiter)
        assert limiters[channel].max_per_minute == CHANNEL_LIMITS[channel]


# ── Execute layer rate-limit integration tests ──────────────────────────────

def test_execute_rate_limit_routes_to_dlq(tmp_path, monkeypatch):
    """When the bucket for 'whatsapp' is empty, execute() must return succeeded=False
    and write an entry to the DLQ."""
    # Drain the whatsapp bucket
    monkeypatch.setitem(_RATE_LIMITERS, "whatsapp", _make_empty_limiter("whatsapp"))

    dlq_file = tmp_path / "rl_dlq.jsonl"
    import vasooli.audit.dead_letter as dlq_mod
    original_write = dlq_mod.write

    def capture_write(record_id, stage, error, path=dlq_file, payload=None):
        original_write(record_id, stage, error, path=path, payload=payload)

    monkeypatch.setattr(dlq_mod, "write", capture_write)

    from vasooli.models import RootCause, Decision
    event = make_event(reason_code="mandate_expired", retry_count_so_far=0)
    decision = Decision(
        record_id=event.record_id,
        root_cause=RootCause.MANDATE_EXPIRED,
        tier=Tier.WHATSAPP,
        reason="Test — mandate expired, sending WhatsApp nudge.",
    )

    result = execute(event, decision)

    assert result["succeeded"] is False
    # message may contain "rate_limit" or "rate limit" depending on formatting
    assert "rate" in result["detail"].lower() and "limit" in result["detail"].lower()
    assert dlq_file.exists()
    entries = read(dlq_file)
    assert len(entries) == 1
    assert entries[0]["stage"] == "execute"
    assert "rate_limit_exceeded" in entries[0]["error"]


def test_execute_human_handoff_bypasses_rate_limiter(monkeypatch):
    """HUMAN_HANDOFF and STOPPED tiers must never be rate-limited."""
    monkeypatch.setitem(_RATE_LIMITERS, "human_handoff", _make_empty_limiter("human_handoff"))

    from vasooli.models import RootCause, Decision
    event = make_event(reason_code="mandate_cancelled_by_user")
    decision = Decision(
        record_id=event.record_id,
        root_cause=RootCause.CANCELLATION_INTENT,
        tier=Tier.HUMAN_HANDOFF,
        reason="Test — cancellation.",
    )

    result = execute(event, decision)
    # Should still route to human_handoff adapter normally
    assert result["channel"] == "human_handoff"
    assert "rate_limit" not in result["detail"].lower()


def _make_empty_limiter(channel: str) -> RateLimiter:
    """Return a RateLimiter whose bucket is fully depleted."""
    rl = RateLimiter(channel, max_per_minute=60)
    rl.tokens = 0.0
    return rl


# ── DLQ read / filter / write tests ─────────────────────────────────────────

def test_dlq_write_and_read(tmp_path):
    dlq_file = tmp_path / "test.jsonl"
    dlq_write("rec_001", "ingest", "bad signature", path=dlq_file)
    dlq_write("rec_002", "execute", "rate_limit_exceeded:voice", path=dlq_file)

    entries = read(dlq_file)
    assert len(entries) == 2
    assert entries[0]["record_id"] == "rec_001"
    assert entries[1]["error"] == "rate_limit_exceeded:voice"


def test_dlq_read_by_stage(tmp_path):
    dlq_file = tmp_path / "test.jsonl"
    dlq_write("rec_001", "ingest", "bad signature", path=dlq_file)
    dlq_write("rec_002", "execute", "rate_limit_exceeded:whatsapp", path=dlq_file)
    dlq_write("rec_003", "execute", "rate_limit_exceeded:voice", path=dlq_file)
    dlq_write("rec_004", "worker", "timeout", path=dlq_file)

    execute_entries = read_by_stage("execute", dlq_file)
    assert len(execute_entries) == 2
    assert all(e["stage"] == "execute" for e in execute_entries)

    ingest_entries = read_by_stage("ingest", dlq_file)
    assert len(ingest_entries) == 1


def test_dlq_read_empty_file(tmp_path):
    dlq_file = tmp_path / "empty.jsonl"
    assert read(dlq_file) == []


def test_dlq_write_includes_payload(tmp_path):
    dlq_file = tmp_path / "test.jsonl"
    payload = {"id": "evt_123", "event": "payment.failed"}
    dlq_write("rec_005", "ingest", "missing field", path=dlq_file, payload=payload)

    entries = read(dlq_file)
    assert entries[0]["payload"] == payload


def test_dlq_read_skips_malformed_lines(tmp_path):
    dlq_file = tmp_path / "corrupt.jsonl"
    dlq_file.write_text('{"record_id": "rec_good", "stage": "ingest", "error": "ok"}\nNOT_JSON\n')

    entries = read(dlq_file)
    assert len(entries) == 1
    assert entries[0]["record_id"] == "rec_good"


# ── Orchestrator DLQ wiring test ─────────────────────────────────────────────

def test_orchestrator_run_batch_routes_bad_record_to_dlq(tmp_path, monkeypatch):
    """A record that raises in run_one() must not abort run_batch(); it goes to DLQ."""
    import vasooli.orchestrator as orch
    from vasooli.audit.dead_letter import write as original_write

    dlq_file = tmp_path / "orch_dlq.jsonl"

    def capture_write(record_id, stage, error, path=dlq_file, payload=None):
        original_write(record_id, stage, error, path=path, payload=payload)

    # Patch where orchestrator.py bound dlq_write at import time
    monkeypatch.setattr(orch, "dlq_write", capture_write)

    # Build a two-event fake batch: first normal, second raises
    event_good = make_event(record_id="rec_good")
    event_bad = make_event(record_id="rec_bad", reason_code="insufficient_funds")

    original_run_one = orch.run_one

    def patched_run_one(event, audit):
        if event.record_id == "rec_bad":
            raise RuntimeError("Simulated pipeline crash")
        return original_run_one(event, audit)

    monkeypatch.setattr(orch, "run_one", patched_run_one)
    monkeypatch.setattr(orch, "load_batch", lambda path=None: [event_good, event_bad])

    results = orch.run_batch()

    assert len(results) == 2
    good_result = next(r for r in results if r["record_id"] == "rec_good")
    bad_result = next(r for r in results if r["record_id"] == "rec_bad")

    assert good_result["succeeded"] in (True, False)   # ran normally
    assert bad_result["succeeded"] is False
    assert bad_result["channel"] == "dlq"

    dlq_entries = read(dlq_file)
    assert len(dlq_entries) == 1
    assert dlq_entries[0]["record_id"] == "rec_bad"
    assert "Simulated pipeline crash" in dlq_entries[0]["error"]

