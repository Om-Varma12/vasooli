"""
Append-only audit log. One JSON line per step, per record. Never mutated, never
overwritten — if a decision needs correcting, a new entry is appended explaining the
correction; the old entry stays. Keyed to the real Razorpay entity ID once the real
webhook listener lands (Day 6) — currently keyed to record_id from the synthetic batch.
"""
import json
from dataclasses import asdict
from pathlib import Path
from ..models import AuditEntry

LOG_PATH = Path(__file__).parent.parent.parent.parent / "data" / "audit_log.jsonl"


class AuditLog:
    def __init__(self, path: Path = LOG_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Fresh file per run — good for demo reproducibility, WRONG for a real persistent
        # service. Remove this truncation before this ever runs against live traffic.
        self.path.write_text("")

    def write(self, record_id: str, step: str, detail: str) -> None:
        entry = AuditEntry(record_id=record_id, step=step, detail=detail)
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(entry), default=str) + "\n")

    def for_record(self, record_id: str) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text().splitlines()
        return [
            json.loads(line) for line in lines
            if json.loads(line)["record_id"] == record_id
        ]
