"""
Budget-aware portfolio allocation: given a capped pool of outreach for the current run (e.g.
X WhatsApp sends, Y voice-minutes), rank ALL pending decisions by
    expected_recovery_value * recovery_probability / channel_cost
and only execute the ones above the cutoff this cycle; queue the rest for the next window.
"""
import logging
from ..models import Decision, Tier
from .rules_engine import load_rules

logger = logging.getLogger("vasooli.decide")

def allocate(decisions: list[Decision], budget: dict[str, float]) -> list[Decision]:
    """
    Ranks decisions by Expected Value / Cost (ROI) and returns the subset that
    fits within the provided budget.

    budget: e.g. {"whatsapp": 50, "voice": 10} meaning max 50 WhatsApps, 10 calls.
    """
    if not budget:
        # No budget constraints specified, execute everything
        return decisions

    # 1. Separate decisions by channel
    by_channel = {}
    for d in decisions:
        tier = d.tier.value
        if tier not in by_channel:
            by_channel[tier] = []
        by_channel[tier].append(d)

    # 2. For each channel, rank by ROI (Expected Value / Cost)
    final_decisions = []
    for channel, channel_decisions in by_channel.items():
        if channel == Tier.STOPPED.value or channel == Tier.HUMAN_HANDOFF.value:
            # Free channels, always include them
            final_decisions.extend(channel_decisions)
            continue

        # Load rules to get recovery probability for the root cause
        rules = load_rules()
        # Using a simple map for cost in this implementation
        costs = {
            "retry": 0.0,
            "whatsapp": 0.50,
            "voice": 15.00,
        }

        # Rank decisions based on (amount * prob) / cost
        scored_decisions = []
        for d in channel_decisions:
            prob = rules["voice_escalation"]["recovery_probability_by_cause"].get(d.root_cause.value, 0.2)
            # We use expected_recovery_inr as the core value metric
            roi = (d.expected_recovery_inr or 0.0) * prob / (costs.get(channel, 1.0) or 1.0) if costs.get(channel) != 0 else 999999
            scored_decisions.append((roi, d))

        # Sort by ROI descending
        scored_decisions.sort(key=lambda x: x[0], reverse=True)

        # Only take as many as the budget allows
        limit = budget.get(channel, float('inf'))
        final_decisions.extend([d for score, d in scored_decisions[:int(limit)]])

    return final_decisions
