"""
Standard Benchmark Baseline Strategies.
Serves as reference controls (Naive Persistence, SMA, EWMA) for methodology evaluation.
"""

from typing import List, Optional
import numpy as np
from .strategy_base import ValidatorStrategy, InputContext
from .models import ValidatorPrediction


class NaivePersistenceStrategy(ValidatorStrategy):
    """Baseline 1: Random-walk persistence forecast (y_hat_{t+h} = y_t)."""

    @property
    def method_id(self) -> str:
        return "bench_naive_persistence"

    @property
    def method_name(self) -> str:
        return "Naive Persistence Baseline"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return ["spot_feed_last_tick"]

    @property
    def assumptions(self) -> List[str]:
        return ["Asset price follows a martingale / random walk with zero expected drift."]

    @property
    def limitations(self) -> List[str]:
        return ["Cannot capture mean reversion, trending regimes, or intraday orderbook dynamics."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        window = context.get_input_window()
        latest = context.latest_observation
        curr_price = latest.price if latest else 100.0

        # Estimate empirical variance from available window
        if len(context.history) >= 5:
            prices = [obs.price for obs in context.history]
            std = float(np.std(prices))
        else:
            std = curr_price * 0.015

        lower = round(curr_price - 1.96 * std, 4)
        upper = round(curr_price + 1.96 * std, 4)

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=round(curr_price, 4),
            lower_bound=lower,
            upper_bound=upper,
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=window,
            status="SIMULATED",
            metadata={"baseline_type": "MARTINGALE_PERSISTENCE"}
        )


class SimpleMovingAverageStrategy(ValidatorStrategy):
    """Baseline 2: 30-minute Rolling Window Simple Moving Average."""

    @property
    def method_id(self) -> str:
        return "bench_sma_30m"

    @property
    def method_name(self) -> str:
        return "30-Minute SMA Baseline"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return ["spot_feed_30m_window"]

    @property
    def assumptions(self) -> List[str]:
        return ["Short-term equilibrium is approximated by a 30-minute uniform rolling mean."]

    @property
    def limitations(self) -> List[str]:
        return ["Lags during rapid price breakouts; equally weights stale and recent ticks."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        window = context.get_input_window()
        cutoff = context.current_ts - 1800  # 30m window
        recent = [obs.price for obs in context.history if obs.timestamp >= cutoff]

        if recent:
            estimate = float(np.mean(recent))
            std = float(np.std(recent)) if len(recent) > 1 else estimate * 0.01
        else:
            latest = context.latest_observation
            estimate = latest.price if latest else 100.0
            std = estimate * 0.015

        lower = round(estimate - 1.96 * max(std, 0.05), 4)
        upper = round(estimate + 1.96 * max(std, 0.05), 4)

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=round(estimate, 4),
            lower_bound=lower,
            upper_bound=upper,
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=window,
            status="SIMULATED",
            metadata={"window_seconds": 1800, "samples": len(recent)}
        )


class ExponentialMovingAverageStrategy(ValidatorStrategy):
    """Baseline 3: Exponentially Weighted Moving Average (EWMA, alpha=0.15)."""

    def __init__(self, alpha: float = 0.15):
        self.alpha = alpha

    @property
    def method_id(self) -> str:
        return f"bench_ewma_a{int(self.alpha * 100)}"

    @property
    def method_name(self) -> str:
        return f"EWMA Filter (alpha={self.alpha}) Baseline"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return ["spot_feed_ewma_stream"]

    @property
    def assumptions(self) -> List[str]:
        return ["More recent ticks contain higher information content decayed exponentially."]

    @property
    def limitations(self) -> List[str]:
        return ["Fixed smoothing factor may overfit calm regimes and underfit sudden regime jumps."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        window = context.get_input_window()
        if not context.history:
            estimate = 100.0
            std = 1.0
        else:
            prices = [obs.price for obs in context.history]
            # Compute EWMA
            ewma = prices[0]
            for p in prices[1:]:
                ewma = self.alpha * p + (1.0 - self.alpha) * ewma
            estimate = ewma
            std = float(np.std(prices[-30:])) if len(prices) >= 30 else float(np.std(prices))

        lower = round(estimate - 1.96 * max(std, 0.05), 4)
        upper = round(estimate + 1.96 * max(std, 0.05), 4)

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=round(estimate, 4),
            lower_bound=lower,
            upper_bound=upper,
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=window,
            status="SIMULATED",
            metadata={"alpha": self.alpha}
        )
