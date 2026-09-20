"""
Tests for Real-Time Cross-Oracle Simulation Engine.
Verifies:
- Authoritative simulation clock & acceleration
- Deterministic multi-oracle price feeds (Chainlink, Pyth, Chronicle, RedStone, Supra, API3, Multipli)
- Price-band agreement clustering
- Dynamic event feed and system interpretation
- Scenario state transitions:
  - Scenario A: scen_normal (Multi-Oracle Agreement)
  - Scenario B: scen_flash_crash (Multipli Delay During Drop)
  - Scenario C: scen_poisoned_validator (Single Outlier Isolation)
  - Scenario D: scen_market_dislocation (Crisis / Disagreement)
  - Scenario E: scen_osm_failure (Source Outage Resilience)
"""

import pytest
from services.api.src.core.simulation_engine import SimulationEngine
from services.api.src.models.schema import OracleStatus, DecisionState


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
    assert len(snapshot["oracle_sources"]) == 6
    assert len(snapshot["events"]) > 0
    assert "interpretation" in snapshot
    assert "consensus" in snapshot
    assert "decision" in snapshot
    assert "position" in snapshot


def test_simulation_engine_step_and_cadence(engine):
    engine.reset("scen_normal", ltv=0.80)
    
    # Step 900s (+15m)
    engine.step(900.0)
    snapshot = engine.get_snapshot()
    assert snapshot["simulation_time_seconds"] == 900.0
    assert snapshot["elapsed_minutes"] == 15
    assert len(snapshot["oracle_sources"]) == 6
    assert snapshot["consensus"]["cluster_size"] == 6
    assert len(snapshot["time_series"]) >= 15


def test_simulation_engine_flash_crash_trajectory(engine):
    engine.reset("scen_flash_crash", ltv=0.80)
    
    # Early in window (t = 120s): prices near 4320
    engine.sim_time_seconds = 120.0
    early_snap = engine.get_snapshot()
    assert early_snap["multipli_observation"]["price"] == 4380.0
    assert early_snap["market_observation"]["price"] > 4250.0

    # Late in window (t = 3600s): market dropped to 4050 while Multipli stays delayed @ 4380.0
    engine.sim_time_seconds = 3600.0
    late_snap = engine.get_snapshot()
    assert late_snap["multipli_observation"]["price"] == 4380.0
    assert late_snap["consensus"]["consensus_price"] <= 4055.0
    assert late_snap["decision"]["is_conservative_applied"] is True
    assert late_snap["decision"]["final_price"] <= 4055.0
    assert late_snap["decision"]["effective_ltv"] == 0.50


def test_simulation_engine_poisoned_validator_isolation(engine):
    engine.reset("scen_outlier", ltv=0.80)
    engine.sim_time_seconds = 2400.0
    snap = engine.get_snapshot()
    
    # Cluster median robustly rejects the $9,000 outlier and stays around 4050.00
    assert abs(snap["consensus"]["consensus_price"] - 4050.0) < 5.0
    assert snap["consensus"]["cluster_size"] == 5
    assert len(snap["consensus"]["outlier_members"]) == 1
    assert snap["decision"]["state"] == DecisionState.HEALTHY_CONSENSUS


def test_simulation_engine_market_dislocation(engine):
    engine.reset("scen_disagreement", ltv=0.80)
    engine.finalize()
    snap = engine.get_snapshot()
    assert snap["is_finalized"] is True
    assert snap["decision"]["state"] in (DecisionState.NO_CONSENSUS, DecisionState.MARKET_CORROBORATED, DecisionState.ORACLE_INSTABILITY)
    assert snap["decision"]["effective_ltv"] <= 0.50


def test_simulation_engine_osm_failure_fallback(engine):
    engine.reset("scen_outage", ltv=0.80)
    engine.sim_time_seconds = 1800.0
    snap = engine.get_snapshot()
    assert snap["consensus"]["cluster_size"] == 4
    assert snap["consensus"]["consensus_price"] > 4000.0
    assert snap["decision"]["state"] == DecisionState.HEALTHY_CONSENSUS


def test_simulation_engine_position_lifecycle(engine):
    # Initial state under normal conditions: 10 oz Gold @ $4320 -> $43,200 collateral, 80% LTV -> $34,560 max borrow
    engine.reset("scen_normal", ltv=0.80)
    snap0 = engine.get_snapshot()
    pos0 = snap0["position"]
    assert pos0["collateral_amount"] == 10.0
    assert pos0["debt_amount"] == 28000.0
    assert pos0["effective_ltv"] == 0.80
    assert pos0["position_status"] == "HEALTHY"
    assert "causal_chain" in snap0

    # Switch to flash crash: at t=3600s, market drops to ~4050, AEGIS enforces conservative $4050 and 50% LTV
    engine.reset("scen_flash_crash", ltv=0.80)
    engine.sim_time_seconds = 3600.0
    snap_crash = engine.get_snapshot()
    pos_crash = snap_crash["position"]
    assert pos_crash["effective_ltv"] == 0.50
    assert pos_crash["max_borrow_capacity"] < 21000.0
    assert pos_crash["position_status"] in ("RESTRICTED", "OVER_LIMIT")

    # Update position (deposit more collateral, e.g. 20 oz)
    engine.update_position(collateral_amount=20.0)
    snap_dep = engine.get_snapshot()
    assert snap_dep["position"]["collateral_amount"] == 20.0
    assert snap_dep["position"]["collateral_value"] > 80000.0

    # Borrow max capacity
    engine.update_position(set_max_borrow=True)
    snap_max = engine.get_snapshot()
    assert snap_max["position"]["debt_amount"] == snap_max["position"]["max_borrow_capacity"]
