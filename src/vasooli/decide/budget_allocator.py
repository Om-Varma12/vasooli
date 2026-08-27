"""
STATUS: stub, explicitly deferred (see PROJECT_PLAN.md "Deferred / stretch" section).

Budget-aware portfolio allocation: given a capped pool of outreach for the current run (e.g.
X WhatsApp sends, Y voice-minutes), rank ALL pending decisions by
    expected_recovery_value * recovery_probability / channel_cost
and only execute the ones above the cutoff this cycle; queue the rest for the next window.

This is a materially different system shape than everything else in decide/ — it operates
on the whole pending batch at once rather than one event at a time, which means it has to
run AFTER decide() has produced a Decision for every event in the batch, not as part of a
single event's decision. Do not bolt this into decide()/rules_engine.py; it belongs as a
post-processing step the orchestrator calls once per batch/window.

Real reason this is deferred rather than skipped: it's the difference between "a decision
engine" and "a decision engine for an entire book," and it's the kind of question
("what happens at 10,000 events a day, more than your channel budget can cover in one run?")
worth having an honest answer to even if the answer is "not built yet, here's the design."
"""
from ..models import Decision


def allocate(decisions: list[Decision], budget: dict[str, float]) -> list[Decision]:
    """Not implemented. Would rank `decisions` by expected-value/cost and return only the
    subset within `budget` (e.g. {"whatsapp": 500, "voice": 50}), demoting the rest to a
    queued/deferred tier rather than executing them this cycle.
    """
    raise NotImplementedError(
        "Budget-aware allocation is deferred — see module docstring. "
        "Current orchestrator executes every decision immediately, unbudgeted."
    )
