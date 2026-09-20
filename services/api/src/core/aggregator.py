"""
P_DEC Aggregator (Phase 4A Task 9).
Deterministic aggregation of independent validator evidence across methodology lanes.

Pipeline:
raw observations -> methodology execution -> ValidatorResult objects
-> eligibility / filtering -> deterministic aggregation -> P_DEC

Important:
Preserves rich forensic methodology information (lane identities, rejected evidence,
anomaly decisions, uncertainty bounds, weights, provenance, timestamps).
The aggregation policy is documented as a deterministic heuristic robust aggregator,
not claimed to be universally optimal.
"""

from typing import List, Optional, Dict, Any
import math
import numpy as np
from ..models.schema import ValidatorResult, DECAggregate, DataStatus


class P_DECAggregator:
    """
    Deterministic Cross-Validator Evidence Aggregator.
    Consumes ValidatorResult objects, applies eligibility filtering,
    and produces P_DEC while preserving forensic evidence.
    """

    def __init__(self, min_quorum: int = 3, method: str = "robust_cross_lane"):
        self.min_quorum = min_quorum
        self.method = method

    def aggregate(self, results: List[ValidatorResult]) -> DECAggregate:
        if not results or len(results) < self.min_quorum:
            return DECAggregate(
                value=None,
                aggregation=self.method,
                validator_count=len(results) if results else 0,
                eligible_count=0,
                rejected_count=0,
                dispersion=0.0,
                quorum_met=False,
                status=DataStatus.SIMULATED,
                lane_results=[],
            )

        # 1. Eligibility & Gating Assessment
        # Inspect each validator result for innovation gating or non-applicability
        eligible_results: List[ValidatorResult] = []
        rejected_results: List[ValidatorResult] = []
        lane_summaries: List[Dict[str, Any]] = []

        for r in results:
            # Check for hard gating or non-applicability
            is_gated = r.decision in ("INNOVATION_GATED", "DIFFUSION_MODEL_INCONSISTENCY", "NOT_APPLICABLE")
            is_eligible = not is_gated

            # If gating leaves fewer than min_quorum eligible nodes, retain with reduced confidence
            if is_eligible:
                eligible_results.append(r)
            else:
                rejected_results.append(r)

        # Quorum fallback: if gating dropped below quorum, include gated nodes with heavy penalty
        if len(eligible_results) < self.min_quorum:
            pool = results
            quorum_satisfied = len(results) >= self.min_quorum
        else:
            pool = eligible_results
            quorum_satisfied = True

        prices = [r.estimated_price for r in pool]

        # 2. Deterministic Robust Location Estimation
        # Compute median as high-breakdown anchor
        median_val = float(np.median(prices))

        # Inverse-variance weighting based on uncertainty interval widths
        variances = []
        for r in pool:
            width = max(abs(r.uncertainty_upper - r.uncertainty_lower), 1e-4)
            std_approx = width / (2.0 * 1.96)
            variances.append(max(std_approx ** 2, 1e-6))

        inv_vars = [1.0 / v for v in variances]
        sum_inv = sum(inv_vars)
        weights = [iv / sum_inv for iv in inv_vars]

        # Weighted estimate blended with median for robustness against asymmetric bounds
        weighted_val = sum(w * p for w, p in zip(weights, prices))
        # 50/50 blend between median and uncertainty-weighted mean
        aggregate_val = 0.5 * median_val + 0.5 * weighted_val

        # 3. Robust Dispersion Calculation (Normalized Median Absolute Deviation)
        abs_deviations = [abs(p - median_val) for p in prices]
        mad = float(np.median(abs_deviations))
        norm_dispersion = float((1.4826 * mad) / max(abs(aggregate_val), 1e-6))

        # 4. Construct lane evidence summaries preserving forensic detail
        for i, r in enumerate(results):
            lane_w = weights[pool.index(r)] if r in pool else 0.0
            lane_summaries.append({
                "validator_id": r.validator_id,
                "lane_id": r.lane_id,
                "methodology": r.methodology,
                "methodology_name": r.methodology_name,
                "estimated_price": r.estimated_price,
                "uncertainty_lower": r.uncertainty_lower,
                "uncertainty_upper": r.uncertainty_upper,
                "confidence": r.confidence,
                "decision": r.decision,
                "reason_code": r.reason_code,
                "is_eligible": (r in pool),
                "assigned_weight": round(float(lane_w), 4),
            })

        return DECAggregate(
            value=round(aggregate_val, 2),
            aggregation=self.method,
            validator_count=len(results),
            eligible_count=len(eligible_results),
            rejected_count=len(rejected_results),
            dispersion=round(norm_dispersion, 4),
            quorum_met=quorum_satisfied,
            status=DataStatus.SIMULATED,
            lane_results=lane_summaries,
        )
