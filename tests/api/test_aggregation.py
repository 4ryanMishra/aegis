import pytest
from services.api.src.core.aggregator import P_DECAggregator
from services.api.src.models.schema import ValidatorObservation, DataStatus


def test_aggregation_quorum_not_met():
    aggregator = P_DECAggregator(min_quorum=3)
    obs = [
        ValidatorObservation(
            validator_id="val_1",
            strategy_id="strat_1",
            strategy_name="Strat 1",
            estimated_price=95.0,
            uncertainty_lower=93.0,
            uncertainty_upper=97.0,
            observed_at=1000,
            source_ids=["src_a"],
            method_version="0.1.0",
            status=DataStatus.SIMULATED
        )
    ]
    res = aggregator.aggregate(obs)
    assert res.quorum_met is False
    assert res.value is None


def test_aggregation_median_calculation():
    aggregator = P_DECAggregator(min_quorum=3, method="median")
    obs = [
        ValidatorObservation(
            validator_id=f"val_{i}",
            strategy_id="strat_1",
            strategy_name="Strat 1",
            estimated_price=p,
            uncertainty_lower=p - 1,
            uncertainty_upper=p + 1,
            observed_at=1000,
            source_ids=["src_a"],
            method_version="0.1.0",
            status=DataStatus.SIMULATED
        )
        for i, p in enumerate([92.0, 93.0, 94.0, 95.0])
    ]
    res = aggregator.aggregate(obs)
    assert res.quorum_met is True
    assert res.value == 93.5  # median of [92, 93, 94, 95] is 93.5
    assert res.validator_count == 4
    assert res.dispersion >= 0.0


