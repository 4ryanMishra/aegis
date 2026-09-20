"""
AEGIS On-Chain Consensus Engine Mirror (Python Implementation).
Deterministic price-band agreement clustering without machine learning or statistical modeling.
"""

from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field


@dataclass
class OracleObservationData:
    source_id: str
    name: str
    price: float
    updated_at: int
    age_seconds: int
    status: str  # "ACTIVE", "STALE", "DELAYED", "FAILED", "DISABLED"
    confidence: Optional[float] = None
    has_confidence: bool = False
    valid: bool = True
    cluster_id: Optional[str] = None


@dataclass
class ConsensusMetrics:
    consensus_price: float
    cluster_size: int
    total_eligible: int
    agreement_ratio: float  # [0.0, 1.0] e.g. 0.857 (85.7%)
    cluster_min: float
    cluster_max: float
    cluster_spread_pct: float  # (cluster_max - cluster_min) / consensus_price * 100
    has_strong_consensus: bool
    cluster_members: List[str] = field(default_factory=list)
    outlier_members: List[str] = field(default_factory=list)


class ConsensusEngine:
    """
    Deterministic price-band agreement clustering.
    Given N eligible oracle prices:
    1. Sort prices.
    2. Find largest cluster where (P_max - P_min) / P_median <= cluster_tolerance (e.g. 0.5%).
    3. Calculate P_CONSENSUS = median(cluster prices).
    """

    def __init__(
        self,
        cluster_tolerance_pct: float = 0.50,  # 0.5% max spread within cluster
        min_quorum: int = 3,                  # Minimum 3 feeds for strong consensus
        min_agreement_ratio: float = 0.60,    # 60% agreement required
    ):
        self.cluster_tolerance_pct = cluster_tolerance_pct
        self.min_quorum = min_quorum
        self.min_agreement_ratio = min_agreement_ratio

    def compute_consensus(self, observations: List[OracleObservationData]) -> ConsensusMetrics:
        # Filter valid and active observations
        eligible = [obs for obs in observations if obs.valid and obs.status == "ACTIVE" and obs.price > 0]
        n = len(eligible)

        if n == 0:
            return ConsensusMetrics(
                consensus_price=0.0,
                cluster_size=0,
                total_eligible=0,
                agreement_ratio=0.0,
                cluster_min=0.0,
                cluster_max=0.0,
                cluster_spread_pct=0.0,
                has_strong_consensus=False,
                cluster_members=[],
                outlier_members=[obs.source_id for obs in observations],
            )

        if n == 1:
            return ConsensusMetrics(
                consensus_price=round(eligible[0].price, 2),
                cluster_size=1,
                total_eligible=1,
                agreement_ratio=1.0,
                cluster_min=round(eligible[0].price, 2),
                cluster_max=round(eligible[0].price, 2),
                cluster_spread_pct=0.0,
                has_strong_consensus=(self.min_quorum <= 1),
                cluster_members=[eligible[0].source_id],
                outlier_members=[],
            )

        # 1. Sort by price
        sorted_obs = sorted(eligible, key=lambda x: x.price)
        prices = [x.price for x in sorted_obs]

        best_start = 0
        best_end = 0
        best_size = 0
        best_spread = float("inf")

        # 2. Find largest cluster within tolerance
        for i in range(n):
            for j in range(i, n):
                size = j - i + 1
                median_idx = i + (size - 1) // 2
                current_median = prices[median_idx]

                if current_median <= 0:
                    continue

                spread_pct = ((prices[j] - prices[i]) / current_median) * 100.0

                if spread_pct <= self.cluster_tolerance_pct:
                    if size > best_size or (size == best_size and spread_pct < best_spread):
                        best_size = size
                        best_start = i
                        best_end = j
                        best_spread = spread_pct

        if best_size == 0:
            # Fallback to overall median if no cluster meets tolerance
            overall_median = prices[n // 2]
            spread_pct = ((prices[-1] - prices[0]) / max(0.0001, overall_median)) * 100.0
            return ConsensusMetrics(
                consensus_price=round(overall_median, 2),
                cluster_size=1,
                total_eligible=n,
                agreement_ratio=round(1.0 / n, 4),
                cluster_min=round(prices[0], 2),
                cluster_max=round(prices[-1], 2),
                cluster_spread_pct=round(spread_pct, 3),
                has_strong_consensus=False,
                cluster_members=[],
                outlier_members=[x.source_id for x in sorted_obs],
            )

        cluster_median = prices[best_start + (best_size - 1) // 2]
        agreement_ratio = round(best_size / n, 4)
        has_strong = (best_size >= self.min_quorum) and (agreement_ratio >= self.min_agreement_ratio)

        cluster_members = [sorted_obs[k].source_id for k in range(best_start, best_end + 1)]
        outlier_members = [sorted_obs[k].source_id for k in range(n) if k < best_start or k > best_end]

        return ConsensusMetrics(
            consensus_price=round(cluster_median, 2),
            cluster_size=best_size,
            total_eligible=n,
            agreement_ratio=agreement_ratio,
            cluster_min=round(prices[best_start], 2),
            cluster_max=round(prices[best_end], 2),
            cluster_spread_pct=round(best_spread, 3),
            has_strong_consensus=has_strong,
            cluster_members=cluster_members,
            outlier_members=outlier_members,
        )
