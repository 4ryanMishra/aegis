"""
Tests for Real-Time Simulation Engine (Phase 4D Upgrade).
Verifies:
- Authoritative simulation clock & acceleration
- Deterministic seeded continuous price stream
- Asynchronous validator node arrival
- Dynamic event feed and system interpretation
- Scenario state transitions (NORMAL, FLASH_CRASH, POISONED_VALIDATOR, MARKET_DISLOCATION, OSM_FAILURE)
"""

import pytest
from services.api.src.core.simulation_engine import SimulationEngine
from services.api.src.models.schema import OracleStatus


@pytest.fixture
def engine():
    return SimulationEngine()


def test_simulation_engine_initial_state(engine):
    engine.reset("scen_normal", ltv=0.80)
    snapshot = engine.get_snapshot()
    assert snapshot["scenario_id"] == "scen_normal"
    assert snapshot["simulation_time_seconds"] == 0.0
    assert snapshot["is_running"] is False
    assert snapshot["is_finalized"] is False
    assert snapshot["total_lanes_count"] == 5
    assert len(snapshot["events"]) > 0
    assert "interpretation" in snapshot


def test_simulation_engine_step_and_cadence(engine):
    engine.reset("scen_normal", ltv=0.80)
    
    # Step 900s (+15m)
    engine.step(900.0)
    snapshot = engine.get_snapshot()
    assert snapshot["simulation_time_seconds"] == 900.0
    assert snapshot["elapsed_minutes"] == 15
    assert snapshot["active_validators_count"] >= 5
    assert snapshot["active_lanes_count"] == 5
    assert len(snapshot["time_series"]) >= 15


def test_simulation_engine_flash_crash_trajectory(engine):
    engine.reset("scen_flash_crash", ltv=0.80)
    
    # Early in window (t = 120s): prices near 100
    engine.sim_time_seconds = 120.0
    early_snap = engine.get_snapshot()
    assert early_snap["p_osm"]["value"] == 100.0
    assert early_snap["p_market"]["value"] > 99.0

    # Late in window (t = 2400s): market dropped to ~93.50 while OSM stays stale @ 100.0
    engine.sim_time_seconds = 2400.0
    late_snap = engine.get_snapshot()
    assert late_snap["p_osm"]["value"] == 100.0
    assert late_snap["p_market"]["value"] < 95.0
    assert late_snap["evidence"]["oracle_status"] in (
        OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION,
        OracleStatus.SUSPECTED_INCONSISTENCY,
    )
    assert "collateral" in late_snap


def test_simulation_engine_poisoned_validator_isolation(engine):
    engine.reset("scen_poisoned_validator", ltv=0.80)
    engine.sim_time_seconds = 2400.0
    snap = engine.get_snapshot()
    
    # P_DEC robustly rejects the outlier and stays around 95.00
    assert abs(snap["p_dec"]["value"] - 95.0) < 1.0
    # Uncertainty is computed
    assert snap["p_dec_uncertainty_half_width"] > 0.0

    # Also test scen_scenario_c ($100.0)
    engine.reset("scen_scenario_c", ltv=0.80)
    engine.sim_time_seconds = 2400.0
    snap_c = engine.get_snapshot()
    assert abs(snap_c["p_dec"]["value"] - 100.0) < 1.0


def test_simulation_engine_market_dislocation(engine):
    engine.reset("scen_market_dislocation", ltv=0.80)
    engine.finalize()
    snap = engine.get_snapshot()
    assert snap["is_finalized"] is True
    assert snap["evidence"]["oracle_status"] == OracleStatus.HALTED_CIRCUIT_BREAKER
    assert snap["decision"]["action"] == "HALT"
    assert snap["decision"]["final_price"] == 0.0


def test_simulation_engine_osm_failure_fallback(engine):
    engine.reset("scen_osm_failure", ltv=0.80)
    engine.sim_time_seconds = 1800.0
    snap = engine.get_snapshot()
    assert snap["p_osm"]["value"] == 0.0
    assert snap["p_dec"]["value"] > 90.0
    assert snap["decision"]["selected_source"] == "P_DEC (FAILSAFE)"
    assert snap["decision"]["action"] == "RESTRICT"
