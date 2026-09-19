import pytest
from services.api.src.core.evidence_engine import EvidenceEngine
from services.api.src.models.schema import (
    OSMFeed,
    DECAggregate,
    MarketObservation,
    ValidatorObservation,
    OracleStatus,
    DataStatus,
)


def test_evidence_engine_healthy_consensus():
    engine = EvidenceEngine()
    osm = OSMFeed(value=95.0, timestamp=1000)
    dec = DECAggregate(value=95.1, aggregation="median", validator_count=4, dispersion=0.01, quorum_met=True)
    mkt = MarketObservation(value=95.05, timestamp=4600, source="mkt", status=DataStatus.SIMULATED)
    vals = [
        ValidatorObservation(
            validator_id=f"val_{i}",
            strategy_id="strat_1",
            strategy_name="Strat 1",
            estimated_price=p,
            uncertainty_lower=p - 1,
            uncertainty_upper=p + 1,
            observed_at=1000,
            source_ids=["src_a"],
            method_version="0.1.0"
        )
        for i, p in enumerate([94.9, 95.0, 95.1, 95.2])
    ]

    ev = engine.evaluate(osm, dec, mkt, vals)
    assert ev.oracle_status == OracleStatus.HEALTHY_CONSENSUS
    assert ev.d_osm_market is not None
    assert ev.d_osm_market < 0.01
    assert ev.anomaly_score < 0.3


def test_evidence_engine_osm_spike_detection():
    engine = EvidenceEngine()
    osm = OSMFeed(value=100.0, timestamp=1000)
    dec = DECAggregate(value=93.0, aggregation="median", validator_count=4, dispersion=0.01, quorum_met=True)
    mkt = MarketObservation(value=95.0, timestamp=4600, source="mkt", status=DataStatus.SIMULATED)
    vals = [
        ValidatorObservation(
            validator_id=f"val_{i}",
            strategy_id="strat_1",
            strategy_name="Strat 1",
            estimated_price=p,
            uncertainty_lower=p - 1,
            uncertainty_upper=p + 1,
            observed_at=1000,
            source_ids=["src_a"],
            method_version="0.1.0"
        )
        for i, p in enumerate([92.8, 93.0, 93.2, 93.1])
    ]

    ev = engine.evaluate(osm, dec, mkt, vals)
    assert ev.oracle_status == OracleStatus.SUSPECTED_INCONSISTENCY
    assert ev.d_osm_market == pytest.approx(0.0526, abs=1e-3)
    assert ev.d_dec_market == pytest.approx(0.0211, abs=1e-3)
    assert ev.d_osm_dec == pytest.approx(0.0753, abs=1e-3)
    assert "OSM_DEVIATION_EXCEEDS_HIGH_THRESHOLD" in ev.reason_codes
