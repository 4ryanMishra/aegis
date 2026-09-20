"""
Decision & Collateral Risk Engine (Phase 4A Task 11).
Evaluates safety policy across P_OSM, P_DEC, P_MARKET, and EvidenceRecord.

Supported States:
- VERIFIED: Consistent multi-source alignment; protocol operates at standard parameters.
- WARNING: Suspected OSM inconsistency; substituted with robust decentralized reference.
- DISPUTED: Material triangular conflict or high validator dispersion; conservative fallback.
- RESTRICTED: Quorum failure or severe divergence; haircuts applied, new debt restricted.
- HALTED: Emergency circuit breaker; trading/minting halted to protect solvency.

Policy Principles:
Does NOT blindly select the nearest-to-market price.
Enforces deterministic fail-safe hierarchy.
"""

from typing import Tuple, Optional
from ..models.schema import (
    OSMFeed,
    DECAggregate,
    MarketObservation,
    EvidenceRecord,
    DecisionResult,
    CollateralImpact,
    DecisionPolicy,
    OracleStatus,
)


class DecisionEngine:
    def __init__(self, policy: DecisionPolicy = DecisionPolicy.NEAREST_TO_MARKET):
        self.policy = policy

    def decide(
        self,
        p_osm: OSMFeed,
        p_dec: DECAggregate,
        p_market: MarketObservation,
        evidence: EvidenceRecord,
        ltv: float = 0.60,
    ) -> Tuple[DecisionResult, CollateralImpact]:
        # 1. Window in progress
        if p_market.value is None or p_dec.value is None:
            decision = DecisionResult(
                policy=self.policy,
                final_price=None,
                selected_source="PENDING",
                confidence=None,
                reason_codes=["AWAITING_WINDOW_FINALIZATION"],
                policy_version="1.0.0-phase4a",
                action="PENDING",
                dispute_status="PENDING",
            )
            collateral = CollateralImpact(
                ltv=ltv,
                baseline_value=round(p_osm.value * ltv, 2),
                aegis_value=None,
                difference=None,
                risk_exposure_pct=None,
            )
            return decision, collateral

        osm_val = float(p_osm.value)
        dec_val = float(p_dec.value)
        mkt_val = float(p_market.value)

        reason_codes = list(evidence.reason_codes)

        # 2. Check Quorum & Integrity Preconditions
        if not p_dec.quorum_met:
            selected_price = min(osm_val, dec_val)
            action = "RESTRICT"
            dispute_status = "RESTRICTED"
            confidence = 0.40
            selected_source = "RESTRICT_FAILSAFE"
            reason_codes.append("INSUFFICIENT_VALIDATOR_QUORUM_FALLBACK")

        # 3. Severe Triangular Divergence Check (> 15% across all feeds)
        elif (
            evidence.d_osm_market is not None
            and evidence.d_dec_market is not None
            and evidence.d_osm_market > 0.15
            and evidence.d_dec_market > 0.15
        ):
            selected_price = min(osm_val, dec_val, mkt_val)
            action = "HALT"
            dispute_status = "HALTED"
            confidence = 0.99
            selected_source = "CIRCUIT_BREAKER_HALT"
            reason_codes.append("EXTREME_TRIANGULAR_DIVERGENCE_EMERGENCY_HALT")

        # 4. Standard Policy Evaluation
        elif self.policy == DecisionPolicy.NEAREST_TO_MARKET:
            d_osm = abs(osm_val - mkt_val)
            d_dec = abs(dec_val - mkt_val)

            if evidence.oracle_status == OracleStatus.HEALTHY_CONSENSUS:
                selected_price = osm_val
                selected_source = "P_OSM"
                confidence = 0.95
                action = "ALLOW"
                dispute_status = "VERIFIED"
                reason_codes.append("OSM_CONSISTENCY_CONFIRMED")

            elif evidence.oracle_status == OracleStatus.SUSPECTED_INCONSISTENCY:
                # OSM deviated, but validator reference aligns with market observation
                selected_price = dec_val
                selected_source = "P_DEC"
                confidence = 0.88
                action = "ALLOW"
                dispute_status = "WARNING"
                reason_codes.append("SUBSTITUTED_INCONSISTENT_OSM_WITH_DEC_REFERENCE")

            elif evidence.oracle_status == OracleStatus.DISPERSED_UNCERTAINTY:
                # High validator disagreement
                selected_price = min(osm_val, dec_val)
                selected_source = "P_DEC"
                confidence = 0.65
                action = "HAIRCUT"
                dispute_status = "DISPUTED"
                reason_codes.append("APPLIED_HAIRCUT_DUE_TO_HIGH_VALIDATOR_DISPERSION")

            elif d_dec <= d_osm:
                selected_price = dec_val
                selected_source = "P_DEC"
                confidence = 0.85
                action = "ALLOW"
                dispute_status = "WARNING"
                reason_codes.append("SELECTED_VALIDATOR_REFERENCE_CLOSER_TO_MARKET")

            else:
                selected_price = osm_val
                selected_source = "P_OSM"
                confidence = 0.70
                action = "ALLOW"
                dispute_status = "WARNING"
                reason_codes.append("RETAINED_BASELINE_OSM")

        elif self.policy == DecisionPolicy.ROBUST_MEDIAN:
            selected_price = dec_val
            selected_source = "P_DEC"
            confidence = 0.90
            action = "ALLOW"
            dispute_status = "VERIFIED" if evidence.oracle_status == OracleStatus.HEALTHY_CONSENSUS else "WARNING"
            reason_codes.append("POLICY_ENFORCED_DECENTRALIZED_REFERENCE")

        elif self.policy == DecisionPolicy.USE_OSM:
            selected_price = osm_val
            selected_source = "P_OSM"
            confidence = 0.60
            action = "ALLOW"
            dispute_status = "WARNING"
            reason_codes.append("POLICY_DEFAULT_PASSIVE_OSM")

        else:  # RESTRICT
            selected_price = min(osm_val, dec_val)
            selected_source = "RESTRICT"
            confidence = 0.99
            action = "RESTRICT"
            dispute_status = "RESTRICTED"
            reason_codes.append("CONSERVATIVE_COLLATERAL_HAIRCUT_APPLIED")

        # 5. Collateral Financial Consequence Calculation
        baseline_borrow_capacity = round(osm_val * ltv, 2)
        aegis_borrow_capacity = round(selected_price * ltv, 2)
        diff = round(baseline_borrow_capacity - aegis_borrow_capacity, 2)
        
        # Overstatement percentage prevented relative to baseline
        if osm_val > selected_price:
            exposure_pct = round(((osm_val - selected_price) / osm_val) * 100.0, 2)
        else:
            exposure_pct = 0.0

        decision = DecisionResult(
            policy=self.policy,
            final_price=round(selected_price, 2),
            selected_source=selected_source,
            confidence=round(confidence, 2),
            reason_codes=reason_codes,
            policy_version="1.0.0-phase4a",
            action=action,
            dispute_status=dispute_status,
        )

        collateral = CollateralImpact(
            ltv=ltv,
            baseline_value=baseline_borrow_capacity,
            aegis_value=aegis_borrow_capacity,
            difference=diff,
            risk_exposure_pct=exposure_pct,
        )

        return decision, collateral
