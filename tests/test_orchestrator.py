import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.orchestrator import run_one
from vasooli.audit.audit_log import AuditLog
from .conftest_helpers import make_event


def test_run_one_produces_audit_trail_with_all_four_steps(tmp_path):
    audit = AuditLog(path=tmp_path / "test_audit.jsonl")
    event = make_event(reason_code="insufficient_funds", retry_count_so_far=0)

    result = run_one(event, audit)

    assert result["record_id"] == event.record_id
    assert "channel" in result
    assert "amount_recovered_inr" in result

    trail = audit.for_record(event.record_id)
    steps = [entry["step"] for entry in trail]
    assert "classify" in steps
    assert "policy" in steps
    assert any(s.startswith("execute:") for s in steps)
    assert "outcome" in steps


def test_run_one_cancellation_case_never_reaches_a_paid_channel(tmp_path):
    audit = AuditLog(path=tmp_path / "test_audit_cancel.jsonl")
    event = make_event(reason_code="mandate_cancelled_by_user")

    result = run_one(event, audit)

    assert result["tier"] == "stopped"
    assert result["channel"] == "human_handoff"
    assert result["amount_recovered_inr"] == 0.0
