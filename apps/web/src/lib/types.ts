export type DataStatus = 'SIMULATED' | 'OBSERVED' | 'PENDING' | 'OFF_CHAIN_API' | 'TO_VERIFY';

export type OracleSourceStatus = 'ACTIVE' | 'STALE' | 'DELAYED' | 'FAILED' | 'DISABLED';

export type OracleStatus = 
  | 'HEALTHY_CONSENSUS'
  | 'SUSPECTED_INCONSISTENCY'
  | 'EVIDENCE_OF_ABNORMAL_DEVIATION'
  | 'DISPERSED_UNCERTAINTY'
  | 'HALTED_CIRCUIT_BREAKER'
  | 'PENDING_FINALIZATION';

export type DecisionState = 
  | 'HEALTHY_CONSENSUS'
  | 'MULTIPLI_DEVIATION'
  | 'SOURCE_DEGRADED'
  | 'NO_CONSENSUS'
  | 'MARKET_CORROBORATED'
  | 'ORACLE_INSTABILITY';

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
  is_applicable?: boolean;
  spot_price: number;
  anchor_price?: number | null;
  log_spread?: number | null;
  theta?: number | null;
  mu?: number | null;
  sigma?: number | null;
  dt?: number | null;
  expected_spread?: number | null;
  conditional_variance?: number | null;
  conditional_std?: number | null;
  standardized_residual?: number | null;
  jump_threshold?: number;
  jump_candidate?: boolean;
  is_jump_candidate?: boolean;
  not_applicable_reason?: string | null;
}

export interface CUSUMMetrics {
  current_price: number;
  baseline_mean?: number;
  baseline_std?: number;
  tick_volatility?: number;
  standardized_increment: number;
  current_increment?: number;
  s_pos: number;
  s_neg: number;
  s_plus?: number;
  s_minus?: number;
  drift_kappa: number;
  kappa?: number;
  threshold_h: number;
  drift_detected: boolean;
  history_length: number;
  recent_trajectory?: number[];
}

export interface OracleObservation {
  source_id: string;
  name: string;
  price: number | null;
  updated_at: number;
  age_seconds: number;
  status: OracleSourceStatus;
  confidence?: number | null;
  has_confidence: boolean;
  valid: boolean;
  cluster_id?: string | null;

  // Backward compatibility properties for legacy drawer / views
  validator_id?: string;
  lane_id?: string;
  operator_id?: string;
  methodology?: string;
  methodology_name?: string;
  estimated_price?: number | null;
  uncertainty_lower?: number | null;
  uncertainty_upper?: number | null;
  anomaly_score?: number;
  decision?: string;
  reason_code?: string;
  is_price_estimator?: boolean;
  diagnostic_evidence?: Record<string, any>;
  intermediate_metrics?: Record<string, any>;
  observed_at?: number;
  strategy_id?: string;
  strategy_name?: string;
  source_ids?: string[];
  method_version?: string;
}

// Backward compatibility alias
export type ValidatorObservation = OracleObservation;

export interface ConsensusResult {
  consensus_price: number | null;
  cluster_size: number;
  total_eligible: number;
  agreement_ratio: number;
  cluster_min?: number | null;
  cluster_max?: number | null;
  cluster_spread_pct: number;
  has_strong_consensus: boolean;
  cluster_members: string[];
  outlier_members: string[];

  // Backward compatibility properties
  value?: number | null;
  aggregation?: string;
  validator_count?: number;
  dispersion?: number;
  quorum_met?: boolean;
  status?: DataStatus;
  eligible_lane_ids?: string[];
  lane_estimates?: Record<string, number | null>;
}

// Backward compatibility alias
export type DECAggregate = ConsensusResult;

export interface RiskDecisionResult {
  state: string;
  oracle_status: OracleStatus;
  final_price: number | null;
  multipli_deviation_pct: number;
  is_conservative_applied: boolean;
  policy_rationale: string;
  effective_ltv: number;
  protocol_state: string;

