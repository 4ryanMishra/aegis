"""
Rolling Backtesting Engine for 1-Hour-Ahead Forecasts.
Enforces strict anti-leakage boundaries and produces verified MethodologyResults.
"""

from typing import List, Optional, Dict, Any
from .models import (
    PredictionErrorRecord,
    MethodologyResult,
    EvaluationMetrics,
)
from .strategy_base import ValidatorStrategy, InputContext
from .dataset import HistoricalReplayDataset
from .metrics import calculate_metrics


class RollingBacktestEngine:
    """
    Executes a rolling out-of-sample backtest of a ValidatorStrategy across a HistoricalReplayDataset.
    Evaluates predictions strictly at horizon t + horizon_seconds.
    """

    def __init__(
        self,
        horizon_seconds: int = 3600,      # Fixed 1-hour verification horizon
        rolling_step_seconds: int = 900,   # Step every 15 minutes
        warmup_seconds: int = 3600,        # Minimum historical warmup window
        tolerance_sec: int = 180           # Matching tolerance for realized observation
    ):
        self.horizon_seconds = horizon_seconds
        self.rolling_step_seconds = rolling_step_seconds
        self.warmup_seconds = warmup_seconds
        self.tolerance_sec = tolerance_sec

    def run(
        self,
        strategy: ValidatorStrategy,
        dataset: HistoricalReplayDataset,
        validator_id: str = "val_benchmark_node"
    ) -> MethodologyResult:
        if len(dataset) == 0:
            return MethodologyResult(
                methodology_id=strategy.method_id,
                methodology_name=strategy.method_name,
                method_version=strategy.version,
                dataset_name=dataset.name,
                dataset_id=dataset.dataset_id,
                dataset_status=dataset.status,
                source=dataset.source,
                horizon_seconds=self.horizon_seconds,
                sampling_interval_seconds=dataset.sampling_interval_seconds,
                evaluation_period={"error": "EMPTY_DATASET", "sample_count": 0},
                metrics=calculate_metrics([]),
                assumptions=strategy.assumptions,
                limitations=strategy.limitations,
                status=dataset.status
            )

        start_ts = dataset.start_ts + self.warmup_seconds
        end_ts = dataset.end_ts - self.horizon_seconds

        if start_ts >= end_ts:
            return MethodologyResult(
                methodology_id=strategy.method_id,
                methodology_name=strategy.method_name,
                method_version=strategy.version,
                dataset_name=dataset.name,
                dataset_id=dataset.dataset_id,
                dataset_status=dataset.status,
                source=dataset.source,
                horizon_seconds=self.horizon_seconds,
                sampling_interval_seconds=dataset.sampling_interval_seconds,
                evaluation_period={"error": "INSUFFICIENT_HISTORY", "sample_count": 0},
                metrics=calculate_metrics([]),
                assumptions=strategy.assumptions,
                limitations=strategy.limitations,
                status=dataset.status
            )

        records: List[PredictionErrorRecord] = []
        current_t = start_ts

        while current_t <= end_ts:
            # 1. Anti-Leakage Query: Fetch strictly observations up to current_t
            history = dataset.get_observations_up_to(current_t)

            # Assert strictly no future observation leaked into input
            if history:
                assert history[-1].timestamp <= current_t, (
                    f"CRITICAL LEAKAGE: observation timestamp {history[-1].timestamp} > current_t {current_t}"
                )

            # 2. Construct InputContext
            context = InputContext.model_construct(
                validator_id=validator_id,
                current_ts=current_t,
                target_horizon_seconds=self.horizon_seconds,
                history=history,
                seed=42,
                metadata={}
            )

            # 3. Strategy Prediction
            prediction = strategy.predict(context)

            # Assert target horizon correctness
            target_ts = current_t + self.horizon_seconds
            assert prediction.target_timestamp == target_ts, (
                f"Horizon mismatch: predicted {prediction.target_timestamp} != target {target_ts}"
            )

            # 4. Fetch Realized Future Value at target_ts
            realized_obs = dataset.get_observation_at(target_ts, tolerance_sec=self.tolerance_sec)

            if realized_obs is not None and history:
                y = realized_obs.price
                y_hat = prediction.point_estimate
                y_curr = history[-1].price

                err = y - y_hat
                abs_err = abs(err)
                pct_err = (err / max(abs(y), 1e-6)) * 100.0
                abs_pct_err = abs(pct_err)

                # Directional check: did price go up, down, or flat from y_curr to y?
                dir_actual = 1 if y > y_curr else (-1 if y < y_curr else 0)
                dir_pred = 1 if y_hat > y_curr else (-1 if y_hat < y_curr else 0)
                dir_correct = (dir_actual == dir_pred)

                # Interval coverage check
                if prediction.lower_bound is not None and prediction.upper_bound is not None:
                    covered = (prediction.lower_bound <= y <= prediction.upper_bound)
                else:
                    covered = None

                records.append(
                    PredictionErrorRecord(
                        t_pred=current_t,
                        t_target=target_ts,
                        point_estimate=round(y_hat, 4),
                        lower_bound=round(prediction.lower_bound, 4) if prediction.lower_bound is not None else None,
                        upper_bound=round(prediction.upper_bound, 4) if prediction.upper_bound is not None else None,
                        realized_value=round(y, 4),
                        error=round(err, 4),
                        abs_error=round(abs_err, 4),
                        pct_error=round(pct_err, 4),
                        abs_pct_error=round(abs_pct_err, 4),
                        direction_actual=dir_actual,
                        direction_pred=dir_pred,
                        direction_correct=dir_correct,
                        interval_covered=covered
                    )
                )

            current_t += self.rolling_step_seconds

        metrics = calculate_metrics(records)

        return MethodologyResult(
            methodology_id=strategy.method_id,
            methodology_name=strategy.method_name,
            method_version=strategy.version,
            dataset_name=dataset.name,
            dataset_id=dataset.dataset_id,
            dataset_status=dataset.status,
            source=dataset.source,
            horizon_seconds=self.horizon_seconds,
            sampling_interval_seconds=dataset.sampling_interval_seconds,
            evaluation_period={
                "start_ts": start_ts,
                "end_ts": end_ts,
                "horizon_seconds": self.horizon_seconds,
                "rolling_step_seconds": self.rolling_step_seconds,
                "sample_count": len(records)
            },
            metrics=metrics,
            assumptions=strategy.assumptions,
            limitations=strategy.limitations,
            status=dataset.status
        )
