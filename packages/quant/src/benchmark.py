"""
Multi-Validator Methodology Benchmark Runner.
Executes standardized comparative evaluations across candidate strategies on identical datasets.
"""

from typing import List, Dict, Any, Optional
import time
from .strategy_base import ValidatorStrategy
from .dataset import HistoricalReplayDataset
from .backtest import RollingBacktestEngine
from .models import MethodologyResult, BenchmarkComparison


class ValidatorBenchmarkRunner:
    """
    Orchestrates comparative benchmarking across multiple validator methodologies.
    Guarantees that all candidate strategies are evaluated on the identical historical split.
    """

    def __init__(
        self,
        horizon_seconds: int = 3600,
        rolling_step_seconds: int = 900,
        warmup_seconds: int = 3600
    ):
        self.engine = RollingBacktestEngine(
            horizon_seconds=horizon_seconds,
            rolling_step_seconds=rolling_step_seconds,
            warmup_seconds=warmup_seconds
        )
        self.horizon_seconds = horizon_seconds

    def run_benchmark(
        self,
        strategies: List[ValidatorStrategy],
        dataset: HistoricalReplayDataset,
        benchmark_id: Optional[str] = None
    ) -> BenchmarkComparison:
        b_id = benchmark_id or f"bench_{dataset.name}_{int(time.time())}"
        results: List[MethodologyResult] = []

        for strat in strategies:
            res = self.engine.run(strategy=strat, dataset=dataset)
            results.append(res)

        # Rank strategies by lowest MAE
        ranked = sorted(results, key=lambda r: r.metrics.mae)
        ranked_ids = [r.methodology_id for r in ranked]

        return BenchmarkComparison(
            benchmark_id=b_id,
            dataset_name=dataset.name,
            horizon_seconds=self.horizon_seconds,
            timestamp=int(time.time()),
            results=results,
            ranked_by_mae=ranked_ids,
            status=dataset.status
        )

    @staticmethod
    def format_markdown_table(comparison: BenchmarkComparison) -> str:
        """Formats side-by-side comparison into a clean Markdown table."""
        header = (
            f"### Benchmark Comparison: {comparison.benchmark_id} [Status: {comparison.status}]\n"
            f"**Dataset**: `{comparison.dataset_name}` | **Horizon**: `{comparison.horizon_seconds // 60}m`\n\n"
            "| Methodology | Version | MAE ($) | RMSE ($) | Dir. Acc (%) | MAPE (%) | Interval Coverage | Rank (MAE) |\n"
            "|---|---|---|---|---|---|---|---|\n"
        )
        rows = []
        ranked_order = {m_id: idx + 1 for idx, m_id in enumerate(comparison.ranked_by_mae)}

        for r in comparison.results:
            cov_str = f"{(r.metrics.prediction_interval_coverage * 100):.1f}%" if r.metrics.prediction_interval_coverage is not None else "N/A"
            dir_str = f"{(r.metrics.directional_accuracy * 100):.1f}%"
            rank = ranked_order.get(r.methodology_id, "-")
            row = (
                f"| {r.methodology_name} (`{r.methodology_id}`) | "
                f"v{r.method_version} | "
                f"${r.metrics.mae:.4f} | "
                f"${r.metrics.rmse:.4f} | "
                f"{dir_str} | "
                f"{r.metrics.mean_absolute_percentage_error:.2f}% | "
                f"{cov_str} | "
                f"#{rank} |"
            )
            rows.append(row)

        return header + "\n".join(rows) + "\n"
