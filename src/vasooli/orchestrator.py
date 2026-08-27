"""
Runs one FailureEvent, or a whole batch, through: classify -> decide -> execute -> audit.
This is the module `scripts/run_demo.py` calls for the batch/offline demo path.

The production path (Day 6+) is different in shape, not in logic: `worker.py` pulls one
event at a time off the ingest queue and calls `run_one()` below per event, continuously,
instead of `run_batch()` loading a static file once. Both paths share this exact function —
that's deliberate, so nothing about classify/decide/execute/audit needs to change when
ingest goes from "read a JSON file" to "consume a live queue."
"""
import json
from pathlib import Path
from . import classify as classify_layer
from .decide import decide
from .execute import execute
from .audit.audit_log import AuditLog
from .models import FailureEvent

BATCH_PATH = Path(__file__).parent.parent.parent / "data" / "failed_payments_batch.json"


def load_batch(path: Path = BATCH_PATH) -> list[FailureEvent]:
    raw = json.loads(path.read_text())
    valid_fields = FailureEvent.__dataclass_fields__.keys()
    return [FailureEvent(**{k: v for k, v in r.items() if k in valid_fields}) for r in raw]


def run_one(event: FailureEvent, audit: AuditLog) -> dict:
    root_cause, classify_reason, confidence, source = classify_layer.classify(event)
    audit.write(event.record_id, "classify", f"[{source}, confidence={confidence:.2f}] {classify_reason}")

    decision = decide(event, root_cause)
    audit.write(event.record_id, "policy", decision.reason)

    result = execute(event, decision)
    audit.write(event.record_id, f"execute:{result['channel']}", result["detail"])
    audit.write(
        event.record_id, "outcome",
        f"succeeded={result['succeeded']} amount_recovered_inr={result['amount_recovered_inr']}",
    )

    return {
        "record_id": event.record_id,
        "merchant_id": event.merchant_id,
        "category": event.category,
        "root_cause": root_cause.value,
        "tier": decision.tier.value,
        "amount_inr": event.amount_inr,
        **result,
    }


def run_batch(path: Path = BATCH_PATH) -> list[dict]:
    audit = AuditLog()
    events = load_batch(path)
    return [run_one(e, audit) for e in events]
