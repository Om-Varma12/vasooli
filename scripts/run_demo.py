"""
Single entrypoint for the 5-minute video demo.

    python scripts/generate_synthetic_data.py   # once, or whenever you want a fresh batch
    python scripts/run_demo.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.orchestrator import run_batch
from vasooli.report import build_report, print_report


def main():
    random.seed(7)  # fixed seed -> same numbers every run, so the video demo is repeatable
    results = run_batch()
    report = build_report(results)
    print_report(report)

    print("Sample audit trail for one voice-escalated record (if any):")
    voice_records = [r for r in results if r["channel"] == "voice"]
    if voice_records:
        r = voice_records[0]
        print(f"\n[{r['record_id']}] root_cause={r['root_cause']} amount=₹{r['amount_inr']:,.0f}")
        print("Transcript:")
        print(r.get("transcript", "(no transcript)"))
    else:
        print("(none escalated to voice in this batch — check config/rules_table.yaml thresholds)")

    print("\nSample graceful-failure (cancellation intent, correctly stopped):")
    stopped = [r for r in results if r["tier"] == "stopped"]
    if stopped:
        r = stopped[0]
        print(f"[{r['record_id']}] {r['detail']}")
    else:
        print("(none in this batch)")


if __name__ == "__main__":
    main()
