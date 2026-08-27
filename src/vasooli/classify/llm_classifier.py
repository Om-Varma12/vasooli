"""
Tier-2 classification: LLM fallback for whatever the rule tier couldn't confidently bucket
(reason_code == "unclassified_bank_response" in the synthetic batch, ~8% of records).

STATUS: stub. Not calling a live API yet so `scripts/run_demo.py` runs with zero credentials
configured — see README "Day 2" for wiring this up for real. Replace the body of
`_call_llm` with a real Anthropic API call; keep the return shape (RootCause, reason, confidence).

Confidence threshold: anything below CONFIDENCE_THRESHOLD should route to a human-review
queue rather than silently proceeding on a guess (feature list point 7) — that queue doesn't
exist yet either; `orchestrator.py` currently just logs low-confidence cases to the audit
trail. Wire the real queue at the same time you wire the real API call.
"""
from ..models import RootCause

CONFIDENCE_THRESHOLD = 0.6

PROMPT_SKETCH = """\
Given this raw bank/NPCI decline signal and context: {event}

Classify the root cause into exactly one of:
insufficient_funds, bank_downtime, mandate_expired, risk_block

(cancellation_intent is handled separately and should never be returned here.)

Return the label and a confidence between 0 and 1.
"""


def classify_by_llm(event) -> tuple[RootCause, str, float]:
    cause, reason, confidence = _call_llm(event)
    if confidence < CONFIDENCE_THRESHOLD:
        reason += (
            f" [confidence {confidence:.2f} below threshold {CONFIDENCE_THRESHOLD} — "
            "should route to human-review queue, not yet wired, see docstring]"
        )
    return cause, reason, confidence


def _call_llm(event) -> tuple[RootCause, str, float]:
    """Stub — wire a real Anthropic API call here. See PROMPT_SKETCH above for the prompt shape."""
    return (
        RootCause.UNKNOWN,
        f"LLM fallback stub — reason_code='{event.reason_code}' did not match a rule; "
        f"defaulted to UNKNOWN (wire real classification call before Day 6 demo)",
        0.0,
    )
