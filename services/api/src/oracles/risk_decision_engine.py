"""
AEGIS Risk Decision Engine Mirror (Python Implementation).
Transparent deterministic risk policy evaluating Multipli OSM against cross-oracle consensus.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from services.api.src.oracles.consensus_engine import ConsensusMetrics, OracleObservationData


@dataclass
class RiskDecisionOutput:
    state: str  # "HEALTHY_CONSENSUS", "MULTIPLI_DEVIATION", "SOURCE_DEGRADED", "NO_CONSENSUS", "MARKET_CORROBORATED", "ORACLE_INSTABILITY"
    oracle_status: str  # "HEALTHY_CONSENSUS", "SUSPECTED_INCONSISTENCY", "EVIDENCE_OF_ABNORMAL_DEVIATION", "HALTED_CIRCUIT_BREAKER"
    final_price: float
    multipli_deviation_pct: float
    is_conservative_applied: bool
    policy_rationale: str
    effective_ltv: float
    protocol_state: str  # "NORMAL", "RESTRICTED", "HALTED"


class RiskDecisionEngine:
    """
    Evaluates cross-oracle consensus metrics against Multipli OSM and terminal market reference.
    """

    def __init__(
        self,
        normal_threshold_pct: float = 0.50,      # 0.50% normal tolerance
        deviation_threshold_pct: float = 1.00,   # 1.00% triggers conservative haircut
        critical_threshold_pct: float = 3.00,    # 3.00% critical divergence
        standard_ltv: float = 0.80,              # 80% LTV under NORMAL
        restricted_ltv: float = 0.50,            # 50% LTV under RESTRICTED
    ):
        self.normal_threshold_pct = normal_threshold_pct
        self.deviation_threshold_pct = deviation_threshold_pct
        self.critical_threshold_pct = critical_threshold_pct
        self.standard_ltv = standard_ltv
        self.restricted_ltv = restricted_ltv

    def evaluate_decision(
        self,
        consensus: ConsensusMetrics,
        multipli_obs: Optional[OracleObservationData],
        market_ref_price: Optional[float] = None,
    ) -> RiskDecisionOutput:
        # Case 1: Total lack of consensus among external sources
        if not consensus.has_strong_consensus or consensus.consensus_price <= 0:
            if market_ref_price is not None and market_ref_price > 0 and consensus.consensus_price > 0:
                mkt_dev = abs(market_ref_price - consensus.consensus_price) / consensus.consensus_price * 100.0
                if mkt_dev <= self.normal_threshold_pct:
                    return RiskDecisionOutput(
                        state="MARKET_CORROBORATED",
                        oracle_status="SUSPECTED_INCONSISTENCY",
                        final_price=round(consensus.consensus_price, 2),
                        multipli_deviation_pct=round(mkt_dev, 2),
                        is_conservative_applied=True,
                        policy_rationale="No dominant oracle cluster, but terminal market reference corroborates consensus median.",
                        effective_ltv=self.restricted_ltv,
                        protocol_state="RESTRICTED",
                    )

            return RiskDecisionOutput(
                state="ORACLE_INSTABILITY",
                oracle_status="HALTED_CIRCUIT_BREAKER",
                final_price=0.0,
                multipli_deviation_pct=0.0,
                is_conservative_applied=False,
                policy_rationale="Oracle ecosystem in bimodal/severe disagreement without resolving reference; emergency halt engaged.",
                effective_ltv=0.0,
                protocol_state="HALTED",
            )

        # Case 2: Multipli OSM feed is missing or failed
        if multipli_obs is None or not multipli_obs.valid or multipli_obs.price <= 0:
            return RiskDecisionOutput(
                state="SOURCE_DEGRADED",
                oracle_status="SUSPECTED_INCONSISTENCY",
                final_price=round(consensus.consensus_price, 2),
                multipli_deviation_pct=0.0,
                is_conservative_applied=False,
                policy_rationale="Multipli OSM feed unavailable or delayed; routed to authoritative cross-oracle consensus.",
                effective_ltv=self.restricted_ltv,
                protocol_state="RESTRICTED",
            )

        # Case 3: Calculate Multipli deviation from cross-oracle consensus
        p_osm = multipli_obs.price
        p_consensus = consensus.consensus_price
        dev_pct = round(abs(p_osm - p_consensus) / max(0.0001, p_consensus) * 100.0, 2)

        # Sub-case A: Normal Convergence (Multipli agrees within 0.5%)
        if dev_pct <= self.normal_threshold_pct:
            return RiskDecisionOutput(
                state="HEALTHY_CONSENSUS",
                oracle_status="HEALTHY_CONSENSUS",
                final_price=round(p_osm, 2),
                multipli_deviation_pct=dev_pct,
                is_conservative_applied=False,
                policy_rationale=f"Multipli OSM (${p_osm:.2f}) agrees with cross-oracle consensus (${p_consensus:.2f}) within normal tolerance (<= 0.50%).",
                effective_ltv=self.standard_ltv,
                protocol_state="NORMAL",
            )

        # Sub-case B: Material Multipli Divergence (e.g. Flash Crash / Delayed OSM)
        conservative_price = min(p_osm, p_consensus)
        status = "EVIDENCE_OF_ABNORMAL_DEVIATION" if dev_pct >= self.critical_threshold_pct else "SUSPECTED_INCONSISTENCY"

        return RiskDecisionOutput(
            state="MULTIPLI_DEVIATION",
            oracle_status=status,
            final_price=round(conservative_price, 2),
            multipli_deviation_pct=dev_pct,
            is_conservative_applied=True,
            policy_rationale=f"Multipli OSM (${p_osm:.2f}) diverged from cross-oracle consensus (${p_consensus:.2f}) by {dev_pct}%. Conservative valuation min(P_OSM, P_CONSENSUS) = ${conservative_price:.2f} enforced to prevent collateral overstatement and bad debt.",
            effective_ltv=self.restricted_ltv,
            protocol_state="RESTRICTED",
        )
