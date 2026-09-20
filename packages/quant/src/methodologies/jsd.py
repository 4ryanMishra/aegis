"""
Methodology Lane 3: Pairwise Jensen-Shannon Divergence (JSD) on Uncertainty Distributions.
Measures information-theoretic divergence between uncertainty profiles of oracle feeds.

Critical Mathematical Rule:
Does NOT treat the mixture distribution M = 0.5*(P_i + P_j) as Gaussian.
Operates on a deterministic finite probability grid:
1. Define a fixed probability grid covering a deterministic range.
2. Convert each supported uncertainty representation into a normalized discrete distribution over that grid.
3. Calculate pairwise KL terms on the discrete distributions.
4. Calculate symmetric JSD: JSD(P, Q) = 0.5 * D_KL(P || M) + 0.5 * D_KL(Q || M)
5. Compute per-lane centrality / mean divergence: d_i = mean_{j != i}(JSD(P_i, P_j))
6. Convert to deterministic weights: w_i = exp(-lambda * d_i) / sum(exp(-lambda * d_k))
"""

from typing import List, Dict, Any, Tuple, Optional
import math
import numpy as np
from pydantic import BaseModel, Field


class JSDLaneInput(BaseModel):
    lane_id: str
    estimate: float
    lower_bound: float
    upper_bound: float
    confidence_level: float = 0.95


class JSDResult(BaseModel):
    grid_min: float
    grid_max: float
    grid_bins: int
    log_base: str
    jsd_bound: float
    lane_ids: List[str]
    pairwise_jsd_matrix: List[List[float]]
    mean_divergence_per_lane: List[float]
    lane_weights: List[float]
    informational_disagreement: float
    consensus_price: float
    decision: str
    reason_code: str
    uncertainty_lower: float
    uncertainty_upper: float
    anomaly_score: float


