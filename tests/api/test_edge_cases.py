import pytest
from services.api.src.core.aggregator import P_DECAggregator
from services.api.src.core.evidence_engine import EvidenceEngine
from services.api.src.core.decision_engine import DecisionEngine
from services.api.src.models.schema import (
    OSMFeed,
    DECAggregate,
    MarketObservation,
    ValidatorObservation,
    EvidenceRecord,
    OracleStatus,
    DecisionPolicy,
    DataStatus,
)


def test_edge_case_zero_near_zero_denominators():
    """Verify division safety when market or DEC value is near zero."""
    engine = EvidenceEngine()
    osm = OSMFeed(value=10.0, timestamp=1000)
    dec = DECAggregate(value=0.0001, aggregation="median", validator_count=4, dispersion=0.0, quorum_met=True)
    mkt = MarketObservation(value=0.0001, timestamp=4600, source="mkt", status=DataStatus.SIMULATED)
    vals = [
        ValidatorObservation(
            validator_id=f"val_{i}",
            strategy_id="strat_1",
            strategy_name="Strat 1",
            estimated_price=0.0001,
            uncertainty_lower=0.0,
            uncertainty_upper=0.0002,
            observed_at=1000,
            source_ids=["src_a"],
            method_version="0.1.0"
        )
        for i in range(4)
    ]

    # Should compute without ZeroDivisionError
    ev = engine.evaluate(osm, dec, mkt, vals)
    assert ev.d_osm_market is not None
    assert ev.d_osm_dec is not None


def test_edge_case_identical_validator_estimates():
    """When all validators submit the exact same price, dispersion must be 0.0 without errors."""
    aggregator = P_DECAggregator(min_quorum=3)
    obs = [
        ValidatorObservation(
            validator_id=f"val_{i}",
            strategy_id="strat_1",
            strategy_name="Strat 1",
            estimated_price=100.0,
            uncertainty_lower=98.0,
            uncertainty_upper=102.0,
            observed_at=1000,
            source_ids=["src_a"],
            method_version="0.1.0",
            status=DataStatus.SIMULATED
        )
        for i in range(4)
    ]
    res = aggregator.aggregate(obs)
    assert res.quorum_met is True
    assert res.value == 100.0
    assert res.dispersion == 0.0


def test_edge_case_negative_difference_collateral():
    """When baseline OSM is lower than market (understated), risk overstatement prevented should be 0.0%."""
    decision_engine = DecisionEngine(policy=DecisionPolicy.NEAREST_TO_MARKET)
    osm = OSMFeed(value=80.0, timestamp=1000)
    dec = DECAggregate(value=95.0, aggregation="median", validator_count=4, dispersion=0.01, quorum_met=True)
    mkt = MarketObservation(value=95.0, timestamp=4600, source="mkt", status=DataStatus.SIMULATED)
    ev = EvidenceRecord(
        d_osm_market=0.1579,
        d_dec_market=0.0,
        d_osm_dec=0.1579,
        validator_dispersion=0.01,
        agreement_ratio=1.0,
        oracle_status=OracleStatus.SUSPECTED_INCONSISTENCY,
        anomaly_score=0.85,
        reason_codes=["OSM_DEVIATION"]
    )

    decision, collateral = decision_engine.decide(osm, dec, mkt, ev, ltv=0.60)
    assert collateral.baseline_value == 48.0  # 80 * 0.60
    assert collateral.aegis_value == 57.0     # 95 * 0.60
    assert collateral.difference == -9.0      # 48 - 57
    assert collateral.risk_exposure_pct == 0.0
