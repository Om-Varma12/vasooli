"""
Aggregates the orchestrator's output into the numbers the 5-minute video needs: ₹ recovered,
recovery rate, a funnel by tier, cost per recovered rupee, and an honest exception list.
Cost assumptions come from config/channel_costs.yaml — the SAME file the decide layer's
voice cost gate reads, so these numbers can't silently drift apart.

Point 16 from the feature review (outcome-driven metric computation as a scheduled job over
the batch, not calculated ad hoc) — this module is already structured that way: it takes a
finished batch of outcomes and computes metrics as a separate step, not inline during
execution. Wiring it as an actual scheduled job (cron/Celery beat) is a Day 6+ concern once
there's a live stream of records rather than one static batch.
"""
from collections import defaultdict
from ..decide.cost_gate import assumed_cost_inr


def build_report(results: list[dict]) -> dict:
    total_at_risk = sum(r["amount_inr"] for r in results)
    total_recovered = sum(r["amount_recovered_inr"] for r in results)
    total_cost = sum(assumed_cost_inr(r["channel"]) for r in results)

    funnel = defaultdict(lambda: {"count": 0, "recovered_inr": 0.0})
    for r in results:
        funnel[r["tier"]]["count"] += 1
        funnel[r["tier"]]["recovered_inr"] += r["amount_recovered_inr"]

    exceptions = [
        {
            "record_id": r["record_id"],
            "merchant_id": r["merchant_id"],
            "amount_inr": r["amount_inr"],
            "tier": r["tier"],
            "root_cause": r["root_cause"],
            "why_unresolved": r["detail"],
        }
        for r in results
        if not r["succeeded"]
    ]

    return {
        "records_processed": len(results),
        "total_at_risk_inr": round(total_at_risk, 2),
        "total_recovered_inr": round(total_recovered, 2),
        "recovery_rate_pct": round(100 * total_recovered / total_at_risk, 2) if total_at_risk else 0.0,
        "total_channel_cost_inr": round(total_cost, 2),
        "cost_inr_per_1000_recovered": round(1000 * total_cost / total_recovered, 4) if total_recovered else None,
        "funnel_by_tier": {k: {"count": v["count"], "recovered_inr": round(v["recovered_inr"], 2)}
                            for k, v in funnel.items()},
        "exceptions_count": len(exceptions),
        "exceptions_sample": exceptions[:5],
    }


def print_report(report: dict) -> None:
    print("\n" + "=" * 60)
    print("VASOOLI — RECOVERY BATCH REPORT")
    print("=" * 60)
    print(f"Records processed:      {report['records_processed']}")
    print(f"₹ at risk:              ₹{report['total_at_risk_inr']:,.2f}")
    print(f"₹ recovered:            ₹{report['total_recovered_inr']:,.2f}")
    print(f"Recovery rate:          {report['recovery_rate_pct']}%")
    print(f"Channel cost:           ₹{report['total_channel_cost_inr']:,.2f}")
    if report["cost_inr_per_1000_recovered"] is not None:
        print(f"Cost per ₹1,000 recovered: ₹{report['cost_inr_per_1000_recovered']:.4f}")
    print("\nFunnel by tier:")
    for tier, stats in report["funnel_by_tier"].items():
        print(f"  {tier:15s} count={stats['count']:3d}   recovered=₹{stats['recovered_inr']:,.2f}")
    print(f"\nUnresolved (exceptions): {report['exceptions_count']} — showing up to 5:")
    for e in report["exceptions_sample"]:
        print(f"  [{e['record_id']}] {e['merchant_id']} ₹{e['amount_inr']:,.0f} "
              f"tier={e['tier']} cause={e['root_cause']}")
    print("=" * 60 + "\n")