class JensenShannonDivergence:
    """
    Deterministic Pairwise Jensen-Shannon Divergence Calculator over Discrete Grids.
    """

    def __init__(
        self,
        grid_bins: int = 200,
        weight_decay_lambda: float = 8.0,
        disagreement_threshold: float = 0.15,
    ):
        self.grid_bins = grid_bins
        self.weight_decay_lambda = weight_decay_lambda
        self.disagreement_threshold = disagreement_threshold

    def evaluate(self, lanes: List[JSDLaneInput]) -> JSDResult:
        if not lanes:
            raise ValueError("Lanes list cannot be empty for JSD evaluation.")

        n = len(lanes)
        lane_ids = [l.lane_id for l in lanes]
        estimates = np.array([l.estimate for l in lanes], dtype=np.float64)

        # Single lane trivial base case
        if n == 1:
            est = float(estimates[0])
            low = float(lanes[0].lower_bound)
            up = float(lanes[0].upper_bound)
            return JSDResult(
                grid_min=low,
                grid_max=up,
                grid_bins=self.grid_bins,
                log_base="log2",
                jsd_bound=1.0,
                lane_ids=lane_ids,
                pairwise_jsd_matrix=[[0.0]],
                mean_divergence_per_lane=[0.0],
                lane_weights=[1.0],
                informational_disagreement=0.0,
                consensus_price=est,
                decision="SINGLE_SOURCE_CONSISTENT",
                reason_code="SINGLE_DISTRIBUTION_TRIVIAL",
                uncertainty_lower=low,
                uncertainty_upper=up,
                anomaly_score=0.0,
            )

        # 1. Determine standard deviations from uncertainty bounds
        # For a 95% interval under explicit symmetric assumption: width = 2 * 1.96 * sigma
        sigmas = np.zeros(n, dtype=np.float64)
        for i, lane in enumerate(lanes):
            width = max(abs(lane.upper_bound - lane.lower_bound), 1e-4)
            sigmas[i] = width / (2.0 * 1.96)

        # 2. Define deterministic probability grid range [V_min, V_max]
        v_min = float(np.min(estimates - 4.0 * sigmas))
        v_max = float(np.max(estimates + 4.0 * sigmas))
        if v_max - v_min < 1e-4:
            v_min = estimates[0] - 1.0
            v_max = estimates[0] + 1.0

        grid = np.linspace(v_min, v_max, self.grid_bins)

        # 3. Discretize each lane's distribution over the grid
        prob_matrix = np.zeros((n, self.grid_bins), dtype=np.float64)
        for i in range(n):
            mu = estimates[i]
            sig = max(sigmas[i], 1e-6)
            # Evaluate Gaussian density on the discrete grid
            dens = np.exp(-0.5 * ((grid - mu) / sig) ** 2) / (math.sqrt(2 * math.pi) * sig)
            # Add uniform smoothing floor to ensure finite support and prevent division by zero
            dens += 1e-12
            # Normalize to valid discrete probability distribution: sum(P) = 1.0
            prob_matrix[i] = dens / np.sum(dens)

        # 4. Compute pairwise discrete Kullback-Leibler and JSD
        # JSD(P, Q) = 0.5 * D_KL(P || M) + 0.5 * D_KL(Q || M)
        # Using base 2 so JSD is strictly bounded in [0.0, 1.0]
        jsd_matrix = np.zeros((n, n), dtype=np.float64)

        for i in range(n):
            for j in range(i, n):
                if i == j:
                    jsd_matrix[i, j] = 0.0
                else:
                    p = prob_matrix[i]
                    q = prob_matrix[j]
                    m = 0.5 * (p + q)

                    # D_KL(P || M) = sum(P * log2(P / M))
                    kl_pm = np.sum(p * np.log2(p / m))
                    # D_KL(Q || M) = sum(Q * log2(Q / M))
                    kl_qm = np.sum(q * np.log2(q / m))

                    val = 0.5 * (kl_pm + kl_qm)
                    # Numerical clamp to valid theoretical range [0.0, 1.0]
                    val = max(0.0, min(1.0, float(val)))
                    jsd_matrix[i, j] = val
                    jsd_matrix[j, i] = val

        # 5. Compute per-lane centrality / mean divergence
        mean_div = np.zeros(n, dtype=np.float64)
        for i in range(n):
            other_indices = [j for j in range(n) if j != i]
            mean_div[i] = float(np.mean(jsd_matrix[i, other_indices]))

        overall_disagreement = float(np.mean(mean_div))

        # 6. Convert mean divergence into deterministic aggregation weights
        # Lower divergence from peers = higher centrality = higher consensus weight
        exp_weights = np.exp(-self.weight_decay_lambda * mean_div)
        sum_exp = np.sum(exp_weights)
        if sum_exp > 1e-12:
            lane_weights = exp_weights / sum_exp
        else:
            lane_weights = np.ones(n, dtype=np.float64) / n

        # 7. Informational consensus price & combined uncertainty
        consensus_price = float(np.sum(lane_weights * estimates))
        # Total variance = sum(w_i * (sigma_i^2 + (mu_i - mu_cons)^2))
        combined_var = float(np.sum(lane_weights * (sigmas ** 2 + (estimates - consensus_price) ** 2)))
        combined_std = math.sqrt(max(combined_var, 1e-10))

        # Decision & Anomaly classification
        if overall_disagreement < self.disagreement_threshold:
            decision = "INFORMATIONAL_CONSENSUS"
            reason_code = "JSD_CENTRALITY_CONVERGED"
            anomaly_score = min(0.3, overall_disagreement * 2.0)
        elif overall_disagreement < self.disagreement_threshold * 2.0:
            decision = "PARTIAL_DISAGREEMENT"
            reason_code = "ASYMMETRIC_UNCERTAINTY_SPREAD"
            anomaly_score = min(0.7, 0.3 + overall_disagreement * 2.0)
        else:
            decision = "INFORMATIONAL_DIVERGENCE_DETECTED"
            reason_code = "HIGH_PAIRWISE_JSD_DISAGREEMENT"
            anomaly_score = min(1.0, 0.5 + overall_disagreement * 2.0)

        lower = round(consensus_price - 1.96 * combined_std, 4)
        upper = round(consensus_price + 1.96 * combined_std, 4)

        return JSDResult(
            grid_min=round(v_min, 4),
            grid_max=round(v_max, 4),
            grid_bins=self.grid_bins,
            log_base="log2",
            jsd_bound=1.0,
            lane_ids=lane_ids,
            pairwise_jsd_matrix=[[round(float(c), 6) for c in row] for row in jsd_matrix],
            mean_divergence_per_lane=[round(float(d), 6) for d in mean_div],
            lane_weights=[round(float(w), 4) for w in lane_weights],
            informational_disagreement=round(overall_disagreement, 6),
            consensus_price=round(consensus_price, 4),
            decision=decision,
            reason_code=reason_code,
            uncertainty_lower=lower,
            uncertainty_upper=upper,
            anomaly_score=round(anomaly_score, 4),
        )