def test_aggregation_with_price_estimators_and_diagnostic_lanes():
    """
    Test that P_DECAggregator separates price estimators (Lanes 1 & 2)
    from diagnostic lanes (Lanes 3, 4, 5).
    P_DEC should be calculated strictly from Lanes 1 & 2, while diagnostic
    lanes receive weight 0.0 but are preserved in lane_results.
    """
    from services.api.src.models.schema import ValidatorResult, MethodologyRole

    results = [
        # Lane 1: Kalman (Price Estimator)
        ValidatorResult(
            validator_id="val_kalman",
            methodology="KALMAN_1D",
            methodology_name="Recursive 1D Kalman",
            methodology_version="1.0.0",
            lane_id=1,
            operator_id="op_1",
            timestamp=1700001000,
            input_sources=["cex_feed"],
            input_values={"price": 100.0},
            role=MethodologyRole.PRICE_ESTIMATOR,
            is_price_estimator=True,
            estimated_price=100.2,
            uncertainty_lower=99.0,
            uncertainty_upper=101.4,
            decision="ACCEPTED",
            reason_code="INNOVATION_ACCEPTED_CONSISTENT",
            status=DataStatus.SIMULATED,
        ),
        # Lane 2: Huber (Price Estimator)
        ValidatorResult(
            validator_id="val_huber",
            methodology="HUBER_IRLS",
            methodology_name="Huber M-Estimation",
            methodology_version="1.0.0",
            lane_id=2,
            operator_id="op_2",
            timestamp=1700001000,
            input_sources=["multi_feed"],
            input_values={"prices": [100.0, 100.1, 99.9]},
            role=MethodologyRole.PRICE_ESTIMATOR,
            is_price_estimator=True,
            estimated_price=100.0,
            uncertainty_lower=99.2,
            uncertainty_upper=100.8,
            decision="ACCEPTED",
            reason_code="CONVERGED_ROBUST_LOCATION",
            status=DataStatus.SIMULATED,
        ),
        # Lane 3: JSD (Diagnostic Consensus Measure)
        ValidatorResult(
            validator_id="val_jsd",
            methodology="JSD",
            methodology_name="Pairwise Jensen-Shannon Divergence",
            methodology_version="1.0.0",
            lane_id=3,
            operator_id="op_3",
            timestamp=1700001000,
            input_sources=["distribution_feed"],
            input_values={"dists": 3},
            role=MethodologyRole.UNCERTAINTY_CONSENSUS_MEASURE,
            is_price_estimator=False,
            estimated_price=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            decision="INFORMATIONAL_CONSENSUS",
            reason_code="CONSISTENT_UNCERTAINTY_REGIME",
            diagnostic_evidence={"informational_disagreement": 0.05},
            status=DataStatus.SIMULATED,
        ),
        # Lane 4: OU (RWA Diagnostic Check)
        ValidatorResult(
            validator_id="val_ou",
            methodology="OU_RESIDUAL",
            methodology_name="Ornstein-Uhlenbeck RWA Residual Analysis",
            methodology_version="1.0.0",
            lane_id=4,
            operator_id="op_4",
            timestamp=1700001000,
            input_sources=["rwa_nav_anchor"],
            input_values={"spot": 100.0, "anchor": 100.0},
            role=MethodologyRole.RWA_STRUCTURAL_CHECK,
            is_price_estimator=False,
            estimated_price=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            decision="DIFFUSION_CONSISTENT",
            reason_code="RESIDUAL_WITHIN_BOUNDS",
            diagnostic_evidence={"jump_candidate": False, "standardized_residual": 0.2},
            status=DataStatus.SIMULATED,
        ),
        # Lane 5: Page CUSUM (Sequential Drift Detector)
        ValidatorResult(
            validator_id="val_cusum",
            methodology="CUSUM",
            methodology_name="Page CUSUM Sequential Drift Detection",
            methodology_version="1.0.0",
            lane_id=5,
            operator_id="op_5",
            timestamp=1700001000,
            input_sources=["tick_stream"],
            input_values={"sample_count": 20},
            role=MethodologyRole.SEQUENTIAL_DRIFT_DETECTOR,
            is_price_estimator=False,
            estimated_price=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            decision="BASELINE_STATIONARY",
            reason_code="NO_DRIFT_DETECTED",
            diagnostic_evidence={"trip_state": "NORMAL", "s_plus": 0.1, "s_minus": 0.05},
            status=DataStatus.SIMULATED,
        ),
    ]

    aggregator = P_DECAggregator(min_quorum=3)
    res = aggregator.aggregate(results)

    assert res.quorum_met is True
    assert res.validator_count == 5
    assert res.eligible_count == 2
    assert res.rejected_count == 0

    # Price estimate must be around 100.1 (blend of 100.2 and 100.0)
    assert res.value is not None
    assert 99.9 <= res.value <= 100.3

    # Diagnostic lanes have assigned_weight == 0.0 and is_eligible == False
    lane_map = {l["lane_id"]: l for l in res.lane_results}
    assert lane_map[1]["is_price_estimator"] is True
    assert lane_map[1]["assigned_weight"] > 0.0
    assert lane_map[2]["is_price_estimator"] is True
    assert lane_map[2]["assigned_weight"] > 0.0

    assert lane_map[3]["is_price_estimator"] is False
    assert lane_map[3]["assigned_weight"] == 0.0
    assert lane_map[3]["estimated_price"] is None

    assert lane_map[4]["is_price_estimator"] is False
    assert lane_map[4]["assigned_weight"] == 0.0
    assert lane_map[4]["estimated_price"] is None

    assert lane_map[5]["is_price_estimator"] is False
    assert lane_map[5]["assigned_weight"] == 0.0
    assert lane_map[5]["estimated_price"] is None


