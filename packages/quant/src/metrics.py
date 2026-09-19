"""
Standardized Evaluation Metrics Engine.
Computes MAE, RMSE, directional accuracy, MPE, MAPE, and interval coverage.
Rule #4: Do not invent statistical meaning for these metrics.
"""

from typing import List, Optional
import numpy as np
from .models import PredictionErrorRecord, EvaluationMetrics


def calculate_metrics(records: List[PredictionErrorRecord]) -> EvaluationMetrics:
    """
    Computes mathematical summary metrics across a sequence of rolling prediction errors.
    Returns EvaluationMetrics with 0.0 values if records list is empty.
    """
    if not records:
        return EvaluationMetrics(
            mae=0.0,
            rmse=0.0,
            directional_accuracy=0.0,
            mean_percentage_error=0.0,
            mean_absolute_percentage_error=0.0,
            prediction_interval_coverage=None,
            sample_count=0
        )

    errors = np.array([r.error for r in records], dtype=float)
    abs_errors = np.array([r.abs_error for r in records], dtype=float)
    pct_errors = np.array([r.pct_error for r in records], dtype=float)
    abs_pct_errors = np.array([r.abs_pct_error for r in records], dtype=float)

    # 1. MAE
    mae = float(np.mean(abs_errors))

    # 2. RMSE
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # 3. Directional Accuracy (on moves where actual move was non-zero)
    dir_records = [r for r in records if r.direction_actual != 0]
    if dir_records:
        dir_correct = sum(1 for r in dir_records if r.direction_correct)
        directional_acc = float(dir_correct / len(dir_records))
    else:
        # If actual price never moved, directional accuracy defaults to 1.0 if predicted no move, else 0.0
        no_move_correct = sum(1 for r in records if r.direction_pred == 0)
        directional_acc = float(no_move_correct / len(records))

    # 4. Mean Percentage Error (MPE) & MAPE
    mpe = float(np.mean(pct_errors))
    mape = float(np.mean(abs_pct_errors))

    # 5. Prediction Interval Coverage (if bounds exist)
    interval_records = [r for r in records if r.interval_covered is not None]
    if interval_records:
        covered_count = sum(1 for r in interval_records if r.interval_covered is True)
        coverage = float(covered_count / len(interval_records))
    else:
        coverage = None

    return EvaluationMetrics(
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        directional_accuracy=round(directional_acc, 4),
        mean_percentage_error=round(mpe, 4),
        mean_absolute_percentage_error=round(mape, 4),
        prediction_interval_coverage=round(coverage, 4) if coverage is not None else None,
        sample_count=len(records)
    )
