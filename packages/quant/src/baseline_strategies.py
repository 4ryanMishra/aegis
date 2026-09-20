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

        # Estimate empirical variance from trailing window (up to 60 observations)
        if len(context.history) >= 5:
            recent_slice = context.history[-60:]
            prices = [obs.price for obs in recent_slice]
            std = float(np.std(prices))
        else:
            std = curr_price * 0.015

        lower = round(curr_price - 1.96 * std, 4)
        upper = round(curr_price + 1.96 * std, 4)

        status_val = latest.status if latest else "HISTORICAL"

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
            status=status_val,
            metadata={"baseline_type": "MARTINGALE_PERSISTENCE"}
        )


class SimpleMovingAverageStrategy(ValidatorStrategy):
    """Baseline 2: Rolling Window Simple Moving Average."""

    def __init__(self, window_seconds: int = 1800):
        self.window_seconds = window_seconds

    @property
    def method_id(self) -> str:
        return f"bench_sma_{self.window_seconds // 60}m"

    @property
    def method_name(self) -> str:
        return f"{self.window_seconds // 60}-Minute SMA Baseline"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return [f"spot_feed_{self.window_seconds // 60}m_window"]

    @property
    def assumptions(self) -> List[str]:
        return [f"Short-term equilibrium is approximated by a {self.window_seconds // 60}-minute uniform rolling mean."]

    @property
    def limitations(self) -> List[str]:
        return ["Lags during rapid price breakouts; equally weights stale and recent ticks."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        window = context.get_input_window()
        cutoff = context.current_ts - self.window_seconds
        recent = []
        for obs in reversed(context.history):
            if obs.timestamp >= cutoff:
                recent.append(obs.price)
            else:
                break

        if recent:
            estimate = float(np.mean(recent))
            std = float(np.std(recent)) if len(recent) > 1 else estimate * 0.01
        else:
            latest = context.latest_observation
            estimate = latest.price if latest else 100.0
            std = estimate * 0.015

        lower = round(estimate - 1.96 * max(std, 0.05), 4)
        upper = round(estimate + 1.96 * max(std, 0.05), 4)

        status_val = context.latest_observation.status if context.latest_observation else "HISTORICAL"

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
            status=status_val,
            metadata={"window_seconds": self.window_seconds, "samples": len(recent)}
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
            # Trailing 180 points capture > 99.9999999% of EWMA weight ((1-0.15)^180 < 1e-12)
            recent_obs = context.history[-180:]
            prices = [obs.price for obs in recent_obs]
            ewma = prices[0]
            for p in prices[1:]:
                ewma = self.alpha * p + (1.0 - self.alpha) * ewma
            estimate = ewma
            std = float(np.std(prices[-30:])) if len(prices) >= 30 else float(np.std(prices))

        lower = round(estimate - 1.96 * max(std, 0.05), 4)
        upper = round(estimate + 1.96 * max(std, 0.05), 4)

        status_val = context.latest_observation.status if context.latest_observation else "HISTORICAL"

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
            status=status_val,
            metadata={"alpha": self.alpha}
        )


class KalmanLaneStrategy(ValidatorStrategy):
    """Methodology Lane 1: Recursive 1D Kalman Filter + Mahalanobis Innovation Gating."""

    @property
    def method_id(self) -> str:
        return "lane1_kalman_1d"

    @property
    def method_name(self) -> str:
        return "Recursive 1D Kalman (Lane 1)"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return ["spot_ticks_kalman_stream"]

    @property
    def assumptions(self) -> List[str]:
        return ["State transitions follow random-walk baseline; innovations are Gaussian under unperturbed regimes."]

    @property
    def limitations(self) -> List[str]:
        return ["Outliers gated by Mahalanobis distance; persistent structural shifts may lag until covariance inflates."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        from ..methodologies.kalman import KalmanFilter1D
        window = context.get_input_window()
        kf = KalmanFilter1D(default_q=0.25, default_r=1.0)
        
        if not context.history:
            est, low, up = 100.0, 98.0, 102.0
            status_val = "SIMULATED"
        else:
            recent = context.history[-30:]
            prices = [obs.price for obs in recent]
            prior = prices[0]
            p_cov = 1.0
            res = None
            for p in prices:
                res = kf.step(observation=p, prior_state=prior, prior_covariance=p_cov)
                prior = res.posterior_state
                p_cov = res.posterior_covariance
            
            est = res.posterior_state if res else prices[-1]
            low = res.uncertainty_lower if res else est * 0.98
            up = res.uncertainty_upper if res else est * 1.02
            status_val = context.latest_observation.status if context.latest_observation else "HISTORICAL"

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=round(est, 4),
            lower_bound=round(low, 4),
            upper_bound=round(up, 4),
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=window,
            status=status_val,
            metadata={"lane_id": 1, "methodology": "KALMAN_1D"}
        )


