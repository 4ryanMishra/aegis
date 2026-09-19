"""
Evidence & Anomaly Engine.
Computes relative deviation metrics, validator dispersion, transparent anomaly scores, and reason codes.
Rule #4: Never claim an anomaly score proves manipulation; use terms like 'suspected manipulation',
'oracle inconsistency', or 'evidence of abnormal deviation'.
"""

from typing import List, Optional
from ..models.schema import (
    OSMFeed,
    DECAggregate,
    MarketObservation,
    ValidatorObservation,
    EvidenceRecord,
    OracleStatus,
)
from ..config import AegisConfig, default_config


class EvidenceEngine:
    def __init__(self, config: AegisConfig = default_config):
        self.config = config

    def evaluate(
        self,
        p_osm: OSMFeed,
        p_dec: DECAggregate,
        p_market: MarketObservation,
        validators: List[ValidatorObservation]
    ) -> EvidenceRecord:
        reason_codes: List[str] = []

        if p_market.value is None or p_dec.value is None:
            return EvidenceRecord(
                d_osm_market=None,
                d_dec_market=None,
                d_osm_dec=None,
                validator_dispersion=p_dec.dispersion,
                agreement_ratio=1.0,
                oracle_status=OracleStatus.PENDING_FINALIZATION,
                anomaly_score=0.0,
                reason_codes=["WINDOW_IN_PROGRESS"]
            )

        osm_val = p_osm.value
        dec_val = p_dec.value
        mkt_val = p_market.value

        # Relative deviations
        d_osm_market = abs(osm_val - mkt_val) / max(mkt_val, 1e-6)
        d_dec_market = abs(dec_val - mkt_val) / max(mkt_val, 1e-6)
        d_osm_dec = abs(osm_val - dec_val) / max(dec_val, 1e-6)

        # Validator agreement ratio (fraction within 2.5% of P_DEC)
        tolerance = 0.025
        agreeing = sum(
            1 for v in validators
            if abs(v.estimated_price - dec_val) / max(dec_val, 1e-6) <= tolerance
        )
        agreement_ratio = agreeing / max(len(validators), 1)

        # Transparent heuristic anomaly score [0.0 - 1.0]
        # Weighted by OSM-DEC divergence and alignment between DEC and Market
        osm_factor = min(1.0, d_osm_dec / (self.config.high_deviation_threshold * 2))
        alignment_bonus = 0.3 if (d_dec_market < d_osm_market and d_osm_market > self.config.abnormal_deviation_threshold) else 0.0
        dispersion_penalty = min(0.2, p_dec.dispersion * 2)

        anomaly_score = min(1.0, max(0.0, (osm_factor * 0.7) + alignment_bonus - dispersion_penalty))

        # Classify status using disciplined terminology
        if d_osm_market > self.config.high_deviation_threshold and d_dec_market < d_osm_market:
            oracle_status = OracleStatus.SUSPECTED_INCONSISTENCY
            reason_codes.append("OSM_DEVIATION_EXCEEDS_HIGH_THRESHOLD")
            reason_codes.append("VALIDATOR_REFERENCE_ALIGNED_WITH_MARKET")
        elif d_osm_dec > self.config.abnormal_deviation_threshold:
            oracle_status = OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION
            reason_codes.append("EVIDENCE_OF_ABNORMAL_OSM_DEVIATION")
        elif p_dec.dispersion > self.config.max_acceptable_dispersion:
            oracle_status = OracleStatus.DISPERSED_UNCERTAINTY
            reason_codes.append("HIGH_VALIDATOR_DISPERSION")
        else:
            oracle_status = OracleStatus.HEALTHY_CONSENSUS
            reason_codes.append("CONSISTENT_ORACLE_ALIGNMENT")

        if agreement_ratio >= 0.75:
            reason_codes.append("STRONG_VALIDATOR_QUORUM_AGREEMENT")

        return EvidenceRecord(
            d_osm_market=round(d_osm_market, 4),
            d_dec_market=round(d_dec_market, 4),
            d_osm_dec=round(d_osm_dec, 4),
            validator_dispersion=round(p_dec.dispersion, 4),
            agreement_ratio=round(agreement_ratio, 2),
            oracle_status=oracle_status,
            anomaly_score=round(anomaly_score, 2),
            reason_codes=reason_codes
        )
