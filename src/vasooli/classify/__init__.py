from .cancellation_gate import is_cancellation_intent
from .rules_classifier import classify_by_rule
from .llm_classifier import classify_by_llm

__all__ = ["is_cancellation_intent", "classify_by_rule", "classify_by_llm", "classify"]


def classify(event):
    """
    Public entrypoint for the classify layer. Order matters:
      1. Cancellation gate — isolated, fast, runs first, own code path.
      2. Rule-tier — deterministic lookup, covers ~92% of the synthetic batch.
      3. LLM-tier fallback — only for what the rule tier can't confidently bucket.
    Returns (root_cause, reason, confidence, source) where source in {"gate","rule","llm"}.
    """
    from ..models import RootCause

    if is_cancellation_intent(event):
        return (
            RootCause.CANCELLATION_INTENT,
            f"Cancellation gate matched on reason_code='{event.reason_code}' — "
            "checked first, own code path, does not share failure modes with the "
            "rule/LLM classifiers below.",
            1.0,
            "gate",
        )

    rule_result = classify_by_rule(event)
    if rule_result is not None:
        cause, reason = rule_result
        return cause, reason, 1.0, "rule"

    cause, reason, confidence = classify_by_llm(event)
    return cause, reason, confidence, "llm"
