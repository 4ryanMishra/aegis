"""
Domain data structures for validator predictions, rolling evaluation, and benchmark results.
Conforms strictly to Phase 2A requirements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TimestampedObservation(BaseModel):
    """An individual historical or simulated market observation."""
    timestamp: int = Field(..., description="Observation Unix timestamp in seconds")
    price: float = Field(..., description="Observed market price")
    volume: Optional[float] = Field(default=None, description="Observed volume if available")
    source_id: str = Field(default="simulated_market_feed", description="Source feed identifier")
    status: str = Field(default="SIMULATED", description="Data integrity status: SIMULATED / OBSERVED")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InputWindow(BaseModel):
    """Metadata describing the historical observation window fed into the prediction."""
    start_ts: int = Field(..., description="Oldest timestamp included in input")
    end_ts: int = Field(..., description="Most recent timestamp included in input (strictly <= t_pred)")
    observation_count: int = Field(..., description="Number of historical ticks in window")
    sampling_interval_sec: int = Field(default=60, description="Step frequency in seconds")


class ValidatorPrediction(BaseModel):
    """
    Standardized prediction output from an independent validator methodology.
    Meets Requirement 1 with full backward-compatibility property aliases.
    """
    validator_id: str = Field(..., description="Identifier of the validator node")
    method_id: str = Field(..., description="Unique methodology identifier")
    method_version: str = Field(default="0.1.0", description="Methodology version or code hash")
    point_estimate: float = Field(..., description="Point forecast for the target horizon")
    lower_bound: Optional[float] = Field(default=None, description="Lower prediction interval bound")
    upper_bound: Optional[float] = Field(default=None, description="Upper prediction interval bound")
    timestamp: int = Field(..., description="Timestamp when prediction was produced (t_now)")
    target_timestamp: int = Field(..., description="Future timestamp being predicted (t_now + 3600s)")
    source_provenance: List[str] = Field(default_factory=list, description="List of source feeds consumed")
    input_window: InputWindow = Field(..., description="Input window bounds and count")
    status: str = Field(default="SIMULATED", description="Data status label")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Backward compatibility properties with existing services/api schema
    @property
    def estimated_price(self) -> float:
        return self.point_estimate

    @property
    def uncertainty_lower(self) -> float:
        return self.lower_bound if self.lower_bound is not None else self.point_estimate

    @property
    def uncertainty_upper(self) -> float:
        return self.upper_bound if self.upper_bound is not None else self.point_estimate

    @property
    def observed_at(self) -> int:
        return self.timestamp

    @property
    def source_ids(self) -> List[str]:
        return self.source_provenance

    @property
    def strategy_id(self) -> str:
        return self.method_id

    @property
    def strategy_name(self) -> str:
        return self.metadata.get("methodology_name", self.method_id)


class PredictionErrorRecord(BaseModel):
    """Evaluation record comparing a point prediction against the realized future value."""
    t_pred: int
    t_target: int
    point_estimate: float
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    realized_value: float
    error: float = Field(..., description="Realized minus point estimate: y - y_hat")
    abs_error: float = Field(..., description="|y - y_hat|")
    pct_error: float = Field(..., description="(y - y_hat) / y * 100")
    abs_pct_error: float = Field(..., description="|y - y_hat| / y * 100")
    direction_actual: int = Field(..., description="+1 if y > y_t, -1 if y < y_t, 0 if equal")
    direction_pred: int = Field(..., description="+1 if y_hat > y_t, -1 if y_hat < y_t, 0 if equal")
    direction_correct: bool = Field(..., description="True if predicted move matches actual move sign")
    interval_covered: Optional[bool] = Field(default=None, description="True if realized value is within bounds")


class EvaluationMetrics(BaseModel):
    """
    Standardized quantitative performance metrics.
    Rule #4: Pure mathematical evaluation; does not invent statistical meaning.
    """
    mae: float = Field(..., description="Mean Absolute Error: mean(|y - y_hat|)")
    rmse: float = Field(..., description="Root Mean Squared Error: sqrt(mean((y - y_hat)^2))")
    directional_accuracy: float = Field(..., description="Fraction of non-zero price moves where direction was correctly anticipated")
    mean_percentage_error: float = Field(..., description="Mean Percentage Error (MPE): mean((y - y_hat) / y) * 100")
    mean_absolute_percentage_error: float = Field(..., description="Mean Absolute Percentage Error (MAPE): mean(|y - y_hat| / y) * 100")
    prediction_interval_coverage: Optional[float] = Field(default=None, description="Fraction of observations falling inside [lower_bound, upper_bound]")
    sample_count: int = Field(..., description="Number of rolling predictions evaluated")


class MethodologyResult(BaseModel):
    """Comprehensive evaluation record for a single candidate validator methodology."""
    methodology_id: str
    methodology_name: str
    method_version: str
    dataset_name: str
    evaluation_period: Dict[str, Any] = Field(
        ...,
        description="Dictionary with start_ts, end_ts, horizon_seconds, rolling_step_seconds, sample_count"
    )
    metrics: EvaluationMetrics
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    status: str = Field(default="SIMULATED", description="Must remain SIMULATED for prototype evaluation")


class BenchmarkComparison(BaseModel):
    """Multi-methodology side-by-side benchmark comparison."""
    benchmark_id: str
    dataset_name: str
    horizon_seconds: int = 3600
    timestamp: int
    results: List[MethodologyResult]
    ranked_by_mae: List[str]
    status: str = "SIMULATED"
