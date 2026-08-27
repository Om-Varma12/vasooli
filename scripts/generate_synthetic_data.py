"""
Generates data/failed_payments_batch.json — a 60-record synthetic batch spanning
UPI Autopay subscriptions, eNACH EMIs, SIP mandates, and B2B receivables.

Distributions are a reasonable approximation for a demo, not a claim of real-world
ground truth — say so out loud if asked in the panel review.

Run from repo root: python scripts/generate_synthetic_data.py
"""
import json
import random
from pathlib import Path

random.seed(42)  # reproducible batch — same numbers every run, easier to demo/debug

MERCHANTS = [
    {"id": "merchant_ott_101", "name": "StreamFlix (OTT)", "category": "subscription"},
    {"id": "merchant_nbfc_202", "name": "QuickLoan NBFC", "category": "emi"},
    {"id": "merchant_invest_303", "name": "WealthSIP", "category": "sip"},
    {"id": "merchant_b2b_404", "name": "BuildMart Wholesale", "category": "b2b_receivable"},
]

REASON_PROFILE = [
    ("insufficient_funds", 0.30),
    ("bank_downtime", 0.12),
    ("mandate_expired", 0.15),
    ("risk_block", 0.10),
    ("mandate_cancelled_by_user", 0.10),
    ("account_closed", 0.05),
    ("otp_timeout", 0.10),
    ("unclassified_bank_response", 0.08),  # deliberately ambiguous -> exercises LLM fallback
]

def weighted_choice(pairs):
    reasons, weights = zip(*pairs)
    return random.choices(reasons, weights=weights, k=1)[0]


def gen_record(i: int) -> dict:
    merchant = random.choice(MERCHANTS)
    category = merchant["category"]

    if category == "b2b_receivable":
        payment_method = "enach"
        webhook_event = random.choice(["invoice.expired", "invoice.partially_paid"])
        amount = round(random.uniform(15000, 250000), 2)
        days_overdue = random.randint(5, 90)
        retry_count = 0
    else:
        payment_method = "upi_autopay" if category in ("subscription", "sip") else random.choice(["upi_autopay", "enach"])
        webhook_event = random.choice(["payment.failed", "subscription.pending", "subscription.halted"])
        amount = round(random.uniform(199, 15000) if category != "emi" else random.uniform(2000, 45000), 2)
        days_overdue = 0
        retry_count = 0 if webhook_event != "subscription.halted" else 3

    reason_code = weighted_choice(REASON_PROFILE)
    risk_tier = random.choices(
        ["high_value", "standard", "low_value"], weights=[0.2, 0.5, 0.3], k=1
    )[0]
    dnd_flag = random.random() < 0.15

    return {
        "record_id": f"rec_{i:04d}",
        "merchant_id": merchant["id"],
        "merchant_name": merchant["name"],
        "customer_id": f"cust_{random.randint(1000, 9999)}",
        "payment_method": payment_method,
        "category": category,
        "amount_inr": amount,
        "webhook_event": webhook_event,
        "reason_code": reason_code,
        "retry_count_so_far": retry_count,
        "customer_risk_tier": risk_tier,
        "dnd_flag": dnd_flag,
        "days_overdue": days_overdue,
    }


def main():
    batch = [gen_record(i) for i in range(1, 61)]
    out_path = Path(__file__).parent.parent / "data" / "failed_payments_batch.json"
    out_path.write_text(json.dumps(batch, indent=2))
    print(f"Wrote {len(batch)} records to {out_path}")


if __name__ == "__main__":
    main()
