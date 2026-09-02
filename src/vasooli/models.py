"""
Single source of truth for the shapes moving through the pipeline.
Kept dependency-free (stdlib dataclasses only) so it's trivial to unit test.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PaymentMethod(str, Enum):
    UPI_AUTOPAY = "upi_autopay"
    ENACH = "enach"
    CARD = "card"


class Category(str, Enum):
    SUBSCRIPTION = "subscription"          # OTT / SaaS style recurring
    EMI = "emi"                            # NBFC / lending recurring
    SIP = "sip"                            # mutual fund SIP mandate
    B2B_RECEIVABLE = "b2b_receivable"       # overdue invoice, not a mandate


class RootCause(str, Enum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    BANK_DOWNTIME = "bank_downtime"
    MANDATE_EXPIRED = "mandate_expired"
    RISK_BLOCK = "risk_block"
    CANCELLATION_INTENT = "cancellation_intent"      # genuinely dead — never escalate
    UNKNOWN = "unknown"                              # goes to LLM fallback


class Tier(str, Enum):
    """The escalation ladder, in order. Never skip a tier without a logged reason."""
    RETRY = "retry"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    HUMAN_HANDOFF = "human_handoff"        # graceful stop, not an escalation
    STOPPED = "stopped"                    # terminal, no further action


@dataclass
class FailureEvent:
    """One row of the synthetic batch / one real Razorpay webhook, normalized."""
    record_id: str
    merchant_id: str
    customer_id: str
    payment_method: PaymentMethod
    category: Category
    amount_inr: float
    webhook_event: str                     # e.g. "subscription.pending", "payment.failed"
    reason_code: str                       # raw bank/NPCI decline code, pre-classification
    retry_count_so_far: int
    customer_risk_tier: str                # "high_value" | "standard" | "low_value"
    dnd_flag: bool
    days_overdue: int = 0                  # only meaningful for B2B_RECEIVABLE
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    past_bounce_count: int = 0
    past_bounce_reasons: list[str] = field(default_factory=list)
    last_successful_charge_date: Optional[str] = None
    channel_response_rates: dict[str, int] = field(default_factory=dict)
    raw_payload: Optional[dict] = None     # original input JSON for pipeline re-runs



@dataclass
class Decision:
    """Output of the policy engine for one FailureEvent."""
    record_id: str
    root_cause: RootCause
    tier: Tier
    reason: str                            # human-readable, goes straight into the audit log
    retry_after_minutes: Optional[int] = None
    expected_recovery_inr: Optional[float] = None
    blocked_by: Optional[str] = None       # e.g. "dnd_flag", "retry_ceiling", "cost_gate"


@dataclass
class AuditEntry:
    record_id: str
    step: str                              # "classify" | "policy" | "execute:<channel>" | "outcome"
    detail: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
