"""
AEGIS Pydantic Domain Models.
Strictly adheres to docs/DATA_CONTRACT.md and anti-hallucination policies.
All mock data is explicitly labeled SIMULATED / OFF_CHAIN_API.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


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


class ValidatorObservation(BaseModel):
    validator_id: str = Field(..., description="Logical validator ID (e.g. val_alpha)")
    strategy_id: str = Field(..., description="Strategy plugin identifier")
    strategy_name: str = Field(..., description="Human-readable methodology name")
    estimated_price: float = Field(..., description="Estimated reference price")
    uncertainty_lower: float = Field(..., description="Lower uncertainty bound (e.g. 5th percentile)")
    uncertainty_upper: float = Field(..., description="Upper uncertainty bound (e.g. 95th percentile)")
    observed_at: int = Field(..., description="Timestamp of submission within the 1-hour window")
    source_ids: List[str] = Field(default_factory=list, description="List of underlying data feeds used")
    method_version: str = Field(default="0.1.0-alpha")
    status: DataStatus = Field(default=DataStatus.SIMULATED)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DECAggregate(BaseModel):
    value: Optional[float] = Field(None, description="Decentralized reference value P_DEC")
    aggregation: str = Field(default="median", description="Aggregation method (e.g. median, trimmed_mean)")
    validator_count: int = Field(default=0)
    dispersion: float = Field(default=0.0, description="Normalized IQR dispersion metric")
    quorum_met: bool = Field(default=False)
    status: DataStatus = Field(default=DataStatus.SIMULATED)


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


class DecisionResult(BaseModel):
    policy: DecisionPolicy = Field(default=DecisionPolicy.NEAREST_TO_MARKET)
    final_price: Optional[float] = Field(None, description="Final protocol valuation")
    selected_source: str = Field(default="PENDING", description="P_OSM, P_DEC, P_MARKET, or RESTRICT")
    confidence: Optional[float] = Field(None, description="Confidence score [0, 1]")
    reason_codes: List[str] = Field(default_factory=list)
    policy_version: str = Field(default="0.1.0-mvp")


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
    validators: List[ValidatorObservation]
    p_dec: DECAggregate
    p_market: MarketObservation
    evidence: EvidenceRecord
    decision: DecisionResult
    collateral: CollateralImpact


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
