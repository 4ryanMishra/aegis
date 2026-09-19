"""
AEGIS Quant & Benchmarking Module.
Provides historical replay, anti-leakage rolling backtesting, evaluation metrics,
and multi-strategy comparison infrastructure for P_DEC validator methodologies.
"""

from .models import (
    TimestampedObservation,
    InputWindow,
    ValidatorPrediction,
    EvaluationMetrics,
    MethodologyResult,
    BenchmarkComparison,
)
from .strategy_base import ValidatorStrategy, InputContext
from .dataset import HistoricalReplayDataset, generate_synthetic_rwa_series
from .metrics import calculate_metrics
from .backtest import RollingBacktestEngine
from .benchmark import ValidatorBenchmarkRunner

__all__ = [
    "TimestampedObservation",
    "InputWindow",
    "ValidatorPrediction",
    "EvaluationMetrics",
    "MethodologyResult",
    "BenchmarkComparison",
    "ValidatorStrategy",
    "InputContext",
    "HistoricalReplayDataset",
    "generate_synthetic_rwa_series",
    "calculate_metrics",
    "RollingBacktestEngine",
    "ValidatorBenchmarkRunner",
]
