"""
Unit and integration tests for Cross-Oracle Consensus and Risk Decision Engine (Python Layer).
"""

import pytest
from services.api.src.oracles.consensus_engine import ConsensusEngine, OracleObservationData
from services.api.src.oracles.risk_decision_engine import RiskDecisionEngine
from services.api.src.core.simulation_engine import SimulationEngine


def test_consensus_engine_price_band_clustering():
    engine = ConsensusEngine(cluster_tolerance_pct=0.50, min_quorum=3, min_agreement_ratio=0.60)

    # 6 feeds tightly clustered around 4320
    observations = [
        OracleObservationData("chainlink", "Chainlink", 4320.10, 1000, 4, "ACTIVE", None, False, True),
        OracleObservationData("pyth", "Pyth", 4319.90, 1000, 2, "ACTIVE", 0.15, True, True),
        OracleObservationData("chronicle", "Chronicle", 4321.20, 1000, 9, "ACTIVE", None, False, True),
        OracleObservationData("redstone", "RedStone", 4318.70, 1000, 6, "ACTIVE", None, False, True),
        OracleObservationData("supra", "Supra", 4320.40, 1000, 5, "ACTIVE", None, False, True),
        OracleObservationData("api3", "API3", 4319.80, 1000, 8, "ACTIVE", None, False, True),
    ]

    metrics = engine.compute_consensus(observations)
    assert metrics.total_eligible == 6
    assert metrics.cluster_size == 6
    assert metrics.agreement_ratio == 1.0
    assert metrics.has_strong_consensus is True
    assert abs(metrics.consensus_price - 4320.0) < 1.5
    assert metrics.cluster_spread_pct < 0.50


def test_consensus_engine_single_outlier_rejection():
    engine = ConsensusEngine(cluster_tolerance_pct=0.50, min_quorum=3, min_agreement_ratio=0.60)

    # 5 feeds agree @ 4050; 1 outlier @ 9000
    observations = [
        OracleObservationData("chainlink", "Chainlink", 4050.20, 1000, 4, "ACTIVE", None, False, True),
        OracleObservationData("pyth", "Pyth", 4051.00, 1000, 2, "ACTIVE", 0.12, True, True),
        OracleObservationData("chronicle", "Chronicle", 4049.80, 1000, 9, "ACTIVE", None, False, True),
        OracleObservationData("redstone", "RedStone", 9000.00, 1000, 6, "ACTIVE", None, False, True),  # Outlier
        OracleObservationData("supra", "Supra", 4050.70, 1000, 5, "ACTIVE", None, False, True),
        OracleObservationData("api3", "API3", 4051.40, 1000, 8, "ACTIVE", None, False, True),
    ]

    metrics = engine.compute_consensus(observations)
    assert metrics.total_eligible == 6
    assert metrics.cluster_size == 5
    assert metrics.has_strong_consensus is True
    assert "redstone" in metrics.outlier_members
    assert abs(metrics.consensus_price - 4050.85) < 1.0


def test_consensus_engine_bimodal_disagreement_halt():
    engine = ConsensusEngine(cluster_tolerance_pct=0.50, min_quorum=3, min_agreement_ratio=0.60)

    # Group A: 3 feeds @ 4050; Group B: 3 feeds @ 4450 (neither has > 60%)
    observations = [
        OracleObservationData("chainlink", "Chainlink", 4050.20, 1000, 4, "ACTIVE", None, False, True),
        OracleObservationData("pyth", "Pyth", 4051.00, 1000, 2, "ACTIVE", 0.12, True, True),
        OracleObservationData("chronicle", "Chronicle", 4049.80, 1000, 9, "ACTIVE", None, False, True),
        OracleObservationData("redstone", "RedStone", 4452.10, 1000, 6, "ACTIVE", None, False, True),
        OracleObservationData("supra", "Supra", 4450.70, 1000, 5, "ACTIVE", None, False, True),
        OracleObservationData("api3", "API3", 4451.40, 1000, 8, "ACTIVE", None, False, True),
    ]

    metrics = engine.compute_consensus(observations)
    assert metrics.has_strong_consensus is False  # 3/6 = 50% < 60% requirement


