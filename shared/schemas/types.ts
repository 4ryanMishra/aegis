/**
 * AEGIS Shared Types — Conforms strictly to docs/DATA_CONTRACT.md
 * Anti-hallucination note: All simulated & off-chain sources are typed with explicit status fields.
 */

export type DataStatus = 'SIMULATED' | 'OBSERVED' | 'PENDING' | 'OFF_CHAIN_API' | 'TO_VERIFY';

export type OracleStatus = 
  | 'HEALTHY_CONSENSUS'
  | 'SUSPECTED_INCONSISTENCY'
  | 'EVIDENCE_OF_ABNORMAL_DEVIATION'
  | 'DISPERSED_UNCERTAINTY'
  | 'PENDING_FINALIZATION';

export type DecisionPolicy = 'NEAREST_TO_MARKET' | 'ROBUST_MEDIAN' | 'USE_OSM' | 'RESTRICT';

export interface TimeWindow {
  start_ts: number;
  end_ts: number;
  duration_seconds: number;
  elapsed_seconds: number;
  is_finalized: boolean;
}

export interface OSMFeed {
  value: number;
  timestamp: number;
  source: string;
  status: DataStatus;
  description?: string;
}

export interface ValidatorObservation {
  validator_id: string;
  strategy_id: string;
  strategy_name: string;
  estimated_price: number;
  uncertainty_lower: number;
  uncertainty_upper: number;
  observed_at: number;
  source_ids: string[];
  method_version: string;
  status: DataStatus;
  metadata?: Record<string, unknown>;
}

export interface DECAggregate {
  value: number | null;
  aggregation: string;
  validator_count: number;
  dispersion: number;
  quorum_met: boolean;
  status: DataStatus;
}

export interface MarketObservation {
  value: number | null;
  timestamp: number | null;
  source: string | null;
  status: DataStatus;
  symbol?: string;
  is_offchain: boolean;
}

export interface EvidenceRecord {
  d_osm_market: number | null;
  d_dec_market: number | null;
  d_osm_dec: number | null;
  validator_dispersion: number;
  agreement_ratio: number;
  oracle_status: OracleStatus;
  anomaly_score: number; // 0.0 to 1.0 transparent heuristic score
  reason_codes: string[];
}

export interface DecisionResult {
  policy: DecisionPolicy;
  final_price: number | null;
  selected_source: 'P_OSM' | 'P_DEC' | 'P_MARKET' | 'RESTRICT_HALT' | 'PENDING';
  confidence: number | null;
  reason_codes: string[];
  policy_version: string;
}

export interface CollateralImpact {
  ltv: number;
  baseline_value: number | null;
  aegis_value: number | null;
  difference: number | null;
  risk_exposure_pct: number | null;
}

export interface ScenarioRecord {
  scenario_id: string;
  title: string;
  description: string;
  asset: string;
  window: TimeWindow;
  p_osm: OSMFeed;
  validators: ValidatorObservation[];
  p_dec: DECAggregate;
  p_market: MarketObservation;
  evidence: EvidenceRecord;
  decision: DecisionResult;
  collateral: CollateralImpact;
}

export interface ScenarioListItem {
  id: string;
  title: string;
  description: string;
  asset: string;
  p_osm: number;
  expected_market: number;
  category: 'OSM_SPIKE' | 'HEALTHY' | 'HIGH_VOLATILITY' | 'VALIDATOR_OUTLIER';
}