def test_aggregation_flash_spike_kalman_gated_huber_selected():
    """
    During a flash spike, Lane 1 (Kalman) rejects the outlier via innovation gating (INNOVATION_GATED).
    Lane 2 (Huber) robustly downweights the outlier and provides the clean uncontaminated location (~100.0).
    P_DECAggregator must isolate the gated Kalman estimator to rejected_price_estimators,
    and use Huber's uncontaminated estimate alone to determine P_DEC.
    """
    from services.api.src.models.schema import ValidatorResult, MethodologyRole

    results = [
        # Lane 1: Kalman gates the innovation
        ValidatorResult(
            validator_id="val_kalman",
            methodology="KALMAN_1D",
            methodology_name="Recursive 1D Kalman",
            methodology_version="1.0.0",
            lane_id=1,
            operator_id="op_1",
            timestamp=1700001000,
            input_sources=["cex_feed"],
            input_values={"price": 115.0},
            role=MethodologyRole.PRICE_ESTIMATOR,
            is_price_estimator=True,
            estimated_price=100.0,  # Prior held state
            uncertainty_lower=98.5,
            uncertainty_upper=101.5,
            decision="INNOVATION_GATED",
            reason_code="STATISTICAL_ANOMALY_GATED",
            status=DataStatus.SIMULATED,
        ),
        # Lane 2: Huber uncontaminated location
        ValidatorResult(
            validator_id="val_huber",
            methodology="HUBER_IRLS",
            methodology_name="Huber M-Estimation",
            methodology_version="1.0.0",
            lane_id=2,
            operator_id="op_2",
            timestamp=1700001000,
            input_sources=["multi_feed"],
            input_values={"prices": [100.0, 100.1, 99.9, 115.0]},
            role=MethodologyRole.PRICE_ESTIMATOR,
            is_price_estimator=True,
            estimated_price=100.05,
            uncertainty_lower=99.2,
            uncertainty_upper=100.9,
            decision="ACCEPTED",
            reason_code="CONVERGED_ROBUST_LOCATION",
            diagnostic_evidence={"outlier_count": 1},
            status=DataStatus.SIMULATED,
        ),
        # Lane 3: JSD
        ValidatorResult(
            validator_id="val_jsd",
            methodology="JSD",
            methodology_name="Pairwise Jensen-Shannon Divergence",
            methodology_version="1.0.0",
            lane_id=3,
            operator_id="op_3",
            timestamp=1700001000,
            input_sources=["feed"],
            input_values={},
            role=MethodologyRole.UNCERTAINTY_CONSENSUS_MEASURE,
            is_price_estimator=False,
            estimated_price=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            decision="INFORMATIONAL_CONSENSUS",
            reason_code="CONSISTENT",
            status=DataStatus.SIMULATED,
        ),
    ]

    aggregator = P_DECAggregator(min_quorum=3)
    res = aggregator.aggregate(results)

    assert res.quorum_met is True
    assert res.validator_count == 3
    assert res.eligible_count == 1  # Only Huber is eligible
    assert res.rejected_count == 1  # Kalman was innovation-gated

    # P_DEC value must strictly equal Huber's uncontaminated price
    assert res.value == 100.05


def test_evidence_engine_consumes_diagnostic_evidence():
    """
    Verify that EvidenceEngine correctly ingests non-price diagnostic evidence
    (CUSUM trip, JSD divergence, OU structural residual alert) without type errors.
    """
    from services.api.src.core.evidence_engine import EvidenceEngine
    from services.api.src.models.schema import (
        OSMFeed,
        DECAggregate,
        MarketObservation,
        ValidatorResult,
        MethodologyRole,
    )

    osm_feed = OSMFeed(value=100.0, timestamp=1700000000, asset="ETH/USD", source="maker_osm")
    p_dec = DECAggregate(value=100.0, quorum_met=True, dispersion=0.01, validator_count=5)
    market_feed = MarketObservation(value=100.0, timestamp=1700003600, source="clob_midpoint")

    validators = [
        ValidatorResult(
            validator_id="val_cusum",
            methodology="CUSUM",
            methodology_name="Page CUSUM",
            methodology_version="1.0.0",
            lane_id=5,
            operator_id="op_5",
            timestamp=1700001000,
            input_sources=["ticks"],
            input_values={},
            role=MethodologyRole.SEQUENTIAL_DRIFT_DETECTOR,
            is_price_estimator=False,
            estimated_price=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            decision="SEQUENTIAL_DRIFT_DETECTED",
            reason_code="CUSUM_ACCUMULATOR_TRIPPED",
            diagnostic_evidence={"trip_state": "TRIP", "direction": "POSITIVE_DRIFT"},
            status=DataStatus.SIMULATED,
        ),
        ValidatorResult(
            validator_id="val_ou",
            methodology="OU_RESIDUAL",
            methodology_name="OU Residual",
            methodology_version="1.0.0",
            lane_id=4,
            operator_id="op_4",
            timestamp=1700001000,
            input_sources=["nav"],
            input_values={},
            role=MethodologyRole.RWA_STRUCTURAL_CHECK,
            is_price_estimator=False,
            estimated_price=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            decision="DIFFUSION_MODEL_INCONSISTENCY",
            reason_code="STRUCTURAL_RESIDUAL_ALERT",
            diagnostic_evidence={"jump_candidate": True, "standardized_residual": 4.2},
            status=DataStatus.SIMULATED,
        ),
    ]

    engine = EvidenceEngine()
    record = engine.evaluate(osm_feed, p_dec, market_feed, validators)

    assert "CUSUM_SEQUENTIAL_DRIFT_TRIPPED" in record.reason_codes
    assert "OU_STRUCTURAL_RESIDUAL_ALERT" in record.reason_codes
    assert record.cusum_state == "TRIP"
    assert record.ou_structural_state == "JUMP_CANDIDATE"

