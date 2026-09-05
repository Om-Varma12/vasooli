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
import logging
from pathlib import Path
from . import classify as classify_layer
from .decide import decide
from .execute import execute
from .audit.audit_log import AuditLog
from .audit.dead_letter import write as dlq_write
from .models import FailureEvent, RootCause, Tier
from .enrichment.account_history import get_history, record_bounce, record_outcome
from .decide.budget_allocator import allocate
from .db_events import write_audit_entry, write_recovery_event

BATCH_PATH = Path(__file__).parent.parent.parent / "data" / "failed_payments_batch.json"


def load_batch(path: Path = BATCH_PATH) -> list[FailureEvent]:
    raw = json.loads(path.read_text())
    valid_fields = FailureEvent.__dataclass_fields__.keys()
    return [
        FailureEvent(
            **{k: v for k, v in r.items() if k in valid_fields},
            raw_payload=r
        ) for r in raw
    ]


def run_one(event: FailureEvent, audit: AuditLog) -> dict:
    # 0. Initialize record in DB to satisfy foreign key constraints for audit logs
    write_recovery_event(
        record_id=event.record_id,
        customer_id=event.customer_id,
        merchant_id=event.merchant_id,
        amount_inr=event.amount_inr,
        root_cause="pending",
        channel="pending",
        tier="pending",
        status="pending",
        retry_count=event.retry_count_so_far,
        message=None,
        reason=None,
        amount_recovered=0.0,
        promise_captured=False,
        raw_payload=event.raw_payload,
        phone_number=event.phone_number
    )

    # 1. Fetch historical context for this customer
    history = get_history(event.customer_id)
    event.past_bounce_count = history["past_bounce_count"]
    event.past_bounce_reasons = history["past_bounce_reasons"]
    event.last_successful_charge_date = history["last_successful_charge_date"]
    event.channel_response_rates = history["channel_response_rates"]

    # 2. Classify first to determine if we should record a bounce
    root_cause, classify_reason, confidence, source = classify_layer.classify(event)
    write_audit_entry(event.record_id, "classify", f"[{source}, confidence={confidence:.2f}] {classify_reason}")
    audit.write(event.record_id, "classify", f"[{source}, confidence={confidence:.2f}] {classify_reason}")

    if root_cause != RootCause.CANCELLATION_INTENT:
        record_bounce(event.customer_id, event.reason_code)

    # 3. Decide strategy
    decision = decide(event, root_cause)
    write_audit_entry(event.record_id, "policy", decision.reason)
    audit.write(event.record_id, "policy", decision.reason)

    # 4. Execute
    result = execute(event, decision)
    write_audit_entry(event.record_id, f"execute:{result['channel']}", result["detail"])
    audit.write(event.record_id, f"execute:{result['channel']}", result["detail"])

    # 5. Final Outcome
    outcome_detail = f"succeeded={result['succeeded']} amount_recovered_inr={result['amount_recovered_inr']}"
    write_audit_entry(event.record_id, "outcome", outcome_detail)
    audit.write(event.record_id, "outcome", outcome_detail)
    record_outcome(event.customer_id, result["channel"], result["succeeded"])

    # Mandate Sequencer Integration: Determine next state and retry time
    from .services.sequencer_service import SequencerService

    recovery_state = "RECOVERED" if result["succeeded"] else "RETRYING"
    # If not succeeded, check if we should actually stop (max retries)
    if not result["succeeded"]:
        # Create a mock object that matches RecoveryEvent for the service logic
        class MockEvent:
            def __init__(self, count, reason):
                self.retry_count = count
                self.last_failure_reason = reason

        mock_event = MockEvent(event.retry_count_so_far, result.get("detail", decision.reason))
        recovery_state = SequencerService.determine_next_state(mock_event)

        next_retry_at = None
        if recovery_state == "RETRYING":
            next_retry_at = SequencerService.calculate_next_retry(mock_event.last_failure_reason)
    else:
        next_retry_at = None

    # Derive status per tables.md: succeeded -> recovered; stopped -> stopped; handoff & not succeeded -> unresolved; else pending
    status = "pending"
    if result["succeeded"]:
        status = "recovered"
    elif recovery_state == "STOPPED":
        status = "stopped"
    elif decision.tier == Tier.HUMAN_HANDOFF and not result["succeeded"]:
        status = "unresolved"

    write_recovery_event(
        record_id=event.record_id,
        customer_id=event.customer_id,
        merchant_id=event.merchant_id,
        amount_inr=event.amount_inr,
        root_cause=root_cause.value,
        channel=result["channel"],
        tier=decision.tier.value,
        status=status,
        retry_count=event.retry_count_so_far,
        message=result.get("message"),
        reason=decision.reason,
        amount_recovered=result["amount_recovered_inr"],
        promise_captured=result.get("promise_captured", False),
        raw_payload=event.raw_payload,
        phone_number=event.phone_number,
        recovery_state=recovery_state,
        next_retry_at=next_retry_at,
        last_failure_reason=result.get("detail", decision.reason)
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


def run_batch(path: Path = BATCH_PATH, budget: dict[str, float] = None) -> list[dict]:
    """
    Process all events in the batch. Per-record exceptions are caught and written
    to the DLQ — one bad record no longer aborts the whole batch.
    """
    audit = AuditLog()
    events = load_batch(path)

    # If no budget, just process everything one by one as before
    if budget is None:
        results = []
        for event in events:
            try:
                results.append(run_one(event, audit))
            except Exception as exc:
                logging.error(f"[orchestrator] unhandled error for {event.record_id}: {exc}")
                dlq_write(record_id=event.record_id, stage="orchestrator", error=str(exc))
                results.append({
                    "record_id": event.record_id,
                    "merchant_id": event.merchant_id,
                    "category": event.category,
                    "root_cause": "unknown",
                    "tier": "human_handoff",
                    "amount_inr": event.amount_inr,
                    "channel": "dlq",
                    "succeeded": False,
                    "amount_recovered_inr": 0.0,
                    "detail": f"Unhandled exception — written to DLQ: {exc}",
                })
        return results

    # Budget-aware flow: 1. Enrich/Classify/Decide ALL -> 2. Allocate -> 3. Execute
    processed_events = []
    for event in events:
        try:
            history = get_history(event.customer_id)
            event.past_bounce_count = history["past_bounce_count"]
            event.past_bounce_reasons = history["past_bounce_reasons"]
            event.last_successful_charge_date = history["last_successful_charge_date"]
            event.channel_response_rates = history["channel_response_rates"]
            record_bounce(event.customer_id, event.reason_code)

            root_cause, classify_reason, confidence, source = classify_layer.classify(event)
            audit.write(event.record_id, "classify", f"[{source}, confidence={confidence:.2f}] {classify_reason}")

            decision = decide(event, root_cause)
            audit.write(event.record_id, "policy", decision.reason)

            processed_events.append((event, decision))
        except Exception as exc:
            logging.error(f"[orchestrator] decision failed for {event.record_id}: {exc}")
            dlq_write(record_id=event.record_id, stage="orchestrator_decision", error=str(exc))

    # Rank and filter decisions based on budget
    decisions_only = [d for _, d in processed_events]
    allowed_decisions = allocate(decisions_only, budget)

    # Create a map of allowed record_ids
    allowed_ids = {d.record_id for d in allowed_decisions}

    results = []
    for event, decision in processed_events:
        if event.record_id in allowed_ids:
            try:
                result = execute(event, decision)
                audit.write(event.record_id, f"execute:{result['channel']}", result["detail"])
                audit.write(event.record_id, "outcome", f"succeeded={result['succeeded']} amount_recovered_inr={result['amount_recovered_inr']}")
                record_outcome(event.customer_id, result["channel"], result["succeeded"])

                results.append({
                    "record_id": event.record_id,
                    "merchant_id": event.merchant_id,
                    "category": event.category,
                    "root_cause": decision.root_cause.value,
                    "tier": decision.tier.value,
                    "amount_inr": event.amount_inr,
                    **result,
                })
            except Exception as exc:
                logging.error(f"[orchestrator] execution failed for {event.record_id}: {exc}")
                dlq_write(record_id=event.record_id, stage="orchestrator_execute", error=str(exc))
        else:
            # Budgeted out
            results.append({
                "record_id": event.record_id,
                "merchant_id": event.merchant_id,
                "category": event.category,
                "root_cause": "budgeted_out",
                "tier": "stopped",
                "amount_inr": event.amount_inr,
                "channel": "none",
                "succeeded": False,
                "amount_recovered_inr": 0.0,
                "detail": "Budget limit reached for this channel; event deferred.",
            })

    return results
