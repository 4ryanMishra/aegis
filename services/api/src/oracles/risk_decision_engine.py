"""
AEGIS Risk Decision Engine Mirror (Python Implementation).
Transparent deterministic risk policy evaluating Multipli OSM against cross-oracle consensus.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from services.api.src.oracles.consensus_engine import ConsensusMetrics, OracleObservationData


@dataclass
class RiskDecisionOutput:
    state: str  # "HEALTHY_CONSENSUS", "MULTIPLI_DEVIATION", "OUTLIER_DETECTED", "SOURCE_DEGRADED", "NO_CONSENSUS", "MARKET_CORROBORATED", "ORACLE_INSTABILITY", "CONSENSUS_RESTORED"
    oracle_status: str  # "HEALTHY_CONSENSUS", "SUSPECTED_INCONSISTENCY", "EVIDENCE_OF_ABNORMAL_DEVIATION", "HALTED_CIRCUIT_BREAKER"
    final_price: float
    selected_source: str  # "MULTIPLI_OSM", "CONSENSUS_MEDIAN", "MARKET_REFERENCE", "CONSERVATIVE_MIN", "NONE"
    consensus_price: float
    cluster_size: int
    total_eligible: int
    multipli_deviation_pct: float
    is_conservative_applied: bool
    market_reference_used: bool
    protocol_state: str  # "NORMAL", "RESTRICTED", "HALTED"
    effective_ltv: float
    policy_rationale: str
    action: str = "ALLOW"  # "ALLOW", "RESTRICT", "HALT"
    decision: str = "VERIFIED"  # "VERIFIED", "WARNING", "RESTRICTED", "HALTED"
    policy: str = "USE_OSM"  # "USE_OSM", "ROBUST_MEDIAN", "RESTRICT", "CIRCUIT_BREAKER_HALT"
    reason_codes: List[str] = field(default_factory=list)


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
        # Case 1: Total lack of consensus among external sources (Bimodal / Dispersed)
        if not consensus.has_strong_consensus or consensus.consensus_price <= 0:
            if market_ref_price is not None and market_ref_price > 0 and consensus.consensus_price > 0:
                mkt_dev = abs(market_ref_price - consensus.consensus_price) / consensus.consensus_price * 100.0
                if mkt_dev <= self.normal_threshold_pct:
                    return RiskDecisionOutput(
                        state="MARKET_CORROBORATED",
                        oracle_status="SUSPECTED_INCONSISTENCY",
                        final_price=round(market_ref_price, 2),
                        selected_source="MARKET_REFERENCE",
                        consensus_price=round(consensus.consensus_price, 2),
                        cluster_size=consensus.cluster_size,
                        total_eligible=consensus.total_eligible,
                        multipli_deviation_pct=round(mkt_dev, 2),
                        is_conservative_applied=True,
                        market_reference_used=True,
                        protocol_state="RESTRICTED",
                        effective_ltv=self.restricted_ltv,
                        policy_rationale="No dominant oracle cluster, but terminal market reference corroborates cluster median. Conservative restricted valuation enforced.",
                        action="RESTRICT",
                        decision="RESTRICTED",
                        policy="NEAREST_TO_MARKET",
                        reason_codes=["MARKET_CORROBORATED", "BIMODAL_RESOLVED"],
                    )

            # Uncorroborated lack of consensus
            return RiskDecisionOutput(
                state="ORACLE_INSTABILITY",
                oracle_status="HALTED_CIRCUIT_BREAKER",
                final_price=0.0,
                selected_source="NONE",
                consensus_price=round(consensus.consensus_price, 2) if consensus.consensus_price > 0 else 0.0,
                cluster_size=consensus.cluster_size,
                total_eligible=consensus.total_eligible,
                multipli_deviation_pct=0.0,
                is_conservative_applied=False,
                market_reference_used=False,
                protocol_state="HALTED",
                effective_ltv=0.0,
                policy_rationale="Oracle ecosystem in bimodal/severe disagreement without resolving market reference. Circuit breaker active; borrowing halted.",
                action="HALT",
                decision="HALTED",
                policy="CIRCUIT_BREAKER_HALT",
                reason_codes=["NO_STRONG_CONSENSUS", "ORACLE_INSTABILITY"],
            )

        # Case 2: Multipli OSM feed is missing or failed
        if multipli_obs is None or not multipli_obs.valid or multipli_obs.price <= 0:
            return RiskDecisionOutput(
                state="SOURCE_DEGRADED",
                oracle_status="SUSPECTED_INCONSISTENCY",
                final_price=round(consensus.consensus_price, 2),
                selected_source="CONSENSUS_MEDIAN",
                consensus_price=round(consensus.consensus_price, 2),
                cluster_size=consensus.cluster_size,
                total_eligible=consensus.total_eligible,
                multipli_deviation_pct=0.0,
                is_conservative_applied=False,
                market_reference_used=False,
                protocol_state="RESTRICTED",
                effective_ltv=self.restricted_ltv,
                policy_rationale="Multipli OSM feed unavailable; routed to authoritative cross-oracle consensus median.",
                action="RESTRICT",
                decision="WARNING",
                policy="ROBUST_MEDIAN",
                reason_codes=["OSM_FEED_UNAVAILABLE", "ROUTED_TO_CONSENSUS"],
            )

        # Case 3: Calculate Multipli deviation from cross-oracle consensus
        p_osm = multipli_obs.price
        p_consensus = consensus.consensus_price
        dev_pct = round(abs(p_osm - p_consensus) / max(0.0001, p_consensus) * 100.0, 2)

        # Sub-case A: Normal Convergence (Multipli agrees within 0.50%)
        if dev_pct <= self.normal_threshold_pct:
            has_outliers = len(consensus.outlier_members) > 0
            state_name = "OUTLIER_DETECTED" if has_outliers else "HEALTHY_CONSENSUS"
            
            return RiskDecisionOutput(
                state=state_name,
                oracle_status="HEALTHY_CONSENSUS",
                final_price=round(p_osm, 2),
                selected_source="MULTIPLI_OSM",
                consensus_price=round(p_consensus, 2),
                cluster_size=consensus.cluster_size,
                total_eligible=consensus.total_eligible,
                multipli_deviation_pct=dev_pct,
                is_conservative_applied=False,
                market_reference_used=False,
                protocol_state="NORMAL",
                effective_ltv=self.standard_ltv,
                policy_rationale=f"Multipli OSM (${p_osm:.2f}) agrees with cross-oracle consensus (${p_consensus:.2f}) within normal tolerance (<= 0.50%).",
                action="ALLOW",
                decision="VERIFIED",
                policy="USE_OSM",
                reason_codes=["CONSENSUS_VERIFIED", "NORMAL_TOLERANCE"],
            )

        # Sub-case B: Material Multipli Divergence (e.g. Flash Crash / Delayed OSM)
        conservative_price = min(p_osm, p_consensus)
        selected_src = "CONSERVATIVE_MIN" if conservative_price < p_osm else "MULTIPLI_OSM"
        status = "EVIDENCE_OF_ABNORMAL_DEVIATION" if dev_pct >= self.critical_threshold_pct else "SUSPECTED_INCONSISTENCY"

        return RiskDecisionOutput(
            state="MULTIPLI_DEVIATION",
            oracle_status=status,
            final_price=round(conservative_price, 2),
            selected_source=selected_src,
            consensus_price=round(p_consensus, 2),
            cluster_size=consensus.cluster_size,
            total_eligible=consensus.total_eligible,
            multipli_deviation_pct=dev_pct,
            is_conservative_applied=True,
            market_reference_used=False,
            protocol_state="RESTRICTED",
            effective_ltv=self.restricted_ltv,
            policy_rationale=f"Multipli OSM (${p_osm:.2f}) diverged from cross-oracle consensus (${p_consensus:.2f}) by {dev_pct}%. Conservative valuation min(P_OSM, P_CONSENSUS) = ${conservative_price:.2f} enforced to prevent collateral overstatement and bad debt.",
            action="RESTRICT",
            decision="RESTRICTED",
            policy="RESTRICT",
            reason_codes=["MULTIPLI_DEVIATION_ALERT", "CONSERVATIVE_PRICE_ENFORCED", "LTV_DAMPENED"],
        )
