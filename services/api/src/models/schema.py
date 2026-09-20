"""
AEGIS Pydantic Domain Models.
Strictly adheres to docs/DATA_CONTRACT.md and anti-hallucination policies.
Implements Phase 4A Canonical ValidatorResult model with rich intermediate metrics.
"""

from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, model_validator


class MethodologyRole(str, Enum):
    PRICE_ESTIMATOR = "PRICE_ESTIMATOR"
    DIAGNOSTIC_ANOMALY_DETECTOR = "DIAGNOSTIC_ANOMALY_DETECTOR"
    UNCERTAINTY_CONSENSUS_MEASURE = "UNCERTAINTY_CONSENSUS_MEASURE"
    RWA_STRUCTURAL_CHECK = "RWA_STRUCTURAL_CHECK"
    SEQUENTIAL_DRIFT_DETECTOR = "SEQUENTIAL_DRIFT_DETECTOR"


class DataStatus(str, Enum):
    SIMULATED = "SIMULATED"
    OBSERVED = "OBSERVED"
    PENDING = "PENDING"
    OFF_CHAIN_API = "OFF_CHAIN_API"
    TO_VERIFY = "TO_VERIFY"


class OracleStatus(str, Enum):
    HEALTHY_CONSENSUS = "HEALTHY_CONSENSUS"
    SUSPECTED_INCONSISTENCY = "SUSPECTED_INCONSISTENCY"
    EVIDENCE_OF_ABNORMAL_DEVIATION = "EVIDENCE_OF_ABNORMAL_DEVIATION"
    DISPERSED_UNCERTAINTY = "DISPERSED_UNCERTAINTY"
    PENDING_FINALIZATION = "PENDING_FINALIZATION"


class DecisionPolicy(str, Enum):
    NEAREST_TO_MARKET = "NEAREST_TO_MARKET"
    ROBUST_MEDIAN = "ROBUST_MEDIAN"
    USE_OSM = "USE_OSM"
    RESTRICT = "RESTRICT"


class TimeWindow(BaseModel):
    start_ts: int = Field(..., description="Timestamp at window start (T0)")
    end_ts: int = Field(..., description="Timestamp at window end (T1, typically T0 + 3600s)")
    duration_seconds: int = Field(default=3600)
    elapsed_seconds: int = Field(default=3600)
    is_finalized: bool = Field(default=True)


class OSMFeed(BaseModel):
    value: float = Field(..., description="Delayed oracle baseline price P_OSM")
    timestamp: int = Field(..., description="Timestamp when OSM value was queued at T0")
    source: str = Field(default="multipli_osm_mock", description="Source identifier")
    status: DataStatus = Field(default=DataStatus.SIMULATED)
    description: Optional[str] = Field(default="Baseline delayed OSM price feed")


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
    status: DataStatus = Field(default=DataStatus.SIMULATED)
    input_window: Optional[Dict[str, Any]] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Backward compatibility properties for existing consumers
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


# Backward-compatible alias
ValidatorObservation = ValidatorResult


class DECAggregate(BaseModel):
    value: Optional[float] = Field(None, description="Decentralized reference value P_DEC")
    aggregation: str = Field(default="deterministic_cross_validator", description="Aggregation method")
    validator_count: int = Field(default=0)
    eligible_count: int = Field(default=0)
    rejected_count: int = Field(default=0)
    dispersion: float = Field(default=0.0, description="Normalized robust dispersion metric")
    quorum_met: bool = Field(default=False)
    status: DataStatus = Field(default=DataStatus.SIMULATED)
    lane_results: List[Dict[str, Any]] = Field(default_factory=list, description="Preserved lane evidence summaries")


class MarketObservation(BaseModel):
    value: Optional[float] = Field(None, description="Independent market observation P_MARKET at T1")
    timestamp: Optional[int] = Field(None, description="Market observation timestamp")
    source: Optional[str] = Field(None, description="External provider adapter (e.g. simulated_binance_adapter)")
    status: DataStatus = Field(default=DataStatus.SIMULATED)
    symbol: Optional[str] = Field(default="XAU/USD")
    is_offchain: bool = Field(default=True, description="Must remain True for CEX/API sources")


class EvidenceRecord(BaseModel):
    d_osm_market: Optional[float] = Field(None, description="|P_OSM - P_MARKET| / P_MARKET")
    d_dec_market: Optional[float] = Field(None, description="|P_DEC - P_MARKET| / P_MARKET")
    d_osm_dec: Optional[float] = Field(None, description="|P_OSM - P_DEC| / P_DEC")
    validator_dispersion: float = Field(default=0.0)
    agreement_ratio: float = Field(default=1.0, description="Fraction of validators within normal dispersion")
    oracle_status: OracleStatus = Field(default=OracleStatus.PENDING_FINALIZATION)
    anomaly_score: float = Field(default=0.0, description="Normalized heuristic score [0, 1]")
    reason_codes: List[str] = Field(default_factory=list)
    methodology_statuses: Dict[str, str] = Field(default_factory=dict)
    cusum_state: Optional[str] = None
    ou_structural_state: Optional[str] = None
    kalman_gated: bool = False
    conflict_detected: bool = False


class DecisionResult(BaseModel):
    policy: DecisionPolicy = Field(default=DecisionPolicy.NEAREST_TO_MARKET)
    final_price: Optional[float] = Field(None, description="Final protocol valuation")
    selected_source: str = Field(default="PENDING", description="P_OSM, P_DEC, P_MARKET, or RESTRICT")
    confidence: Optional[float] = Field(None, description="Confidence score [0, 1]")
    reason_codes: List[str] = Field(default_factory=list)
    policy_version: str = Field(default="1.0.0-phase4a")
    action: str = Field(default="ALLOW", description="ALLOW, HAIRCUT, FREEZE, HALT")
    dispute_status: str = Field(default="VERIFIED", description="VERIFIED, WARNING, DISPUTED, RESTRICTED, HALTED")


class CollateralImpact(BaseModel):
    ltv: float = Field(default=0.60, description="Configured collateral factor / LTV")
    baseline_value: Optional[float] = Field(None, description="Collateral borrowing power under P_OSM")
    aegis_value: Optional[float] = Field(None, description="Collateral borrowing power under AEGIS final price")
    difference: Optional[float] = Field(None, description="Difference in borrowing power per unit")
    risk_exposure_pct: Optional[float] = Field(None, description="Overstatement percentage prevented")


class ScenarioRecord(BaseModel):
    scenario_id: str
    title: str
    description: str
    asset: str
    window: TimeWindow
    p_osm: OSMFeed
    validators: List[ValidatorResult]
    p_dec: DECAggregate
    p_market: MarketObservation
    evidence: EvidenceRecord
    decision: DecisionResult
    collateral: CollateralImpact
    intermediate_telemetry: Dict[str, Any] = Field(default_factory=dict)


class ScenarioRunRequest(BaseModel):
    scenario_id: str = Field(default="scen_gold_osm_spike_01")
    ltv_factor: Optional[float] = Field(default=0.60, ge=0.05, le=0.99)
    custom_seed: Optional[int] = Field(default=42)
    step_seconds: Optional[int] = Field(default=3600, description="Window time to simulate (up to 3600s)")


class CustomVerificationRequest(BaseModel):
    asset: str = Field(default="XAU/USD")
    p_osm: float = Field(..., gt=0.0)
    p_market: float = Field(..., gt=0.0)
    ltv_factor: float = Field(default=0.60, ge=0.05, le=0.99)
    validator_estimates: Optional[List[float]] = Field(default=None)
    policy: DecisionPolicy = Field(default=DecisionPolicy.NEAREST_TO_MARKET)
