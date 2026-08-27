"""
STATUS: stub, cheap to build, not yet wired.

A queue for events the pipeline couldn't classify, decide on, or execute, with enough
context to debug later — as opposed to silently dropping them or crashing the batch. This
is a small addition that's disproportionately valuable to show a panel: it's the difference
between "we didn't think about failure" and "we did, here's where it goes."

Not wired into orchestrator.py yet because nothing in the current pipeline actually raises
an unhandled exception mid-record on the synthetic batch — wire this when the real
webhook listener (Day 6) introduces real failure modes: a malformed payload, a Razorpay
entity-fetch timeout, a WhatsApp API 500, etc.
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

DLQ_PATH = Path(__file__).parent.parent.parent.parent / "data" / "dead_letter.jsonl"


@dataclass
class DeadLetterEntry:
    record_id: str
    stage: str          # "ingest" | "enrich" | "classify" | "decide" | "execute"
    error: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


def write(record_id: str, stage: str, error: str, path: Path = DLQ_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = DeadLetterEntry(record_id=record_id, stage=stage, error=error)
    with path.open("a") as f:
        f.write(json.dumps(asdict(entry)) + "\n")
