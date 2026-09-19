"""
Comprehensive test suite for Phase 2A Validator Benchmarking Foundation.
Tests:
- No future-data leakage
- Rolling one-hour horizon enforcement
- Metric calculation accuracy (hand-verified test vectors)
- Deterministic replay reproducibility
- Empty and insufficient history edge-cases
- Validator output schema completeness (all 10 fields)
"""

import pytest
import numpy as np
from packages.quant.src.models import (
    TimestampedObservation,
    PredictionErrorRecord,
    EvaluationMetrics,
    ValidatorPrediction,
)
from packages.quant.src.strategy_base import ValidatorStrategy, InputContext
from packages.quant.src.dataset import (
    HistoricalReplayDataset,
    generate_synthetic_rwa_series,
)
from packages.quant.src.metrics import calculate_metrics
from packages.quant.src.backtest import RollingBacktestEngine
from packages.quant.src.baseline_strategies import (
    NaivePersistenceStrategy,
    SimpleMovingAverageStrategy,
    ExponentialMovingAverageStrategy,
)
from packages.quant.src.benchmark import ValidatorBenchmarkRunner


# --- Test Strategy that records input window timestamps ---
class LeakageProbeStrategy(ValidatorStrategy):
    """Probe strategy that records the maximum timestamp it ever sees."""
    def __init__(self):
        self.max_seen_timestamp = -1
        self.call_contexts = []

    @property
    def method_id(self) -> str:
        return "probe_leakage"

    @property
    def method_name(self) -> str:
        return "Leakage Probe Strategy"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> list:
        return ["probe_feed"]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        for obs in context.history:
            if obs.timestamp > context.current_ts:
                raise AssertionError(
                    f"FUTURE LEAKAGE DETECTED: Observation timestamp {obs.timestamp} > current_ts {context.current_ts}"
                )
            if obs.timestamp > self.max_seen_timestamp:
                self.max_seen_timestamp = obs.timestamp

        self.call_contexts.append((context.current_ts, context.target_ts))
        latest = context.latest_observation
        p = latest.price if latest else 100.0

        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=p,
            lower_bound=p - 1.0,
            upper_bound=p + 1.0,
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=context.get_input_window(),
            status="SIMULATED"
        )


def test_no_future_data_leakage():
    """Verify that under rolling backtest, strategy NEVER receives observations with timestamp > current_ts."""
    dataset = generate_synthetic_rwa_series(
        duration_seconds=7200,  # 2 hours
        step_seconds=60,
        seed=123
    )
    probe = LeakageProbeStrategy()
    engine = RollingBacktestEngine(
        horizon_seconds=1800,
        rolling_step_seconds=600,
        warmup_seconds=1800
    )

    result = engine.run(probe, dataset)
    assert result.metrics.sample_count > 0

    for current_t, target_t in probe.call_contexts:
        # Every call must have target strictly in the future and input strictly <= current_t
        assert target_t == current_t + 1800
        # Check dataset query directly
        sub_history = dataset.get_observations_up_to(current_t)
        assert all(obs.timestamp <= current_t for obs in sub_history)


def test_rolling_one_hour_horizon():
    """Verify that predictions are generated strictly for horizon t + 3600."""
    dataset = generate_synthetic_rwa_series(
        duration_seconds=14400,  # 4 hours
        step_seconds=60,
        seed=42
    )
    strat = NaivePersistenceStrategy()
    engine = RollingBacktestEngine(
        horizon_seconds=3600,
        rolling_step_seconds=1800,
        warmup_seconds=3600
    )
    res = engine.run(strat, dataset)

    assert res.evaluation_period["horizon_seconds"] == 3600
    assert res.metrics.sample_count > 0


def test_metric_calculations_hand_verified():
    """Verify metric calculations against known hand-calculated values."""
    # Construct 4 synthetic records:
    # 1. actual=100, pred=98 (error = +2, abs=2, pct=2%)
    # 2. actual=105, pred=105 (error = 0, abs=0, pct=0%)
    # 3. actual=90, pred=94 (error = -4, abs=4, pct=-4.4444%)
    # 4. actual=95, pred=93 (error = +2, abs=2, pct=2.1053%)
    records = [
        PredictionErrorRecord(
            t_pred=1000, t_target=4600,
            point_estimate=98.0, lower_bound=95.0, upper_bound=102.0, realized_value=100.0,
            error=2.0, abs_error=2.0, pct_error=2.0, abs_pct_error=2.0,
            direction_actual=1, direction_pred=1, direction_correct=True, interval_covered=True
        ),
        PredictionErrorRecord(
            t_pred=1600, t_target=5200,
            point_estimate=105.0, lower_bound=100.0, upper_bound=108.0, realized_value=105.0,
            error=0.0, abs_error=0.0, pct_error=0.0, abs_pct_error=0.0,
            direction_actual=1, direction_pred=1, direction_correct=True, interval_covered=True
        ),
        PredictionErrorRecord(
            t_pred=2200, t_target=5800,
            point_estimate=94.0, lower_bound=92.0, upper_bound=96.0, realized_value=90.0,
            error=-4.0, abs_error=4.0, pct_error=-4.4444, abs_pct_error=4.4444,
            direction_actual=-1, direction_pred=1, direction_correct=False, interval_covered=False
        ),
        PredictionErrorRecord(
            t_pred=2800, t_target=6400,
            point_estimate=93.0, lower_bound=91.0, upper_bound=96.0, realized_value=95.0,
            error=2.0, abs_error=2.0, pct_error=2.1053, abs_pct_error=2.1053,
            direction_actual=1, direction_pred=1, direction_correct=True, interval_covered=True
        ),
    ]

    metrics = calculate_metrics(records)

    # MAE = (2 + 0 + 4 + 2) / 4 = 8 / 4 = 2.0
    assert metrics.mae == 2.0

    # RMSE = sqrt((4 + 0 + 16 + 4) / 4) = sqrt(24 / 4) = sqrt(6) ≈ 2.4495
    assert metrics.rmse == pytest.approx(np.sqrt(6.0), abs=1e-3)

    # Directional accuracy: 3 correct out of 4 = 75%
    assert metrics.directional_accuracy == 0.75

    # Coverage: 3 covered out of 4 = 75%
    assert metrics.prediction_interval_coverage == 0.75

    # MAPE = (2.0 + 0.0 + 4.4444 + 2.1053) / 4 = 8.5497 / 4 ≈ 2.1374%
    assert metrics.mean_absolute_percentage_error == pytest.approx(2.1374, abs=1e-3)


