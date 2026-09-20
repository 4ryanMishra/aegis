"""
Tests for Cross-Oracle End-to-End Scenarios and Python Integration
"""

import pytest
from packages.client.scenario_runner import (
    run_scenario_1,
    run_scenario_2,
    run_scenario_3,
    run_scenario_4,
    run_scenario_5,
    run_all_scenarios,
    run_scenario_a,
    run_scenario_b,
    run_scenario_c,
    run_scenario_d,
    run_scenario_e,
)
from services.api.src.models.schema import DecisionState


def test_scenario_a_normal_operation():
    res = run_scenario_a()
    assert res["decision"]["state"] == DecisionState.HEALTHY_CONSENSUS
    assert res["decision"]["protocol_state"] == "NORMAL"
    assert res["decision"]["effective_ltv"] == 0.80
    assert abs(res["decision"]["final_price"] - 4320.0) < 5.0


def test_scenario_b_flash_crash():
    res = run_scenario_b()
    assert res["decision"]["state"] == DecisionState.MULTIPLI_DEVIATION
    assert res["decision"]["protocol_state"] == "RESTRICTED"
    assert res["decision"]["effective_ltv"] == 0.50
    assert res["decision"]["final_price"] < 4300.0  # Captures market drop, not stale Multipli 4380


def test_scenario_c_poisoned_validator():
    res = run_scenario_c()
    # Outlier oracle injection of $9,000 is isolated by clustering; consensus is at ~4320.0
    assert abs(res["consensus"]["consensus_price"] - 4320.0) < 5.0
    assert res["decision"]["state"] in (DecisionState.HEALTHY_CONSENSUS, "OUTLIER_DETECTED")
    assert len(res["consensus"]["outlier_members"]) == 1


def test_scenario_d_market_dislocation():
    res = run_scenario_d()
    assert res["decision"]["state"] in (DecisionState.NO_CONSENSUS, DecisionState.MARKET_CORROBORATED, DecisionState.ORACLE_INSTABILITY)
    assert res["decision"]["effective_ltv"] <= 0.50


def test_scenario_e_osm_failure():
    res = run_scenario_e()
    assert res["decision"]["state"] in (DecisionState.SOURCE_DEGRADED, DecisionState.HEALTHY_CONSENSUS)
    assert res["consensus"]["cluster_size"] >= 4
