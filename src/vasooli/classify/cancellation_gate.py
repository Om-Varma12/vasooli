"""
Cancellation-intent gate. This is the one classification decision that has to be correct
every single time, so it is deliberately its OWN small function with its own tiny lookup —
not a branch inside the rule classifier and not something that could ever fall through to
the LLM tier. If the rule/LLM classifiers below have a bug, this gate is unaffected, because
it doesn't call into them and they don't call into it.

This is checked again, independently, as decide-layer guard clause #1 (see
src/vasooli/decide/guard_clauses.py). That's intentional duplication, not redundancy —
defense in depth for the one thing this system must never get wrong.
"""

# Reason codes that mean "this customer is gone," not "this customer had a hiccup."
CANCELLATION_REASON_CODES = frozenset({
    "mandate_cancelled_by_user",
    "account_closed",
})


def is_cancellation_intent(event) -> bool:
    return event.reason_code in CANCELLATION_REASON_CODES
