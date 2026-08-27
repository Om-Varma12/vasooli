"""
STATUS: stub, Day 2/6. A lightweight table (SQLite is enough to start) keyed by
customer_id/mandate_id: past bounce count, past bounce reasons, last successful charge
date, per-channel response rate. Read by classify/decide to treat a first bounce and a
fifth bounce on the same mandate differently — not built yet; current pipeline treats every
record independently.
"""


def get_history(customer_id: str) -> dict:
    raise NotImplementedError("Account history store not yet wired — see module docstring.")


def record_outcome(customer_id: str, channel: str, succeeded: bool) -> None:
    raise NotImplementedError("Account history store not yet wired — see module docstring.")