class HuberLaneStrategy(ValidatorStrategy):
    """Methodology Lane 2: Huber M-Estimation via IRLS."""

    @property
    def method_id(self) -> str:
        return "lane2_huber_irls"

    @property
    def method_name(self) -> str:
        return "Huber M-Estimation IRLS (Lane 2)"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return ["spot_ticks_rolling_window"]

    @property
    def assumptions(self) -> List[str]:
        return ["Observations follow central Gaussian core with potential heavy-tailed contamination."]

    @property
    def limitations(self) -> List[str]:
        return ["Bounds outlier influence linearly; does not eliminate large cluster collusion."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        from ..methodologies.huber import HuberMEstimator
        window = context.get_input_window()
        estimator = HuberMEstimator(k=1.345)

        if not context.history:
            est, low, up = 100.0, 98.0, 102.0
            status_val = "SIMULATED"
        else:
            recent = context.history[-30:]
            prices = [obs.price for obs in recent]
            res = estimator.estimate(prices)
            est = res.final_estimate
            low = res.uncertainty_lower
            up = res.uncertainty_upper
            status_val = context.latest_observation.status if context.latest_observation else "HISTORICAL"

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=round(est, 4),
            lower_bound=round(low, 4),
            upper_bound=round(up, 4),
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=window,
            status=status_val,
            metadata={"lane_id": 2, "methodology": "HUBER_IRLS"}
        )


class JSDLaneStrategy(ValidatorStrategy):
    """Methodology Lane 3: Pairwise Jensen-Shannon Divergence on Uncertainty Distributions."""

    @property
    def method_id(self) -> str:
        return "lane3_jsd"

    @property
    def method_name(self) -> str:
        return "Pairwise JSD Consensus (Lane 3)"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return ["multi_source_uncertainty_distributions"]

    @property
    def assumptions(self) -> List[str]:
        return ["Informational agreement is reflected by low symmetric JSD across discrete probability profiles."]

    @property
    def limitations(self) -> List[str]:
        return ["Sensitive to grid resolution and tails of discrete distributions."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        from ..methodologies.jsd import JensenShannonDivergence, JSDLaneInput
        window = context.get_input_window()
        jsd = JensenShannonDivergence(grid_bins=100)

        if not context.history:
            est, low, up = 100.0, 98.0, 102.0
            status_val = "SIMULATED"
        else:
            recent = context.history[-30:]
            prices = [obs.price for obs in recent]
            mean_p = float(np.mean(prices))
            std_p = max(float(np.std(prices)), 0.05)
            # Create synthetic uncertainty partitions (short, medium, long window)
            inputs = [
                JSDLaneInput(lane_id="sub_10", estimate=float(np.mean(prices[-10:])), lower_bound=float(np.mean(prices[-10:])) - 1.96 * std_p, upper_bound=float(np.mean(prices[-10:])) + 1.96 * std_p),
                JSDLaneInput(lane_id="sub_20", estimate=float(np.mean(prices[-20:])), lower_bound=float(np.mean(prices[-20:])) - 1.96 * std_p, upper_bound=float(np.mean(prices[-20:])) + 1.96 * std_p),
                JSDLaneInput(lane_id="sub_30", estimate=mean_p, lower_bound=mean_p - 1.96 * std_p, upper_bound=mean_p + 1.96 * std_p),
            ]
            res = jsd.evaluate(inputs)
            est = res.consensus_price
            low = res.uncertainty_lower
            up = res.uncertainty_upper
            status_val = context.latest_observation.status if context.latest_observation else "HISTORICAL"

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=round(est, 4),
            lower_bound=round(low, 4),
            upper_bound=round(up, 4),
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=window,
            status=status_val,
            metadata={"lane_id": 3, "methodology": "JSD"}
        )


