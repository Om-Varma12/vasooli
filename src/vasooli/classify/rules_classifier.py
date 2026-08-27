"""
Tier-1 classification: a deterministic lookup table on Razorpay's own `error_reason`-style
reason codes. This covers the large majority of records — in the synthetic batch, ~92% of
records match a rule here and never touch the LLM tier at all. That's the actual scalability
argument: calling an LLM per event is slow and needlessly expensive when most failures are a
lookup table away from being solved.

Note: cancellation-signal codes (mandate_cancelled_by_user, account_closed) are intentionally
NOT in this map — they're caught earlier by the cancellation gate and never reach here.
"""
from ..models import RootCause

RULE_MAP = {
    "insufficient_funds": RootCause.INSUFFICIENT_FUNDS,
    "bank_downtime": RootCause.BANK_DOWNTIME,
    "mandate_expired": RootCause.MANDATE_EXPIRED,
    "risk_block": RootCause.RISK_BLOCK,
    "otp_timeout": RootCause.INSUFFICIENT_FUNDS,  # treated as a transient retry-worthy signal
}


def classify_by_rule(event):
    """Returns (RootCause, reason_str) on a match, or None if no rule matches."""
    if event.reason_code in RULE_MAP:
        cause = RULE_MAP[event.reason_code]
        return cause, f"rule match on reason_code='{event.reason_code}'"
    return None