def test_risk_decision_engine_multipli_divergence_conservative():
    decision_engine = RiskDecisionEngine(normal_threshold_pct=0.50, critical_threshold_pct=3.00)
    consensus_engine = ConsensusEngine()

    # Consensus is 4050.85; Multipli is delayed @ 4380.00
    observations = [
        OracleObservationData("chainlink", "Chainlink", 4050.20, 1000, 4, "ACTIVE", None, False, True),
        OracleObservationData("pyth", "Pyth", 4051.00, 1000, 2, "ACTIVE", 0.12, True, True),
        OracleObservationData("chronicle", "Chronicle", 4049.80, 1000, 9, "ACTIVE", None, False, True),
        OracleObservationData("redstone", "RedStone", 4052.10, 1000, 6, "ACTIVE", None, False, True),
        OracleObservationData("supra", "Supra", 4050.70, 1000, 5, "ACTIVE", None, False, True),
        OracleObservationData("api3", "API3", 4051.40, 1000, 8, "ACTIVE", None, False, True),
    ]
    consensus = consensus_engine.compute_consensus(observations)
    multipli = OracleObservationData("multipli", "Multipli", 4380.00, 1000, 1800, "DELAYED", None, False, True)

    decision = decision_engine.evaluate_decision(consensus, multipli)
    assert decision.state == "MULTIPLI_DEVIATION"
    assert decision.oracle_status == "EVIDENCE_OF_ABNORMAL_DEVIATION"
    assert decision.is_conservative_applied is True
    # min(4380, 4050.85) = 4050.85
    assert decision.final_price == round(consensus.consensus_price, 2)
    assert decision.effective_ltv == 0.50
    assert decision.protocol_state == "RESTRICTED"


def test_simulation_engine_scenarios():
    sim = SimulationEngine()

    # Scenario 1: Normal
    sim.reset("scen_normal")
    snap1 = sim.get_snapshot()
    assert snap1["scenario_id"] == "scen_normal"
    assert snap1["decision"]["state"] == "HEALTHY_CONSENSUS"
    assert snap1["decision"]["effective_ltv"] == 0.80

    # Scenario 2: Flash Crash
    sim.reset("scen_flash_crash")
    sim.step(1800.0)  # t=30m
    snap2 = sim.get_snapshot()
    assert snap2["decision"]["state"] == "MULTIPLI_DEVIATION"
    assert snap2["decision"]["effective_ltv"] == 0.50
    assert snap2["position"]["position_status"] in ("RESTRICTED", "OVER_LIMIT")

    # Scenario 3: Outlier
    sim.reset("scen_outlier")
    snap3 = sim.get_snapshot()
    assert snap3["consensus"]["has_strong_consensus"] is True
    assert snap3["decision"]["state"] in ("OUTLIER_DETECTED", "HEALTHY_CONSENSUS")
    assert snap3["decision"]["effective_ltv"] == 0.80

    # Scenario 4: Disagreement
    sim.reset("scen_disagreement")
    snap4 = sim.get_snapshot()
    assert snap4["decision"]["state"] in ("MARKET_CORROBORATED", "ORACLE_INSTABILITY", "NO_CONSENSUS")
    assert snap4["decision"]["protocol_state"] in ("RESTRICTED", "HALTED")
    assert snap4["position"]["position_status"] in ("RESTRICTED", "HALTED")

    # Scenario 5: Outage
    sim.reset("scen_outage")
    snap5 = sim.get_snapshot()
    assert snap5["consensus"]["cluster_size"] == 4
    assert snap5["decision"]["state"] == "HEALTHY_CONSENSUS"
