"""
Methodology Lane 5: Page CUSUM Sequential Drift Detection.
Detects persistent directional drift under a specified calibrated baseline process.

Mathematical Form:
S_plus(k) = max(0, S_plus(k-1) + y_k - kappa)
S_minus(k) = max(0, S_minus(k-1) - y_k - kappa)

Claims Policy:
Do NOT claim CUSUM eliminates manipulation.
Describe as: 'Detects persistent directional drift under a specified calibrated baseline process.'
"""

from typing import List, Dict, Any, Optional
import math
import numpy as np
from pydantic import BaseModel, Field


class CUSUMHistoryPoint(BaseModel):
    step: int
    price: float
    standardized_increment: float
    s_plus: float
    s_minus: float
    threshold_h: float
    trip_state: str


class CUSUMResult(BaseModel):
    current_increment: float
    s_plus: float
    s_minus: float
    kappa: float
    threshold_h: float
    trip_state: str  # NORMAL, DRIFT, TRIP, RECOVERY
    direction: str   # POSITIVE_DRIFT, NEGATIVE_DRIFT, STATIONARY
    decision: str
    reason_code: str
    history_series: List[CUSUMHistoryPoint]
    estimated_price: float
    uncertainty_lower: float
    uncertainty_upper: float
    anomaly_score: float


class PageCUSUM:
    """
    Deterministic Two-Sided Page CUSUM Sequential Drift Detector.
    """

    def __init__(
        self,
        kappa: float = 0.5,        # Allowance / slack parameter
        threshold_h: float = 4.0,  # Decision threshold parameter
    ):
        self.kappa = kappa
        self.threshold_h = threshold_h

    def evaluate_series(
        self,
        prices: List[float],
        baseline_price: Optional[float] = None,
        baseline_volatility: Optional[float] = None,
    ) -> CUSUMResult:
        if not prices:
            raise ValueError("Prices sequence cannot be empty for CUSUM evaluation.")

        n = len(prices)
        ref_price = float(baseline_price if baseline_price is not None else prices[0])
        
        # Estimate or use provided baseline sigma
        if baseline_volatility is not None and baseline_volatility > 0.0:
            sigma = float(baseline_volatility)
        elif n >= 5:
            # Empirical standard deviation
            sigma = max(float(np.std(prices)), 1e-4)
        else:
            sigma = max(ref_price * 0.005, 1e-4)

        s_plus = 0.0
        s_minus = 0.0
        history: List[CUSUMHistoryPoint] = []

        for k, p in enumerate(prices):
            # Standardized increment: y_k = (P_k - P_ref) / sigma
            y_k = (float(p) - ref_price) / sigma

            s_plus = max(0.0, s_plus + y_k - self.kappa)
            s_minus = max(0.0, s_minus - y_k - self.kappa)

            max_s = max(s_plus, s_minus)
            if max_s >= self.threshold_h:
                step_state = "TRIP"
            elif max_s >= self.threshold_h * 0.5:
                step_state = "DRIFT"
            else:
                step_state = "NORMAL"

            history.append(
                CUSUMHistoryPoint(
                    step=k,
                    price=round(float(p), 4),
                    standardized_increment=round(float(y_k), 4),
                    s_plus=round(float(s_plus), 4),
                    s_minus=round(float(s_minus), 4),
                    threshold_h=round(self.threshold_h, 4),
                    trip_state=step_state,
                )
            )

        # Final state evaluation
        latest_price = float(prices[-1])
        latest_y = (latest_price - ref_price) / sigma
        max_s = max(s_plus, s_minus)

        if s_plus > s_minus:
            direction = "POSITIVE_DRIFT" if s_plus > 0.5 else "STATIONARY"
        elif s_minus > s_plus:
            direction = "NEGATIVE_DRIFT" if s_minus > 0.5 else "STATIONARY"
        else:
            direction = "STATIONARY"

        if max_s >= self.threshold_h:
            trip_state = "TRIP"
            decision = "SEQUENTIAL_DRIFT_DETECTED"
            reason_code = "CUSUM_ACCUMULATOR_TRIPPED"
            anomaly_score = min(1.0, 0.7 + min(0.3, (max_s - self.threshold_h) / 5.0))
        elif max_s >= self.threshold_h * 0.5:
            trip_state = "DRIFT"
            decision = "PERSISTENT_DRIFT_WARNING"
            reason_code = "CUSUM_ACCUMULATOR_ELEVATED"
            anomaly_score = min(0.65, 0.35 + (max_s / self.threshold_h) * 0.3)
        else:
            trip_state = "NORMAL"
            decision = "BASELINE_STATIONARY"
            reason_code = "CUSUM_STATIONARY_REGIME"
            anomaly_score = min(0.2, (max_s / (self.threshold_h * 0.5)) * 0.2)

        # Conservative bounds around latest price incorporating cumulative drift
        drift_adjustment = (s_plus - s_minus) * 0.5 * sigma
        lower_bound = latest_price - 1.96 * sigma - max(0.0, -drift_adjustment)
        upper_bound = latest_price + 1.96 * sigma + max(0.0, drift_adjustment)

        return CUSUMResult(
            current_increment=round(float(latest_y), 4),
            s_plus=round(float(s_plus), 4),
            s_minus=round(float(s_minus), 4),
            kappa=round(self.kappa, 4),
            threshold_h=round(self.threshold_h, 4),
            trip_state=trip_state,
            direction=direction,
            decision=decision,
            reason_code=reason_code,
            history_series=history,
            estimated_price=round(latest_price, 4),
            uncertainty_lower=round(lower_bound, 4),
            uncertainty_upper=round(upper_bound, 4),
            anomaly_score=round(anomaly_score, 4),
        )