class OULaneStrategy(ValidatorStrategy):
    """Methodology Lane 4: Ornstein-Uhlenbeck RWA Residual Analysis."""

    @property
    def method_id(self) -> str:
        return "lane4_ou_residual"

    @property
    def method_name(self) -> str:
        return "Ornstein-Uhlenbeck Residual (Lane 4)"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return ["rwa_redemption_spread_stream"]

    @property
    def assumptions(self) -> List[str]:
        return ["Log-spread relative to anchor follows continuous-time mean-reverting diffusion."]

    @property
    def limitations(self) -> List[str]:
        return ["Requires defensible reference anchor; returns NOT_APPLICABLE if anchor missing."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        from ..methodologies.ou import OrnsteinUhlenbeckAnalyzer
        window = context.get_input_window()
        ou = OrnsteinUhlenbeckAnalyzer(theta=0.5, mu=0.0, sigma=0.02)

        if not context.history:
            est, low, up = 100.0, 98.0, 102.0
            status_val = "SIMULATED"
        else:
            latest = context.latest_observation.price if context.latest_observation else 100.0
            anchor = float(np.mean([obs.price for obs in context.history[-60:]])) if len(context.history) >= 5 else latest
            res = ou.evaluate(spot_price=latest, anchor_price=anchor, is_rwa=True)
            est = res.estimated_price
            low = res.uncertainty_lower
            up = res.uncertainty_upper
            status_val = context.latest_observation.status if context.latest_observation else "HISTORICAL"

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=round(est, 4),
            lower_bound=round(low, 4),
            upper_bound=round(up, 4),
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=window,
            status=status_val,
            metadata={"lane_id": 4, "methodology": "OU_RESIDUAL"}
        )


class CUSUMLaneStrategy(ValidatorStrategy):
    """Methodology Lane 5: Page CUSUM Sequential Drift Detection."""

    @property
    def method_id(self) -> str:
        return "lane5_cusum_drift"

    @property
    def method_name(self) -> str:
        return "Page CUSUM Drift (Lane 5)"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> List[str]:
        return ["continuous_drift_accumulator"]

    @property
    def assumptions(self) -> List[str]:
        return ["Standardized deviations accumulate sequentially; trips upon persistent directional change."]

    @property
    def limitations(self) -> List[str]:
        return ["Requires calibrated baseline reference and variance; does not eliminate manipulation."]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        from ..methodologies.cusum import PageCUSUM
        window = context.get_input_window()
        cusum = PageCUSUM(kappa=0.5, threshold_h=4.0)

        if not context.history:
            est, low, up = 100.0, 98.0, 102.0
            status_val = "SIMULATED"
        else:
            recent = context.history[-20:]
            prices = [obs.price for obs in recent]
            base_p = prices[0]
            base_vol = max(float(np.std(prices)), 0.05)
            res = cusum.evaluate_series(prices=prices, baseline_price=base_p, baseline_volatility=base_vol)
            est = res.estimated_price
            low = res.uncertainty_lower
            up = res.uncertainty_upper
            status_val = context.latest_observation.status if context.latest_observation else "HISTORICAL"

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=round(est, 4),
            lower_bound=round(low, 4),
            upper_bound=round(up, 4),
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=window,
            status=status_val,
            metadata={"lane_id": 5, "methodology": "CUSUM"}
        )

