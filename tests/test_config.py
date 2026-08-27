import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vasooli.decide.rules_engine import load_rules
from vasooli.decide.cost_gate import assumed_cost_inr


def test_rules_table_loads_and_has_expected_causes():
    config = load_rules()
    causes_covered = {r["match"]["root_cause"] for r in config["rules"]}
    # cancellation_intent must NOT be in here — it's handled by guard clauses, never the table
    assert "cancellation_intent" not in causes_covered
    assert {"insufficient_funds", "bank_downtime", "risk_block", "mandate_expired", "unknown"} <= causes_covered


def test_channel_costs_single_source_of_truth():
    """decide/cost_gate.py and report/metrics.py both call assumed_cost_inr() from the same
    module — this test just confirms the loader works and returns sane values, guarding
    against the two layers silently drifting apart the way the pre-refactor constants did."""
    assert assumed_cost_inr("retry") == 0.0
    assert assumed_cost_inr("whatsapp") > 0.0
    assert assumed_cost_inr("voice") > assumed_cost_inr("whatsapp")
    assert assumed_cost_inr("nonexistent_channel") == 0.0  # safe default, doesn't raise


def test_voice_escalation_config_has_no_zero_probability_causes_missing():
    config = load_rules()
    probs = config["voice_escalation"]["recovery_probability_by_cause"]
    assert probs["cancellation_intent"] == 0.0  # documents intent: never worth calling
