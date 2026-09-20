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
    Consumes ValidatorResult objects, separates price-estimating lanes from diagnostic lanes,
    applies innovation gating and outlier filtering to price estimators,
    and produces P_DEC while preserving full forensic evidence across all lanes.
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

        # 1. Separate Price Estimators from Diagnostic Lanes
        price_estimators = [
            r for r in results
            if getattr(r, "is_price_estimator", False) and r.estimated_price is not None
        ]
        # Fallback for backward compatibility if is_price_estimator is missing but estimated_price is given
        if not price_estimators and results:
            price_estimators = [r for r in results if r.estimated_price is not None]

        # 2. Eligibility & Gating Assessment on Price Estimators
        eligible_price_estimators: List[ValidatorResult] = []
        rejected_price_estimators: List[ValidatorResult] = []

        for r in price_estimators:
            # Check for hard gating or disqualification
            is_gated = r.decision in ("INNOVATION_GATED", "DISQUALIFIED")
            if is_gated:
                rejected_price_estimators.append(r)
            else:
                eligible_price_estimators.append(r)

        # Determine price estimator pool
        if eligible_price_estimators:
            pool = eligible_price_estimators
        elif price_estimators:
            # All price estimators gated: fallback to held posterior states
            pool = price_estimators
        else:
            pool = []

        # 3. Calculate P_DEC from Price Estimators Pool
        if not pool:
            aggregate_val = None
            norm_dispersion = 0.0
            weights: List[float] = []
        elif len(pool) == 1:
            # Single uncontaminated estimator (e.g. Huber uncontaminated when Kalman is gated)
            aggregate_val = pool[0].estimated_price
            norm_dispersion = 0.0
            weights = [1.0]
        else:
            prices = [r.estimated_price for r in pool if r.estimated_price is not None]
            median_val = float(np.median(prices))

            # Inverse-variance weighting based on uncertainty interval widths
            variances = []
            for r in pool:
                if r.uncertainty_upper is not None and r.uncertainty_lower is not None:
                    width = max(abs(r.uncertainty_upper - r.uncertainty_lower), 1e-4)
                else:
                    width = 1.0
                std_approx = width / (2.0 * 1.96)
                variances.append(max(std_approx ** 2, 1e-6))

            inv_vars = [1.0 / v for v in variances]
            sum_inv = sum(inv_vars)
            weights = [iv / sum_inv for iv in inv_vars]

            weighted_val = sum(w * p for w, p in zip(weights, prices))
            # 50/50 blend between median and uncertainty-weighted mean
            aggregate_val = 0.5 * median_val + 0.5 * weighted_val

            abs_deviations = [abs(p - median_val) for p in prices]
            mad = float(np.median(abs_deviations))
            norm_dispersion = float((1.4826 * mad) / max(abs(aggregate_val), 1e-6))

        # 4. Construct lane evidence summaries preserving forensic detail across all lanes
        lane_summaries: List[Dict[str, Any]] = []
        for r in results:
            is_in_pool = (r in pool)
            assigned_w = weights[pool.index(r)] if is_in_pool else 0.0
            lane_summaries.append({
                "validator_id": r.validator_id,
                "lane_id": r.lane_id,
                "methodology": r.methodology,
                "methodology_name": r.methodology_name,
                "role": getattr(r, "role", None),
                "is_price_estimator": getattr(r, "is_price_estimator", True),
                "estimated_price": r.estimated_price,
                "uncertainty_lower": r.uncertainty_lower,
                "uncertainty_upper": r.uncertainty_upper,
                "confidence": r.confidence,
                "decision": r.decision,
                "reason_code": r.reason_code,
                "is_eligible": is_in_pool,
                "assigned_weight": round(float(assigned_w), 4),
                "diagnostic_evidence": getattr(r, "diagnostic_evidence", {}),
            })

        return DECAggregate(
            value=round(aggregate_val, 2) if aggregate_val is not None else None,
            aggregation=self.method,
            validator_count=len(results),
            eligible_count=len(eligible_price_estimators),
            rejected_count=len(rejected_price_estimators),
            dispersion=round(norm_dispersion, 4),
            quorum_met=len(results) >= self.min_quorum,
            status=DataStatus.SIMULATED,
            lane_results=lane_summaries,
        )
