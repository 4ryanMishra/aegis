"""
AEGIS Pydantic Domain Models.
Cross-Oracle Agreement & Risk-Resolution Layer Data Contracts.
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


class OracleSourceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    DELAYED = "DELAYED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class OracleStatus(str, Enum):
    HEALTHY_CONSENSUS = "HEALTHY_CONSENSUS"
    SUSPECTED_INCONSISTENCY = "SUSPECTED_INCONSISTENCY"
    EVIDENCE_OF_ABNORMAL_DEVIATION = "EVIDENCE_OF_ABNORMAL_DEVIATION"
    DISPERSED_UNCERTAINTY = "DISPERSED_UNCERTAINTY"
    HALTED_CIRCUIT_BREAKER = "HALTED_CIRCUIT_BREAKER"
    PENDING_FINALIZATION = "PENDING_FINALIZATION"


class DecisionState(str, Enum):
    HEALTHY_CONSENSUS = "HEALTHY_CONSENSUS"
    MULTIPLI_DEVIATION = "MULTIPLI_DEVIATION"
    SOURCE_DEGRADED = "SOURCE_DEGRADED"
    NO_CONSENSUS = "NO_CONSENSUS"
    MARKET_CORROBORATED = "MARKET_CORROBORATED"
    ORACLE_INSTABILITY = "ORACLE_INSTABILITY"


class DecisionPolicy(str, Enum):
    NEAREST_TO_MARKET = "NEAREST_TO_MARKET"
    ROBUST_MEDIAN = "ROBUST_MEDIAN"
    USE_OSM = "USE_OSM"
    RESTRICT = "RESTRICT"


class DataStatus(str, Enum):
    SIMULATED = "SIMULATED"
    OBSERVED = "OBSERVED"
    PENDING = "PENDING"
    OFF_CHAIN_API = "OFF_CHAIN_API"
    TO_VERIFY = "TO_VERIFY"


class OracleObservation(BaseModel):
    source_id: str = Field(default="oracle_feed", description="Unique provider ID (e.g. chainlink_main, pyth_gold)")
    name: str = Field(default="Oracle Network", description="Human-readable provider name (e.g. Chainlink, Pyth, Chronicle)")
    price: Optional[float] = Field(default=None, description="Observed price in USD")
    updated_at: int = Field(default=0, description="Unix timestamp of observation")
    age_seconds: int = Field(default=0, description="Seconds elapsed since update")
    status: Union[OracleSourceStatus, DataStatus, str] = Field(default=OracleSourceStatus.ACTIVE)
    confidence: Optional[float] = Field(default=None, description="Native confidence / spread bound")
    has_confidence: bool = Field(default=False)
    valid: bool = Field(default=True)
    cluster_id: Optional[str] = Field(default=None, description="Assigned agreement cluster ID (e.g. 'A', 'OUTLIER')")

    # Backward compatibility attributes for legacy validator strategies
    validator_id: Optional[str] = None
    lane_id: Optional[Union[str, int]] = None
    operator_id: Optional[str] = "operator_node_1"
    methodology: Optional[str] = None
    methodology_name: Optional[str] = None
    methodology_version: Optional[str] = "1.0.0"
    timestamp: Optional[int] = 0
    input_sources: Optional[List[str]] = None
    input_values: Optional[Dict[str, Any]] = None
    role: Optional[Union[MethodologyRole, str]] = None
    is_price_estimator: bool = True
    estimated_price: Optional[float] = None
    uncertainty_lower: Optional[float] = None
    uncertainty_upper: Optional[float] = None
    diagnostic_evidence: Optional[Dict[str, Any]] = None
    intermediate_metrics: Optional[Dict[str, Any]] = None
    anomaly_score: float = 0.0
    decision: str = "OBSERVATION_ACCEPTED"
    reason_code: str = "NORMAL"
    provenance: Optional[Dict[str, Any]] = None
    computation_metadata: Optional[Dict[str, Any]] = None
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = None
    observed_at: Optional[int] = 0
    source_ids: Optional[List[str]] = None
    method_version: Optional[str] = "0.1.0"

    @model_validator(mode="before")
    @classmethod
    def populate_compat_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "validator_id" in data and "source_id" not in data:
                data["source_id"] = data["validator_id"]
            if "methodology_name" in data and "name" not in data:
                data["name"] = data["methodology_name"]
            elif "methodology" in data and "name" not in data:
                data["name"] = str(data["methodology"])
            if "estimated_price" in data and data.get("price") is None:
                data["price"] = data["estimated_price"]
        return data


# Backward compatibility aliases
ValidatorObservation = OracleObservation
ValidatorResult = OracleObservation


class ConsensusResult(BaseModel):
    consensus_price: Optional[float] = Field(None, description="Median price of largest valid cluster")
    cluster_size: int = Field(default=0, description="Number of feeds in agreement cluster")
    total_eligible: int = Field(default=0, description="Total active eligible feeds")
    agreement_ratio: float = Field(default=0.0, description="Fraction of eligible feeds agreeing (e.g. 0.857 = 85.7%)")
    cluster_min: Optional[float] = Field(None)
    cluster_max: Optional[float] = Field(None)
    cluster_spread_pct: float = Field(default=0.0, description="Relative spread within cluster (%)")
    has_strong_consensus: bool = Field(default=False)
    cluster_members: List[str] = Field(default_factory=list)
    outlier_members: List[str] = Field(default_factory=list)

    # Backward compatibility properties
    value: Optional[float] = None
    aggregation: str = "median_uncertainty_weighted"
    validator_count: int = 0
    eligible_count: int = 0
    rejected_count: int = 0
    dispersion: float = 0.0
    quorum_met: bool = True
    status: DataStatus = DataStatus.SIMULATED
    eligible_lane_ids: List[str] = Field(default_factory=list)
    lane_estimates: Dict[str, Optional[float]] = Field(default_factory=dict)
    lane_results: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sync_compat(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "consensus_price" in data and "value" not in data:
                data["value"] = data["consensus_price"]
            elif "value" in data and "consensus_price" not in data:
                data["consensus_price"] = data["value"]
            if "cluster_size" in data and "validator_count" not in data:
                data["validator_count"] = data["cluster_size"]
        return data


DECAggregate = ConsensusResult


class TimelineMarker(BaseModel):
    time_seconds: int = Field(default=0)
    time_formatted: str = Field(default="00:00")
    title: str = Field(default="NORMAL")
    description: str = Field(default="")
    severity: str = Field(default="INFO")  # INFO, SUCCESS, WARNING, ALERT, CRITICAL


class RiskDecisionResult(BaseModel):
    state: str = Field(default="HEALTHY_CONSENSUS")
    oracle_status: OracleStatus = Field(default=OracleStatus.HEALTHY_CONSENSUS)
    final_price: Optional[float] = Field(None, description="Authoritative protocol valuation")
    selected_source: str = Field(default="MULTIPLI_OSM", description="MULTIPLI_OSM, CONSENSUS_MEDIAN, MARKET_REFERENCE, CONSERVATIVE_MIN, NONE")
    consensus_price: Optional[float] = Field(None, description="Consensus median")
    cluster_size: int = Field(default=0, description="Agreeing feeds count")
    total_eligible: int = Field(default=0, description="Total eligible feeds count")
    multipli_deviation_pct: float = Field(default=0.0, description="|P_OSM - P_CONSENSUS| / P_CONSENSUS * 100")
    is_conservative_applied: bool = Field(default=False, description="True if min(P_OSM, P_CONSENSUS) was enforced")
    market_reference_used: bool = Field(default=False, description="True if terminal market reference was used")
    policy_rationale: str = Field(default="", description="Audit explanation of decision")
    effective_ltv: float = Field(default=0.80)
    protocol_state: str = Field(default="NORMAL", description="NORMAL, RESTRICTED, HALTED")

    # Backward compatibility properties
    action: str = "ALLOW"
    decision: str = "VERIFIED"
    policy: Union[DecisionPolicy, str] = "USE_OSM"
    dispute_status: Optional[str] = None
    confidence: Optional[float] = 0.95
    reason_codes: List[str] = Field(default_factory=list)
    policy_version: str = "0.2.0"


DecisionResult = RiskDecisionResult


class UserPositionState(BaseModel):
    user_address: str = Field(default="0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
    collateral_asset: str = Field(default="Tokenized Gold (XAU)")
    collateral_amount: float = Field(default=10.0, description="Deposited collateral (oz)")
    collateral_value: float = Field(default=43200.0, description="Collateral value under authoritative price")
    effective_oracle_price: float = Field(default=4320.0, description="Price used for valuation")
    debt_amount: float = Field(default=28000.0, description="Borrowed RWAUSD debt")
    current_ltv: float = Field(default=0.648, description="Debt / Collateral Value")
    effective_ltv: float = Field(default=0.80, description="Max permitted LTV under active risk state")
    max_borrow_capacity: float = Field(default=34560.0, description="Collateral Value * Effective LTV")
    borrowing_headroom: float = Field(default=6560.0, description="Max Borrow - Current Debt")
    health_factor: float = Field(default=1.23, description="Max Capacity / Current Debt")
    protocol_state: str = Field(default="NORMAL", description="NORMAL, RESTRICTED, HALTED")
    position_status: str = Field(default="HEALTHY", description="HEALTHY, RESTRICTED, OVER_LIMIT, AT_RISK, HALTED")
    bad_debt_prevented: float = Field(default=0.0, description="Cumulative bad debt prevented ($)")


class CausalChainTelemetry(BaseModel):
    multipli_price: Optional[float] = None
    consensus_price: Optional[float] = None
    market_price: Optional[float] = None
    deviation_pct: float = 0.0
    agreement_ratio: float = 1.0
    oracle_state: str = "HEALTHY_CONSENSUS"
    selected_price: Optional[float] = None
    effective_ltv: float = 0.80
    max_borrow_capacity: float = 32400.0
    position_status: str = "HEALTHY"


class TimeSeriesPoint(BaseModel):
    minute: int
    time_label: str = Field(default="00:00")
    p_multipli: Optional[float] = None
    p_consensus: Optional[float] = None
    p_market: Optional[float] = None
    cluster_min: Optional[float] = None
    cluster_max: Optional[float] = None
    p_osm: Optional[float] = None
    p_dec: Optional[float] = None
    uncertainty_lower: Optional[float] = None
    uncertainty_upper: Optional[float] = None


class SimulationEvent(BaseModel):
    timestamp: str
    category: str
    message: str
    severity: str  # INFO, SUCCESS, WARNING, ALERT, CRITICAL


class TimeWindow(BaseModel):
    start_ts: int = 1774000000
    end_ts: int = 1774003600
    duration_seconds: int = 3600
    elapsed_seconds: int = 3600
    is_finalized: bool = True


class OSMFeed(BaseModel):
    value: float = 4050.0
    timestamp: int = 1774000000
    asset: Optional[str] = "XAU/USD"
    source: str = "multipli_osm"
    status: DataStatus = DataStatus.SIMULATED
    description: Optional[str] = "Multipli OSM delayed price"


class MarketObservation(BaseModel):
    value: Optional[float] = 4050.0
    timestamp: Optional[int] = 1774000000
    source: Optional[str] = "market_terminal"
    status: DataStatus = DataStatus.SIMULATED
    symbol: Optional[str] = "XAU/USD"
    is_offchain: bool = True


class EvidenceRecord(BaseModel):
    d_osm_market: Optional[float] = None
    d_dec_market: Optional[float] = None
    d_osm_dec: Optional[float] = None
    validator_dispersion: float = 0.0
    agreement_ratio: float = 1.0
    oracle_status: OracleStatus = OracleStatus.HEALTHY_CONSENSUS
    anomaly_score: float = 0.0
    reason_codes: List[str] = Field(default_factory=list)
    lane_anomalies: Dict[str, bool] = Field(default_factory=dict)
    conflict_indicators: Dict[str, bool] = Field(default_factory=dict)
    methodology_statuses: Dict[str, str] = Field(default_factory=dict)
    cusum_state: Optional[str] = None
    ou_structural_state: Optional[str] = None
    kalman_gated: bool = False
    conflict_detected: bool = False


class CollateralImpact(BaseModel):
    ltv: float = 0.80
    baseline_value: Optional[float] = 32400.0
    aegis_value: Optional[float] = 32400.0
    difference: Optional[float] = 0.0
    risk_exposure_pct: Optional[float] = 0.0
    protected_capital: Optional[float] = 0.0


class ScenarioRecord(BaseModel):
    scenario_id: str
    title: str
    description: str
    asset: str
    window: TimeWindow = Field(default_factory=TimeWindow)
    p_osm: OSMFeed = Field(default_factory=OSMFeed)
    validators: List[OracleObservation] = Field(default_factory=list)
    p_dec: ConsensusResult = Field(default_factory=ConsensusResult)
    p_market: MarketObservation = Field(default_factory=MarketObservation)
    evidence: EvidenceRecord = Field(default_factory=EvidenceRecord)
    decision: RiskDecisionResult = Field(default_factory=RiskDecisionResult)
    collateral: CollateralImpact = Field(default_factory=CollateralImpact)


class SimulationSnapshot(BaseModel):
    scenario_id: str
    title: str
    description: str
    asset: str = "Tokenized Gold (XAU/USD)"
    simulation_time_seconds: float = 0.0
    simulation_time_formatted: str = "00:00"
    elapsed_minutes: int = 0
    window_duration_seconds: int = 3600
    speed_multiplier: float = 60.0
    is_running: bool = False
    is_paused: bool = False
    is_finalized: bool = False
    current_block: str = "SIM-18400"
    ltv: float = 0.80
    total_lanes_count: int = 5
    active_lanes_count: int = 5
    total_validators_count: int = 6
    active_validators_count: int = 6
    total_observations: int = 60
    p_dec_uncertainty_half_width: float = 0.25

    # Cross-Oracle specific properties
    oracle_sources: List[OracleObservation] = Field(default_factory=list)
    multipli_observation: Optional[OracleObservation] = None
    market_observation: Optional[OracleObservation] = None
    consensus: ConsensusResult = Field(default_factory=ConsensusResult)
    decision: RiskDecisionResult = Field(default_factory=RiskDecisionResult)
    position: UserPositionState = Field(default_factory=UserPositionState)
    causal_chain: CausalChainTelemetry = Field(default_factory=CausalChainTelemetry)
    time_series: List[TimeSeriesPoint] = Field(default_factory=list)
    events: List[SimulationEvent] = Field(default_factory=list)
    interpretation: str = ""
    timeline_markers: List[TimelineMarker] = Field(default_factory=list)
    bad_debt_prevented: float = 0.0

    # Backward-compat
    p_osm: OSMFeed = Field(default_factory=OSMFeed)
    p_dec: ConsensusResult = Field(default_factory=ConsensusResult)
    p_market: MarketObservation = Field(default_factory=MarketObservation)
    evidence: EvidenceRecord = Field(default_factory=EvidenceRecord)
    collateral: CollateralImpact = Field(default_factory=CollateralImpact)
    validators: List[OracleObservation] = Field(default_factory=list)
    lane_telemetry: Dict[str, Any] = Field(default_factory=dict)


class ScenarioListItem(BaseModel):
    scenario_id: str
    title: str
    description: str
    asset: str
    p_osm_initial: float = 4320.0
    expected_market: float = 4320.0
    category: str = "NORMAL"
    ltv_default: float = 0.80
    timeline_markers: List[TimelineMarker] = Field(default_factory=list)


# Request Models
class SimulationResetRequest(BaseModel):
    scenario_id: Optional[str] = Field(default="scen_normal")
    ltv_factor: Optional[float] = Field(default=0.80)
    seed: Optional[int] = Field(default=42)


class SimulationStepRequest(BaseModel):
    delta_seconds: Optional[float] = Field(default=600.0)


class SimulationConfigRequest(BaseModel):
    speed_multiplier: Optional[float] = None
    scenario_id: Optional[str] = None
    ltv_factor: Optional[float] = None


class PositionUpdateRequest(BaseModel):
    collateral_amount: Optional[float] = Field(default=None, ge=0.0)
    debt_amount: Optional[float] = Field(default=None, ge=0.0)
    set_max_borrow: Optional[bool] = Field(default=False)


class ScenarioRunRequest(BaseModel):
    scenario_id: str = "scen_normal"
    ltv_factor: Optional[float] = 0.80
    custom_seed: Optional[int] = 42
    step_seconds: Optional[int] = 3600


class CustomVerificationRequest(BaseModel):
    asset: str = "XAU/USD"
    p_osm: float = 4050.0
    p_market: float = 4050.0
    ltv_factor: float = 0.80