def test_deterministic_replay_reproducibility():
    """Ensure running backtest twice with same seed produces bit-for-bit identical results."""
    ds1 = generate_synthetic_rwa_series(seed=777)
    ds2 = generate_synthetic_rwa_series(seed=777)

    strat1 = ExponentialMovingAverageStrategy(alpha=0.15)
    strat2 = ExponentialMovingAverageStrategy(alpha=0.15)

    engine1 = RollingBacktestEngine(horizon_seconds=3600, rolling_step_seconds=1800, warmup_seconds=3600)
    engine2 = RollingBacktestEngine(horizon_seconds=3600, rolling_step_seconds=1800, warmup_seconds=3600)

    res1 = engine1.run(strat1, ds1)
    res2 = engine2.run(strat2, ds2)

    assert res1.metrics.mae == res2.metrics.mae
    assert res1.metrics.rmse == res2.metrics.rmse
    assert res1.metrics.directional_accuracy == res2.metrics.directional_accuracy
    assert res1.metrics.sample_count == res2.metrics.sample_count


def test_empty_and_insufficient_history():
    """Verify graceful handling when dataset is empty or shorter than warmup."""
    empty_dataset = HistoricalReplayDataset(name="empty", observations=[])
    strat = NaivePersistenceStrategy()
    engine = RollingBacktestEngine(horizon_seconds=3600, warmup_seconds=3600)

    res_empty = engine.run(strat, empty_dataset)
    assert res_empty.metrics.sample_count == 0
    assert res_empty.evaluation_period.get("error") == "EMPTY_DATASET"

    # Short dataset (only 10 minutes, but warmup requires 60 minutes)
    short_dataset = generate_synthetic_rwa_series(duration_seconds=600, step_seconds=60)
    res_short = engine.run(strat, short_dataset)
    assert res_short.metrics.sample_count == 0
    assert res_short.evaluation_period.get("error") == "INSUFFICIENT_HISTORY"


def test_validator_output_schema_completeness():
    """Asserts that ValidatorPrediction and ValidatorObservation satisfy all 10 required fields."""
    dataset = generate_synthetic_rwa_series(duration_seconds=3600, step_seconds=60)
    context = InputContext(
        validator_id="val_test_node",
        current_ts=1774001800,
        target_horizon_seconds=3600,
        history=dataset.get_observations_up_to(1774001800)
    )

    strat = SimpleMovingAverageStrategy()
    pred = strat.predict(context)

    # 1. validator_id
    assert hasattr(pred, "validator_id") and isinstance(pred.validator_id, str)
    # 2. method_id
    assert hasattr(pred, "method_id") and isinstance(pred.method_id, str)
    # 3. method_version
    assert hasattr(pred, "method_version") and isinstance(pred.method_version, str)
    # 4. point_estimate
    assert hasattr(pred, "point_estimate") and isinstance(pred.point_estimate, float)
    # 5. lower_bound
    assert hasattr(pred, "lower_bound") and (pred.lower_bound is None or isinstance(pred.lower_bound, float))
    # 6. upper_bound
    assert hasattr(pred, "upper_bound") and (pred.upper_bound is None or isinstance(pred.upper_bound, float))
    # 7. timestamp
    assert hasattr(pred, "timestamp") and isinstance(pred.timestamp, int)
    # 8. source_provenance
    assert hasattr(pred, "source_provenance") and isinstance(pred.source_provenance, list)
    # 9. input_window
    assert hasattr(pred, "input_window") and pred.input_window is not None
    # 10. status
    assert hasattr(pred, "status") and pred.status == "SIMULATED"


def test_multi_strategy_benchmark_runner():
    """Verify side-by-side benchmark comparison execution and markdown table generation."""
    dataset = generate_synthetic_rwa_series(
        dataset_name="rwa_gold_benchmark_sample",
        duration_seconds=28800,  # 8 hours
        step_seconds=120,
        seed=101
    )

    strategies = [
        NaivePersistenceStrategy(),
        SimpleMovingAverageStrategy(),
        ExponentialMovingAverageStrategy(alpha=0.10),
        ExponentialMovingAverageStrategy(alpha=0.25),
    ]

    runner = ValidatorBenchmarkRunner(
        horizon_seconds=3600,
        rolling_step_seconds=1800,
        warmup_seconds=3600
    )

    comparison = runner.run_benchmark(strategies=strategies, dataset=dataset)

    assert len(comparison.results) == 4
    assert len(comparison.ranked_by_mae) == 4
    # Lowest MAE is ranked #1
    assert comparison.ranked_by_mae[0] == min(comparison.results, key=lambda r: r.metrics.mae).methodology_id

    md_table = ValidatorBenchmarkRunner.format_markdown_table(comparison)
    assert "Benchmark Comparison" in md_table
    assert "Naive Persistence Baseline" in md_table
    assert "MAE ($)" in md_table
