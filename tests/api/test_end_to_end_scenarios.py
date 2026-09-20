"""
Tests for Phase 4C End-to-End Scenarios and Python Validator/Keeper Integration
"""

import pytest
import numpy as np
from packages.client.scenario_runner import (
    run_scenario_a,
    run_scenario_b,
    run_scenario_c,
    run_scenario_d,
    run_scenario_e,
    run_all_scenarios
)
from packages.client.validator_client import ValidatorNodeClient, LaneType
from packages.client.keeper_orchestrator import KeeperOrchestrator, OracleStatus, ProtocolActionState


def test_scenario_a_normal_operation():
    res = run_scenario_a()
    assert res.oracle_status == OracleStatus.HEALTHY_CONSENSUS
    assert res.protocol_state == ProtocolActionState.NORMAL
    assert abs(res.p_final - 100.0) < 1.0


def test_scenario_b_flash_crash():
    res = run_scenario_b()
    assert res.oracle_status in (OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION, OracleStatus.SUSPECTED_INCONSISTENCY)
    assert res.protocol_state == ProtocolActionState.RESTRICTED
    assert res.p_final < 96.0  # Captures real-time crash, not stale OSM 100


def test_scenario_c_poisoned_validator():
    res = run_scenario_c()
    # Outlier validator injection of 500.0 is suppressed by robust median
    assert res.p_dec < 110.0
    assert res.oracle_status == OracleStatus.HEALTHY_CONSENSUS
    assert res.protocol_state == ProtocolActionState.NORMAL


def test_scenario_d_market_dislocation():
    res = run_scenario_d()
    assert res.protocol_state in (ProtocolActionState.RESTRICTED, ProtocolActionState.HALTED)


def test_scenario_e_osm_failure():
    res = run_scenario_e()
    assert res.oracle_status in (OracleStatus.SUSPECTED_INCONSISTENCY, OracleStatus.HALTED_CIRCUIT_BREAKER)
    assert res.protocol_state in (ProtocolActionState.RESTRICTED, ProtocolActionState.HALTED)


def test_validator_client_commit_reveal_integrity():
    val = ValidatorNodeClient("op1", "0x1111111111111111111111111111111111111111", LaneType.LANE_1_KALMAN)
    out = val.execute_methodology(market_quotes=[100.0, 100.5, 99.8, 100.2])
    commit_hash, nonce, reveal_params = val.generate_commitment(
        round_id=1,
        chain_id=31337,
        manager_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
        methodology_output=out
    )
    assert len(commit_hash) == 32  # 32 bytes keccak256
    assert out["price"] > 0
    assert out["uncertainty_val"] >= 0
