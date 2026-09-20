export type DataStatus = 'SIMULATED' | 'OBSERVED' | 'PENDING' | 'OFF_CHAIN_API' | 'TO_VERIFY';

export type OracleStatus = 
  | 'HEALTHY_CONSENSUS'
  | 'SUSPECTED_INCONSISTENCY'
  | 'EVIDENCE_OF_ABNORMAL_DEVIATION'
  | 'DISPERSED_UNCERTAINTY'
  | 'PENDING_FINALIZATION'
  | 'VALIDATOR_QUORUM_DEFICIT'
  | 'OUTLIER_CONTAMINATED_CONSENSUS'
  | 'LATENT_SYSTEMATIC_DRIFT'
  | 'STRUCTURAL_DEPEG_ANOMALY';

export type DecisionPolicy = 
  | 'NEAREST_TO_MARKET' 
  | 'ROBUST_MEDIAN' 
  | 'USE_OSM' 
  | 'RESTRICT' 
  | 'RESTRICT_COLLATERAL_CEILING' 
  | 'CIRCUIT_BREAKER_HALT'
  | 'VERIFIED'
  | 'WARNING'
  | 'DISPUTED'
  | 'RESTRICTED'
  | 'HALTED';

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

export interface KalmanMetrics {
  prior_state: number;
  prior_covariance: number;
  observation: number;
  innovation: number;
  innovation_covariance?: number;
  innovation_variance?: number;
  kalman_gain: number;
  posterior_state: number;
  posterior_covariance: number;
  mahalanobis_d2: number;
  chi2_threshold: number;
  alpha?: number;
  confidence_level?: number;
  is_accepted?: boolean;
  gate_decision?: string;
  measurement_noise_r?: number;
  process_noise_q?: number;
}

export interface HuberWeightRecord {
  price: number;
  residual: number;
  std_residual: number;
  weight: number;
  is_outlier: boolean;
}

export interface HuberMetrics {
  raw_observations: number[];
  initial_median: number;
  mad: number;
  scale_s: number;
  huber_k: number;
  iterations: number;
  converged: boolean;
  weights_table: HuberWeightRecord[];
  final_estimate: number;
  robust_dispersion: number;
  standard_error: number;
  outlier_count: number;
}

export interface JSDMetrics {
  pairwise_jsd_matrix: number[][];
  mean_divergence_per_lane: Record<string, number>;
  lane_weights: Record<string, number>;
  divergent_lanes: string[];
  informational_disagreement: number;
  grid_bins: number;
  lane_ids: string[];
}

export interface OUMetrics {
  is_rwa: boolean;
  has_anchor: boolean;
  spot_price: number;
  anchor_price?: number | null;
  log_spread?: number | null;
  theta?: number | null;
  mu?: number | null;
  sigma?: number | null;
  dt?: number | null;
  expected_spread?: number | null;
  conditional_variance?: number | null;
  standardized_residual?: number | null;
  is_jump_candidate?: boolean;
  not_applicable_reason?: string | null;
}

export interface CUSUMMetrics {
  current_price: number;
  baseline_mean: number;
  baseline_std: number;
  standardized_increment: number;
  s_pos: number;
  s_neg: number;
  drift_kappa: number;
  threshold_h: number;
  drift_detected: boolean;
  history_length: number;
  recent_trajectory?: number[];
}

export interface ValidatorObservation {
  validator_id: string;
  lane_id: string;
  operator_id: string;
  methodology: string;
  methodology_name: string;
  role?: string;
  is_price_estimator?: boolean;
  estimated_price: number | null;
  uncertainty_lower: number | null;
  uncertainty_upper: number | null;
  anomaly_score: number;
  decision: string;
  reason_code: string;
  diagnostic_evidence?: Record<string, any>;
  intermediate_metrics: Record<string, any>;
  status: DataStatus;
  
  // Backward-compatibility properties
  strategy_id?: string;
  strategy_name?: string;
  observed_at?: number;
  source_ids?: string[];
  method_version?: string;
}

export interface DECAggregate {
  value: number | null;
  aggregation: string;
  validator_count: number;
  dispersion: number;
  quorum_met: boolean;
  status: DataStatus;
  eligible_lane_ids?: string[];
  lane_estimates?: Record<string, number | null>;
  lane_results?: Array<Record<string, any>>;
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
  anomaly_score: number;
  reason_codes: string[];
  lane_anomalies?: Record<string, boolean>;
  conflict_indicators?: Record<string, boolean>;
  evidence_timestamp?: number;
}

export interface DecisionResult {
  policy: DecisionPolicy | string;
  decision?: string;
  final_price: number | null;
  selected_source: 'P_OSM' | 'P_DEC' | 'P_MARKET' | 'RESTRICT_HALT' | 'RESTRICT_COLLATERAL_CEILING' | 'CIRCUIT_BREAKER_HALT' | 'PENDING' | string;
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
  protected_capital?: number | null;
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
  intermediate_telemetry?: Record<string, any>;
}

export interface ScenarioListItem {
  scenario_id: string;
  title: string;
  description: string;
  asset: string;
  p_osm_initial: number;
  expected_market: number;
  category: 'NORMAL' | 'FLASH_SPIKE' | 'POISONED_VALIDATOR' | 'VALIDATOR_OUTAGE' | 'SLOW_DRIFT' | 'RWA_DEPEG' | string;
  ltv_default: number;
}
