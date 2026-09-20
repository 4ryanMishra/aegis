import pytest
from services.api.src.core.coordinator import VerificationCoordinator
from services.api.src.models.schema import ScenarioRunRequest


def test_coordinator_scenario_run():
    coordinator = VerificationCoordinator()
    scenarios = coordinator.list_scenarios()
    assert len(scenarios) >= 3

    req = ScenarioRunRequest(
        scenario_id="scen_gold_osm_spike_01",
        ltv_factor=0.60,
        custom_seed=42,
        step_seconds=3600
    )
    result = coordinator.run_scenario(req)

    assert result.scenario_id == "scen_gold_osm_spike_01"
    assert result.window.is_finalized is True
    assert result.p_osm.value == 100.0
    assert result.p_market.value == 95.0
    assert result.p_dec.value is not None
    assert len(result.validators) == 5
    assert result.collateral.difference > 0
