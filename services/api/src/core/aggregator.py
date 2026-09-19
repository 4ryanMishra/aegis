"""
P_DEC Aggregator.
Deterministic aggregation of independent validator submissions.
Computes median consensus, interquartile dispersion, and quorum validation.
"""

from typing import List, Optional
import numpy as np
from ..models.schema import ValidatorObservation, DECAggregate, DataStatus


class P_DECAggregator:
    def __init__(self, min_quorum: int = 3, method: str = "median"):
        self.min_quorum = min_quorum
        self.method = method

    def aggregate(self, observations: List[ValidatorObservation]) -> DECAggregate:
        if not observations or len(observations) < self.min_quorum:
            return DECAggregate(
                value=None,
                aggregation=self.method,
                validator_count=len(observations),
                dispersion=0.0,
                quorum_met=False,
                status=DataStatus.SIMULATED
            )

        prices = [obs.estimated_price for obs in observations]
        
        # Deterministic robust calculation using median
        if self.method == "median":
            aggregate_val = float(np.median(prices))
        elif self.method == "trimmed_mean":
            # 20% trimmed mean
            p_sorted = sorted(prices)
            k = max(1, int(len(p_sorted) * 0.2))
            trimmed = p_sorted[k:-k] if len(p_sorted) > 2 * k else p_sorted
            aggregate_val = float(np.mean(trimmed))
        else:
            aggregate_val = float(np.mean(prices))

        # Normalized Dispersion (IQR / Median or StdDev / Mean)
        q75, q25 = np.percentile(prices, [75, 25])
        iqr = q75 - q25
        norm_dispersion = float(iqr / max(abs(aggregate_val), 1e-6))

        return DECAggregate(
            value=round(aggregate_val, 2),
            aggregation=self.method,
            validator_count=len(observations),
            dispersion=round(norm_dispersion, 4),
            quorum_met=True,
            status=DataStatus.SIMULATED
        )
