"""
Domain data structures for validator predictions, rolling evaluation, historical datasets,
data manifests, and benchmark results.
Conforms strictly to Phase 2A and Phase 2B requirements.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, model_validator


from enum import Enum


class MethodologyRole(str, Enum):
    PRICE_ESTIMATOR = "PRICE_ESTIMATOR"
    DIAGNOSTIC_ANOMALY_DETECTOR = "DIAGNOSTIC_ANOMALY_DETECTOR"
    UNCERTAINTY_CONSENSUS_MEASURE = "UNCERTAINTY_CONSENSUS_MEASURE"
    RWA_STRUCTURAL_CHECK = "RWA_STRUCTURAL_CHECK"
    SEQUENTIAL_DRIFT_DETECTOR = "SEQUENTIAL_DRIFT_DETECTOR"


DataStatusType = Literal["LIVE", "HISTORICAL", "REPLAY", "SIMULATED"]


class HistoricalMarketObservation(BaseModel):
    """
    Canonical historical market observation model.
    Retains timestamp, price, asset, provider source, and provenance metadata.
    """
    timestamp: int = Field(..., description="Observation Unix timestamp in integer seconds (UTC)")
    price: float = Field(..., gt=0.0, description="Observed market price (strictly > 0.0)")
    source: str = Field(default="simulated_market_feed", description="Originating provider/market source identifier")
    asset: str = Field(default="XAU/USD", description="Asset or trading pair symbol (e.g. PAXG/USDT, XAU/USD)")
    status: str = Field(default="HISTORICAL", description="Data integrity status: LIVE, HISTORICAL, REPLAY, SIMULATED")
    volume: Optional[float] = Field(default=None, description="Observed volume if available")
    bid: Optional[float] = Field(default=None, description="Best bid quote if available")
    ask: Optional[float] = Field(default=None, description="Best ask quote if available")
    open: Optional[float] = Field(default=None, description="Interval open price")
    high: Optional[float] = Field(default=None, description="Interval high price")
    low: Optional[float] = Field(default=None, description="Interval low price")
    close: Optional[float] = Field(default=None, description="Interval close price")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary provenance/tick metadata")

    @model_validator(mode="before")
    @classmethod
    def handle_source_id_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "source_id" in data and "source" not in data:
                data["source"] = data["source_id"]
        return data

    @property
    def source_id(self) -> str:
        return self.source


# Backward-compatible alias for existing quant code
class TimestampedObservation(HistoricalMarketObservation):
    """Backward-compatible alias for HistoricalMarketObservation."""
    pass


class DatasetManifest(BaseModel):
    """
    Metadata manifest detailing the origin, time boundaries, sampling frequency,
    and acquisition integrity of a market dataset.
    """
    dataset_id: str = Field(..., description="Unique immutable dataset identifier")
    asset: str = Field(..., description="Target asset identifier (e.g. PAXG/USDT, XAU/USD)")
    source: str = Field(..., description="Primary data provider/archive (e.g. binance_vision_public_archive)")
    acquisition_method: str = Field(
        ...,
        description="Method of acquisition: MANUAL_DOWNLOAD, REST_API_BATCH, DETERMINISTIC_SYNTHETIC, HISTORICAL_REPLAY"
    )
    source_url: Optional[str] = Field(default=None, description="Public documentation or download URL")
    timezone: str = Field(default="UTC", description="Normalized timezone of records (always UTC in AEGIS)")
    sampling_interval_seconds: int = Field(default=60, description="Target sampling interval in seconds (e.g. 60 for 1m)")
    start_timestamp: int = Field(..., description="First observation timestamp in seconds (UTC)")
    end_timestamp: int = Field(..., description="Last observation timestamp in seconds (UTC)")
    status: str = Field(default="HISTORICAL", description="Data status: LIVE, HISTORICAL, REPLAY, SIMULATED")
    checksum_sha256: Optional[str] = Field(default=None, description="SHA-256 hash of the raw dataset file")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="License, citation, notes, collection date")


class DataQualityReport(BaseModel):
    """
    Data quality audit report assessing continuity, duplicate counts,
    and missing intervals in a historical dataset.
    """
    observation_count: int = Field(..., description="Total raw rows or observations processed")
    valid_count: int = Field(..., description="Total valid records retained after cleaning")
    dropped_duplicates: int = Field(default=0, description="Duplicate timestamps removed")
    invalid_prices_count: int = Field(default=0, description="Non-positive, null, or invalid price rows dropped")
    missing_intervals_count: int = Field(default=0, description="Number of interval gaps detected (> 1.5 * sampling_interval)")
    expected_intervals_count: int = Field(..., description="Theoretical expected tick count over [min_ts, max_ts]")
    coverage_percentage: float = Field(..., description="Percentage of expected interval ticks present (valid / expected * 100)")
    min_timestamp: Optional[int] = Field(default=None, description="Earliest observation timestamp (UTC)")
    max_timestamp: Optional[int] = Field(default=None, description="Latest observation timestamp (UTC)")
    source: str = Field(..., description="Source feed identifier")
    data_status: str = Field(default="HISTORICAL", description="LIVE, HISTORICAL, REPLAY, SIMULATED")
    gaps: List[Dict[str, int]] = Field(default_factory=list, description="List of detected gaps with start_ts, end_ts, duration_seconds")
    is_strictly_monotonic: bool = Field(default=True, description="Whether timestamps are strictly increasing")


class InputWindow(BaseModel):
    """Metadata describing the historical observation window fed into the prediction."""
    start_ts: int = Field(..., description="Oldest timestamp included in input")
    end_ts: int = Field(..., description="Most recent timestamp included in input (strictly <= t_pred)")
    observation_count: int = Field(..., description="Number of historical ticks in window")
    sampling_interval_sec: int = Field(default=60, description="Step frequency in seconds")


class ValidatorResult(BaseModel):
    """
    Canonical ValidatorResult Model (Phase 4A Task 2).
    Carries complete forensic intermediate evidence explaining HOW a methodology
    reached its conclusion.
    """
    validator_id: str = Field(..., description="Unique validator node identifier")
    methodology: str = Field(default="KALMAN_1D", description="Machine identifier (KALMAN_1D, HUBER_IRLS, JSD, OU_RESIDUAL, CUSUM)")
    methodology_name: str = Field(default="Methodology Lane", description="Human-readable methodology name")
    methodology_version: str = Field(default="1.0.0", description="Methodology version or code hash")
    lane_id: int = Field(default=1, ge=1, le=5, description="Methodology lane number (1-5)")
    operator_id: str = Field(default="operator_node_1", description="Independent operator identifier")
    timestamp: int = Field(default=0, description="Observation timestamp within verification window")

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "methodology" not in data and "strategy_id" in data:
                data["methodology"] = data["strategy_id"]
            if "methodology_name" not in data and "strategy_name" in data:
                data["methodology_name"] = data["strategy_name"]
            if "timestamp" not in data and "observed_at" in data:
                data["timestamp"] = data["observed_at"]
            if "input_sources" not in data and "source_ids" in data:
                data["input_sources"] = data["source_ids"]
        return data

    input_sources: List[str] = Field(default_factory=list, description="Feeds/sources consumed")
    input_values: Dict[str, Any] = Field(default_factory=dict, description="Input values summary")

    role: MethodologyRole = Field(default=MethodologyRole.PRICE_ESTIMATOR, description="Functional role of the methodology")
    is_price_estimator: bool = Field(default=True, description="Whether this methodology outputs an eligible price estimate for P_DEC")
    estimated_price: Optional[float] = Field(default=None, description="Estimated reference/forecast price (None for diagnostic lanes)")
    uncertainty_lower: Optional[float] = Field(default=None, description="Lower uncertainty bound (None for diagnostic lanes)")
    uncertainty_upper: Optional[float] = Field(default=None, description="Upper uncertainty bound (None for diagnostic lanes)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Methodology confidence / quality representation")

    diagnostic_evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic evidence payload for Evidence Engine"
    )
    intermediate_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Forensic intermediate metrics explaining how methodology reached conclusion"
    )

    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized anomaly heuristic [0, 1]")
    decision: str = Field(default="ACCEPTED", description="ACCEPTED, GATED, OUTLIER, DRIFTING, TRIPPED, NOT_APPLICABLE")
    reason_code: str = Field(default="MODEL_CONSISTENT", description="Machine-readable diagnostic reason code")

    provenance: Dict[str, Any] = Field(default_factory=dict, description="Data provenance & audit trail")
    computation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Runtime execution metadata")
    status: str = Field(default="SIMULATED")
    input_window: Optional[InputWindow] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def strategy_id(self) -> str:
        return self.methodology.lower()

    @property
    def strategy_name(self) -> str:
        return self.methodology_name

    @property
    def observed_at(self) -> int:
        return self.timestamp

    @property
    def source_ids(self) -> List[str]:
        return self.input_sources

    @property
    def method_version(self) -> str:
        return self.methodology_version

    @property
    def point_estimate(self) -> Optional[float]:
        return self.estimated_price

    @property
    def lower_bound(self) -> Optional[float]:
        return self.uncertainty_lower

    @property
    def upper_bound(self) -> Optional[float]:
        return self.uncertainty_upper

    @property
    def method_id(self) -> str:
        return self.methodology


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
    dataset_id: Optional[str] = None
    dataset_status: str = "HISTORICAL"
    source: str = "unknown_source"
    horizon_seconds: int = 3600
    sampling_interval_seconds: int = 60
    evaluation_period: Dict[str, Any] = Field(
        ...,
        description="Dictionary with start_ts, end_ts, horizon_seconds, rolling_step_seconds, sample_count"
    )
    metrics: EvaluationMetrics
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    status: str = Field(default="HISTORICAL", description="Must remain SIMULATED/HISTORICAL as appropriate")


class BenchmarkComparison(BaseModel):
    """Multi-methodology side-by-side benchmark comparison."""
    benchmark_id: str
    dataset_name: str
    dataset_id: Optional[str] = None
    dataset_status: str = "HISTORICAL"
    source: str = "unknown_source"
    sampling_interval_seconds: int = 60
    horizon_seconds: int = 3600
    timestamp: int
    results: List[MethodologyResult]
    ranked_by_mae: List[str]
    status: str = "HISTORICAL"
