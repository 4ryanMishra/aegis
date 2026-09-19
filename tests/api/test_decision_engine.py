import pytest
from services.api.src.core.decision_engine import DecisionEngine
from services.api.src.models.schema import (
    OSMFeed,
    DECAggregate,
    MarketObservation,
    EvidenceRecord,
    OracleStatus,
    DecisionPolicy,
    DataStatus,
)


def test_decision_engine_collateral_delta():
    engine = DecisionEngine(policy=DecisionPolicy.NEAREST_TO_MARKET)
    osm = OSMFeed(value=100.0, timestamp=1000)
    dec = DECAggregate(value=93.0, aggregation="median", validator_count=4, dispersion=0.01, quorum_met=True)
    mkt = MarketObservation(value=95.0, timestamp=4600, source="mkt", status=DataStatus.SIMULATED)
    ev = EvidenceRecord(
        d_osm_market=0.0526,
        d_dec_market=0.0211,
        d_osm_dec=0.0753,
        validator_dispersion=0.01,
        agreement_ratio=1.0,
        oracle_status=OracleStatus.SUSPECTED_INCONSISTENCY,
        anomaly_score=0.75,
        reason_codes=["OSM_DEVIATION"]
    )

    decision, collateral = engine.decide(osm, dec, mkt, ev, ltv=0.60)
    assert decision.final_price == 93.0
    assert decision.selected_source == "P_DEC"
    assert collateral.baseline_value == 60.0  # 100 * 0.60
    assert collateral.aegis_value == 55.8     # 93 * 0.60
    assert collateral.difference == 4.2       # 60.0 - 55.8
    assert collateral.risk_exposure_pct == pytest.approx(7.0, abs=1e-2)