  // Backward compatibility properties
  policy?: DecisionPolicy | string;
  decision?: string;
  action?: string;
  dispute_status?: string;
  selected_source?: string;
  confidence?: number | null;
  reason_codes?: string[];
  policy_version?: string;
}

// Backward compatibility alias
export type DecisionResult = RiskDecisionResult;

export interface OSMFeed {
  value: number;
  timestamp: number;
  source: string;
  status: DataStatus;
  description?: string;
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
  validators: OracleObservation[];
  p_dec: ConsensusResult;
  p_market: MarketObservation;
  evidence: EvidenceRecord;
  decision: RiskDecisionResult;
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
  category: 'NORMAL' | 'FLASH_CRASH' | 'POISONED_VALIDATOR' | 'MARKET_DISLOCATION' | 'OSM_FAILURE' | string;
  ltv_default: number;
}

export interface SimulationEvent {
  timestamp: string;
  category: string;
  message: string;
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'ALERT' | 'CRITICAL';
}

export interface TimeSeriesPoint {
  minute: number;
  time_label: string;
  p_multipli?: number | null;
  p_consensus?: number | null;
  p_market?: number | null;
  cluster_min?: number | null;
  cluster_max?: number | null;

  // Backward compatibility fields
  p_osm?: number | null;
  p_dec?: number;
  uncertainty_lower?: number;
  uncertainty_upper?: number;
}

export interface UserPositionState {
  user_address: string;
  collateral_asset: string;
  collateral_amount: number;
  collateral_value: number;
  effective_oracle_price: number;
  debt_amount: number;
  current_ltv: number;
  effective_ltv: number;
  max_borrow_capacity: number;
  borrowing_headroom: number;
  health_factor: number;
  protocol_state: 'NORMAL' | 'RESTRICTED' | 'HALTED' | string;
  position_status: 'HEALTHY' | 'RESTRICTED' | 'OVER_LIMIT' | 'AT_RISK' | 'HALTED' | string;
}

export interface CausalChainTelemetry {
  multipli_price?: number | null;
  consensus_price?: number | null;
  market_price?: number | null;
  deviation_pct: number;
  agreement_ratio: number;
  oracle_state: string;
  selected_price?: number | null;
  effective_ltv: number;
  max_borrow_capacity: number;
  position_status: string;

  // Legacy aliases
  osm_price?: number | null;
  dec_price?: number | null;
  deviation_detected_pct?: number;
  anomaly_score?: number;
  oracle_status?: string;
  oracle_decision?: string;
}

export interface SimulationSnapshot {
  scenario_id: string;
  title: string;
  description: string;
  asset: string;
  simulation_time_seconds: number;
  simulation_time_formatted: string;
  elapsed_minutes: number;
  window_duration_seconds: number;
  speed_multiplier: number;
  is_running: boolean;
  is_paused: boolean;
  is_finalized: boolean;
  current_block: string;
  ltv?: number;

  // Cross-Oracle specific properties
  oracle_sources: OracleObservation[];
  multipli_observation?: OracleObservation | null;
  market_observation?: OracleObservation | null;
  consensus: ConsensusResult;
  decision: RiskDecisionResult;
  position: UserPositionState;
  causal_chain: CausalChainTelemetry;
  time_series: TimeSeriesPoint[];
  events: SimulationEvent[];
  interpretation: string;

  // Backward-compatibility properties
  total_observations?: number;
  active_validators_count?: number;
  total_validators_count?: number;
  active_lanes_count?: number;
  total_lanes_count?: number;
  p_osm?: OSMFeed;
  p_dec?: ConsensusResult;
  p_dec_uncertainty_half_width?: number;
  p_market?: MarketObservation;
  evidence?: EvidenceRecord;
  collateral?: CollateralImpact;
  validators?: OracleObservation[];
  validator_nodes?: any[];
  lane_telemetry?: Record<string, any>;
}
