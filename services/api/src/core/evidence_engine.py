"""
Evidence & Anomaly Engine (Phase 4A Task 10).
Consumes P_OSM, P_DEC, P_MARKET, and rich ValidatorResult evidence from five methodology lanes.

Computes:
- Triangular deviations: d(OSM, MARKET), d(DEC, MARKET), d(OSM, DEC)
- Validator agreement ratio & dispersion
- Methodology-specific anomaly states (Kalman gating, Huber outliers, JSD disagreement, OU residual, CUSUM drift)
- Conflict indicators & disciplined machine-readable reason codes
- Transparent anomaly score
"""

from typing import List, Optional, Dict, Any
from ..models.schema import (
    OSMFeed,
    DECAggregate,
    MarketObservation,
    ValidatorResult,
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
        validators: List[ValidatorResult],
    ) -> EvidenceRecord:
        reason_codes: List[str] = []
        methodology_statuses: Dict[str, str] = {}

        # 1. Check window progression
        if p_market.value is None or p_dec.value is None:
            return EvidenceRecord(
                d_osm_market=None,
                d_dec_market=None,
                d_osm_dec=None,
                validator_dispersion=p_dec.dispersion,
                agreement_ratio=1.0,
                oracle_status=OracleStatus.PENDING_FINALIZATION,
                anomaly_score=0.0,
                reason_codes=["WINDOW_IN_PROGRESS"],
                methodology_statuses={},
                cusum_state=None,
                ou_structural_state=None,
                kalman_gated=False,
                conflict_detected=False,
            )

        osm_val = float(p_osm.value)
        dec_val = float(p_dec.value)
        mkt_val = float(p_market.value)

        # 2. Triangular relative deviations
        d_osm_market = abs(osm_val - mkt_val) / max(abs(mkt_val), 1e-6)
        d_dec_market = abs(dec_val - mkt_val) / max(abs(mkt_val), 1e-6)
        d_osm_dec = abs(osm_val - dec_val) / max(abs(dec_val), 1e-6)

        # 3. Extract methodology-specific anomaly signals
        kalman_gated = False
        cusum_state: Optional[str] = None
        ou_structural_state: Optional[str] = None

        for v in validators:
            meth_key = v.methodology or getattr(v, "strategy_id", None) or getattr(v, "validator_id", None) or "unknown"
            methodology_statuses[meth_key] = v.decision

            diag = getattr(v, "diagnostic_evidence", {}) or v.intermediate_metrics

            if v.methodology == "KALMAN_1D" and v.decision == "INNOVATION_GATED":
                kalman_gated = True
                reason_codes.append("KALMAN_MAHALANOBIS_GATED_INNOVATION")

            elif v.methodology == "HUBER_IRLS" and diag.get("outlier_count", 0) > 0:
                reason_codes.append(f"HUBER_DOWNWEIGHTED_{diag['outlier_count']}_OUTLIERS")

            elif v.methodology == "JSD" and v.decision == "INFORMATIONAL_DIVERGENCE_DETECTED":
                reason_codes.append("JSD_INFORMATIONAL_DISAGREEMENT_HIGH")

            elif v.methodology == "OU_RESIDUAL":
                if diag.get("jump_candidate", False):
                    ou_structural_state = "JUMP_CANDIDATE"
                    reason_codes.append("OU_STRUCTURAL_RESIDUAL_ALERT")
                elif v.decision == "NOT_APPLICABLE":
                    ou_structural_state = "NOT_APPLICABLE"

            elif v.methodology == "CUSUM":
                cusum_state = diag.get("trip_state", "NORMAL")
                if cusum_state == "TRIP":
                    reason_codes.append("CUSUM_SEQUENTIAL_DRIFT_TRIPPED")
                elif cusum_state == "DRIFT":
                    reason_codes.append("CUSUM_PERSISTENT_DRIFT_ACCUMULATING")

        # 4. Validator Agreement Ratio (calculated on price estimators only)
        price_validators = [
            v for v in validators
            if getattr(v, "is_price_estimator", True) and v.estimated_price is not None
        ]
        tolerance = 0.025
        if price_validators:
            agreeing = sum(
                1 for v in price_validators
                if abs(v.estimated_price - dec_val) / max(abs(dec_val), 1e-6) <= tolerance
            )
            agreement_ratio = agreeing / len(price_validators)
        else:
            agreement_ratio = 1.0

        # 5. Triangular conflict and anomaly classification
        conflict_detected = False

        if osm_val <= 0.0:
            # Upstream OSM failed / reverted
            oracle_status = OracleStatus.SUSPECTED_INCONSISTENCY
            reason_codes.append("OSM_READ_FAILURE_DECENTRALIZED_FALLBACK")
            conflict_detected = True

        elif d_dec_market > 0.20 or (d_osm_dec > 0.20 and d_osm_market > 0.20 and d_dec_market > 0.15):
            # Extreme off-chain market dislocation (>20%)
            oracle_status = OracleStatus.HALTED_CIRCUIT_BREAKER
            reason_codes.append("EXTREME_TRIANGULAR_DIVERGENCE_CIRCUIT_BREAKER")
            conflict_detected = True

        elif d_osm_market > self.config.high_deviation_threshold and d_dec_market < d_osm_market:
            # Clear OSM spike or lag; validator reference confirms market
            oracle_status = OracleStatus.SUSPECTED_INCONSISTENCY
            reason_codes.append("OSM_DEVIATION_EXCEEDS_HIGH_THRESHOLD")
            reason_codes.append("VALIDATOR_REFERENCE_ALIGNED_WITH_MARKET")
            conflict_detected = True

        elif d_osm_dec > self.config.abnormal_deviation_threshold and d_dec_market > self.config.abnormal_deviation_threshold:
            # Triangular divergence: all three sources disagree
            oracle_status = OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION
            reason_codes.append("TRIANGULAR_DIVERGENCE_ACROSS_SOURCES")
            conflict_detected = True

        elif d_osm_dec > self.config.abnormal_deviation_threshold or d_osm_market > self.config.abnormal_deviation_threshold:
            oracle_status = OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION
            reason_codes.append("EVIDENCE_OF_ABNORMAL_OSM_DEVIATION")
            conflict_detected = True

        elif p_dec.dispersion > self.config.max_acceptable_dispersion:
            oracle_status = OracleStatus.DISPERSED_UNCERTAINTY
            reason_codes.append("HIGH_VALIDATOR_DISPERSION")

        else:
            oracle_status = OracleStatus.HEALTHY_CONSENSUS
            reason_codes.append("CONSISTENT_ORACLE_ALIGNMENT")

        if agreement_ratio >= 0.75:
            reason_codes.append("STRONG_VALIDATOR_QUORUM_AGREEMENT")

        # 6. Heuristic Anomaly Score [0.0 - 1.0]
        osm_factor = min(1.0, d_osm_dec / (self.config.high_deviation_threshold * 2))
        alignment_bonus = 0.25 if (d_dec_market < d_osm_market and d_osm_market > self.config.abnormal_deviation_threshold) else 0.0
        dispersion_penalty = min(0.2, p_dec.dispersion * 2)
        methodology_penalty = 0.15 if (kalman_gated or cusum_state == "TRIP" or ou_structural_state == "JUMP_CANDIDATE") else 0.0

        anomaly_score = min(1.0, max(0.0, (osm_factor * 0.6) + alignment_bonus + methodology_penalty - dispersion_penalty))

        return EvidenceRecord(
            d_osm_market=round(d_osm_market, 4),
            d_dec_market=round(d_dec_market, 4),
            d_osm_dec=round(d_osm_dec, 4),
            validator_dispersion=round(p_dec.dispersion, 4),
            agreement_ratio=round(agreement_ratio, 2),
            oracle_status=oracle_status,
            anomaly_score=round(anomaly_score, 2),
            reason_codes=reason_codes,
            methodology_statuses=methodology_statuses,
            cusum_state=cusum_state,
            ou_structural_state=ou_structural_state,
            kalman_gated=kalman_gated,
            conflict_detected=conflict_detected,
        )
