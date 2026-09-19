"""
Decision & Collateral Risk Engine.
Calculates final protocol valuation action and collateral delta based on configurable LTV.
"""

from typing import Optional
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
        ltv: float = 0.60
    ) -> tuple[DecisionResult, CollateralImpact]:
        if p_market.value is None or p_dec.value is None:
            decision = DecisionResult(
                policy=self.policy,
                final_price=None,
                selected_source="PENDING",
                confidence=None,
                reason_codes=["AWAITING_WINDOW_FINALIZATION"],
                policy_version="0.1.0-mvp"
            )
            collateral = CollateralImpact(
                ltv=ltv,
                baseline_value=round(p_osm.value * ltv, 2),
                aegis_value=None,
                difference=None,
                risk_exposure_pct=None
            )
            return decision, collateral

        osm_val = p_osm.value
        dec_val = p_dec.value
        mkt_val = p_market.value

        selected_price: float
        selected_source: str
        confidence: float
        reason_codes = list(evidence.reason_codes)

        if self.policy == DecisionPolicy.NEAREST_TO_MARKET:
            # MVP baseline evaluation policy
            d_osm = abs(osm_val - mkt_val)
            d_dec = abs(dec_val - mkt_val)

            if evidence.oracle_status == OracleStatus.HEALTHY_CONSENSUS:
                selected_price = osm_val
                selected_source = "P_OSM"
                confidence = 0.95
                reason_codes.append("OSM_CONSISTENCY_CONFIRMED")
            elif d_dec <= d_osm:
                selected_price = dec_val
                selected_source = "P_DEC"
                confidence = 0.88
                reason_codes.append("SUBSTITUTED_INCONSISTENT_OSM_WITH_DEC_REFERENCE")
            else:
                selected_price = osm_val
                selected_source = "P_OSM"
                confidence = 0.70
                reason_codes.append("RETAINED_BASELINE_OSM")

        elif self.policy == DecisionPolicy.ROBUST_MEDIAN:
            selected_price = dec_val
            selected_source = "P_DEC"
            confidence = 0.90
            reason_codes.append("POLICY_ENFORCED_DECENTRALIZED_MEDIAN")

        elif self.policy == DecisionPolicy.USE_OSM:
            selected_price = osm_val
            selected_source = "P_OSM"
            confidence = 0.60
            reason_codes.append("POLICY_DEFAULT_PASSIVE_OSM")

        else:  # RESTRICT
            selected_price = min(osm_val, dec_val)
            selected_source = "RESTRICT"
            confidence = 0.99
            reason_codes.append("CONSERVATIVE_COLLATERAL_HAIRCUT_APPLIED")

        decision = DecisionResult(
            policy=self.policy,
            final_price=round(selected_price, 2),
            selected_source=selected_source,
            confidence=round(confidence, 2),
            reason_codes=reason_codes,
            policy_version="0.1.0-mvp"
        )

        # Collateral risk delta
        baseline_collateral = round(osm_val * ltv, 2)
        aegis_collateral = round(selected_price * ltv, 2)
        diff = round(baseline_collateral - aegis_collateral, 2)
        # Risk exposure overstatement percentage prevented (only positive when baseline was overstated)
        risk_pct = round((diff / max(abs(baseline_collateral), 1e-6)) * 100, 2) if diff > 0 else 0.0

        collateral = CollateralImpact(
            ltv=round(ltv, 2),
            baseline_value=baseline_collateral,
            aegis_value=aegis_collateral,
            difference=diff,
            risk_exposure_pct=risk_pct
        )

        return decision, collateral
