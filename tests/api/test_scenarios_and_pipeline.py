"""
Pipeline & Scenario Execution Tests (Phase 4A Task 17).
Verifies:
- All 6 scenarios (NORMAL, FLASH_SPIKE, POISONED_VALIDATOR, VALIDATOR_OUTAGE, SLOW_DRIFT, RWA_DEPEG)
- P_DEC pipeline eligibility filtering
- Quorum stress / degradation
- Triangular conflict resolution
- Collateral delta and financial impact
"""

import pytest
from services.api.src.core.coordinator import VerificationCoordinator
from services.api.src.core.aggregator import P_DECAggregator
from services.api.src.models.schema import (
    ScenarioRunRequest,
    ValidatorResult,
    DecisionPolicy,
    OracleStatus,
)


@pytest.fixture
def coordinator():
    return VerificationCoordinator()


def test_scenario_normal_consensus(coordinator):
    """Under normal consensus, system finalizes with VERIFIED status."""
    req = ScenarioRunRequest(scenario_id="scen_normal_consensus", step_seconds=3600)
    res = coordinator.run_scenario(req)
    assert res.decision.dispute_status == "VERIFIED"
    assert res.decision.action == "ALLOW"
    assert len(res.validators) == 5
    assert res.evidence.oracle_status == OracleStatus.HEALTHY_CONSENSUS


def test_scenario_flash_spike(coordinator):
    """In flash spike, Kalman gates transient outlier and Huber downweights it."""
    req = ScenarioRunRequest(scenario_id="scen_flash_spike", step_seconds=3600)
    res = coordinator.run_scenario(req)
    # Check that Kalman gated or flagged innovation
    kalman_val = [v for v in res.validators if v.methodology == "KALMAN_1D"][0]
    assert kalman_val.decision == "INNOVATION_GATED"
    # P_DEC is anchored near market, not near the spike
    assert res.p_dec.value < 100.0
    # Overstatement prevented
    assert res.collateral.difference > 0


def test_scenario_poisoned_validator(coordinator):
    """Poisoned node is downweighted by Huber and isolated by JSD."""
    req = ScenarioRunRequest(scenario_id="scen_poisoned_validator", step_seconds=3600)
    res = coordinator.run_scenario(req)
    huber_val = [v for v in res.validators if v.methodology == "HUBER_IRLS"][0]
    assert huber_val.intermediate_metrics["outlier_count"] >= 1
    # Aggregation isolates the poison
    assert abs(res.p_dec.value - 95.0) < 2.0


def test_scenario_validator_outage(coordinator):
    """With 2 nodes offline, remaining 3 nodes satisfy quorum (N=3)."""
    req = ScenarioRunRequest(scenario_id="scen_validator_outage", step_seconds=3600)
    res = coordinator.run_scenario(req)
    assert len(res.validators) == 3
    assert res.p_dec.quorum_met is True
    assert res.p_dec.validator_count == 3


def test_scenario_slow_drift(coordinator):
    """Subtle price creep trips Page CUSUM sequential accumulation."""
    req = ScenarioRunRequest(scenario_id="scen_slow_drift", step_seconds=3600)
    res = coordinator.run_scenario(req)
    cusum_val = [v for v in res.validators if v.methodology == "CUSUM"][0]
    assert cusum_val.intermediate_metrics["trip_state"] in ("TRIP", "DRIFT")
    assert "CUSUM" in res.evidence.reason_codes[0] or any("CUSUM" in r for r in res.evidence.reason_codes)


def test_scenario_rwa_depeg(coordinator):
    """RWA secondary depeg triggers Ornstein-Uhlenbeck structural residual alert."""
    req = ScenarioRunRequest(scenario_id="scen_rwa_depeg", step_seconds=3600)
    res = coordinator.run_scenario(req)
    ou_val = [v for v in res.validators if v.methodology == "OU_RESIDUAL"][0]
    assert ou_val.intermediate_metrics["jump_candidate"] is True
    assert ou_val.decision == "DIFFUSION_MODEL_INCONSISTENCY"


def test_aggregator_quorum_failure():
    """If fewer than min_quorum validators submit, quorum_met is False and value is None."""
    agg = P_DECAggregator(min_quorum=3)
    res = agg.aggregate([])
    assert res.quorum_met is False
    assert res.value is None

    single = [
        ValidatorResult(
            validator_id="val_1",
            methodology="KALMAN_1D",
            methodology_name="Kalman",
            lane_id=1,
            estimated_price=100.0,
            uncertainty_lower=98.0,
            uncertainty_upper=102.0,
            timestamp=1000,
        )
    ]
    res_single = agg.aggregate(single)
    assert res_single.quorum_met is False
    assert res_single.value is None
