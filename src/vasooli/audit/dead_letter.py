"""
Append-only Dead Letter Queue for events the pipeline could not process.

Every failed record lands here with enough context to debug and replay:
  - record_id  — the Razorpay event ID / synthetic batch ID
  - stage      — where in the pipeline the failure occurred
                 ("ingest" | "enrich" | "classify" | "decide" | "execute" | "worker")
  - error      — the exception message or structured reason code
  - payload    — optional raw payload dict for replay (omitted when not available)
  - timestamp  — UTC ISO-8601

Reading the DLQ:
    from vasooli.audit.dead_letter import read, read_by_stage
    all_entries = read()
    execute_failures = read_by_stage("execute")

CLI (inspect the DLQ without opening Python):
    python -m vasooli.audit.dead_letter
    python -m vasooli.audit.dead_letter --stage execute
"""
import json
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DLQ_PATH = Path(__file__).parent.parent.parent.parent / "data" / "dead_letter.jsonl"


@dataclass
class DeadLetterEntry:
    record_id: str
    stage: str          # "ingest" | "enrich" | "classify" | "decide" | "execute" | "worker"
    error: str
    payload: Optional[dict] = field(default=None)
    timestamp: str = field(default=None)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


def write(
    record_id: str,
    stage: str,
    error: str,
    path: Path = DLQ_PATH,
    payload: Optional[dict] = None,
) -> None:
    """Append one entry to the DLQ. Thread-safe because file.open("a") is atomic on append."""
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = DeadLetterEntry(record_id=record_id, stage=stage, error=error, payload=payload)
    with path.open("a") as f:
        f.write(json.dumps(asdict(entry), default=str) + "\n")


def read(path: Path = DLQ_PATH) -> list[dict]:
    """Return all DLQ entries as a list of dicts, oldest first."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def read_by_stage(stage: str, path: Path = DLQ_PATH) -> list[dict]:
    """Return DLQ entries filtered to a single pipeline stage."""
    return [e for e in read(path) if e.get("stage") == stage]


def print_dlq(path: Path = DLQ_PATH, stage: Optional[str] = None) -> None:
    """Pretty-print the DLQ to stdout. Optionally filter by stage."""
    entries = read_by_stage(stage, path) if stage else read(path)
    if not entries:
        print(f"Dead Letter Queue is empty{f' for stage={stage!r}' if stage else ''}.")
        return

    print(f"\n{'='*60}")
    print(f"VASOOLI — Dead Letter Queue  ({len(entries)} entries)")
    if stage:
        print(f"Filtered to stage: {stage!r}")
    print(f"{'='*60}")
    for e in entries:
        print(
            f"  [{e.get('timestamp', '?')}]  "
            f"record={e.get('record_id', '?')}  "
            f"stage={e.get('stage', '?')}  "
            f"error={e.get('error', '?')}"
        )
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # python -m vasooli.audit.dead_letter [--stage <stage>]
    stage_filter = None
    args = sys.argv[1:]
    if "--stage" in args:
        idx = args.index("--stage")
        if idx + 1 < len(args):
            stage_filter = args[idx + 1]
    print_dlq(stage=stage_filter)
