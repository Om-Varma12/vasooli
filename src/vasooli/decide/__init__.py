"""
Public entrypoint for the decide layer: guard clauses first (unconditional, code-level),
then the config-driven rules table for anything that survives them.
"""
from ..models import FailureEvent, Decision, RootCause
from .guard_clauses import run_guard_clauses
from .rules_engine import evaluate

__all__ = ["decide"]


def decide(event: FailureEvent, root_cause: RootCause) -> Decision:
    guarded = run_guard_clauses(event, root_cause)
    if guarded is not None:
        return guarded
    return evaluate(event, root_cause)
