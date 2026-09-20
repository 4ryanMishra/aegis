import { ScenarioRecord, ScenarioListItem } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchScenarios(): Promise<ScenarioListItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/scenarios`, { cache: 'no-store' });
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Graceful fallback to deterministic static list
  }

  return [
    {
      scenario_id: 'scen_normal_consensus',
      title: 'Normal Baseline Consensus (Stationary Market)',
      description: 'Stationary market conditions. Baseline OSM queues $95.20. All five methodology lanes agree within narrow dispersion. Protocol issues VERIFIED status at standard collateral factor.',
      asset: 'XAU/USD (Tokenized Gold)',
      category: 'NORMAL',
      p_osm_initial: 95.20,
      expected_market: 95.15,
      ltv_default: 0.60
    },
    {
      scenario_id: 'scen_flash_spike',
      title: 'Flash Spike Attack (Transient Upstream Anomaly)',
      description: 'Single-block liquidity manipulation causes a sudden +12% price spike. Lane 1 (Kalman) Mahalanobis innovation gate triggers (D² > 6.635, α=0.01) and rejects the observation, while Lane 2 (Huber) attenuates the quote weight.',
      asset: 'XAU/USD (Tokenized Gold)',
      category: 'FLASH_SPIKE',
      p_osm_initial: 106.50,
      expected_market: 95.00,
      ltv_default: 0.60
    },
    {
      scenario_id: 'scen_poisoned_validator',
      title: 'Poisoned Validator Node (Adversarial Sybil Outlier)',
      description: 'Validator Node 2 is compromised and submits a malicious +20% quote. Lane 2 (Huber M-estimation) calculates a high standardized residual and shrinks its weight. Lane 3 (JSD) isolates the divergent node.',
      asset: 'XAU/USD (Tokenized Gold)',
      category: 'POISONED_VALIDATOR',
      p_osm_initial: 95.00,
      expected_market: 95.10,
      ltv_default: 0.60
    },
    {
      scenario_id: 'scen_validator_outage',
      title: 'Validator Infrastructure Outage (Quorum Stress)',
      description: 'Network partition or infrastructure crash takes Nodes 4 and 5 offline. The verification coordinator validates that remaining 3 nodes satisfy minimum quorum (N=3), flagging elevated dispersion.',
      asset: 'XAU/USD (Tokenized Gold)',
      category: 'VALIDATOR_OUTAGE',
      p_osm_initial: 95.00,
      expected_market: 94.90,
      ltv_default: 0.60
    },
    {
      scenario_id: 'scen_slow_drift',
      title: 'Slow Cumulative Drift (Stealth Manipulation)',
      description: 'Adversary induces subtle price creep (+0.25% per tick) beneath single-tick thresholds. Lane 5 (Page CUSUM) accumulates sequential deviations in S+, tripping threshold h=4.0 with early warning.',
      asset: 'XAU/USD (Tokenized Gold)',
      category: 'SLOW_DRIFT',
      p_osm_initial: 95.00,
      expected_market: 98.20,
      ltv_default: 0.60
    },
    {
      scenario_id: 'scen_rwa_depeg',
      title: 'RWA Secondary Depeg (NAV Jump Divergence)',
      description: 'Secondary liquidity collapses by -9% while physical redemption anchor remains at $100.00. Lane 4 (Ornstein-Uhlenbeck) standardized spread residual exceeds diffusion bounds (|z| >= 3.5 under configured threshold), flagging a structural residual alert / jump candidate.',
      asset: 'PAXG / XAU (Tokenized Gold RWA)',
      category: 'RWA_DEPEG',
      p_osm_initial: 100.00,
      expected_market: 91.00,
      ltv_default: 0.60
    }
  ];
}

export async function runScenario(
  scenarioId: string,
  ltvFactor: number = 0.60,
  stepSeconds: number = 3600
): Promise<ScenarioRecord> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/scenarios/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario_id: scenarioId,
        ltv_factor: ltvFactor,
        step_seconds: stepSeconds,
        custom_seed: 42
      }),
      cache: 'no-store'
    });

    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Fallback deterministic local engine
  }

  return generateLocalScenarioRecord(scenarioId, ltvFactor, stepSeconds);
}

function generateLocalScenarioRecord(
  scenarioId: string,
  ltvFactor: number,
  stepSeconds: number
): ScenarioRecord {
  const isFinalized = stepSeconds >= 3600;
  const startTs = 1774000000;
  
  let pOsmVal = 95.20;
  let pMktVal = 95.15;
  let title = 'Normal Baseline Consensus (Stationary Market)';
  let desc = 'Stationary market conditions with tightly aligned multi-source inputs.';
  let isRwa = true;
  let anchorPrice = 95.20;

  if (scenarioId === 'scen_flash_spike' || scenarioId === 'scen_gold_osm_spike_01') {
    pOsmVal = 106.50;
    pMktVal = 95.00;
    title = 'Flash Spike Attack (Transient Upstream Anomaly)';
    desc = 'Single-block liquidity manipulation causes a sudden +12% price spike.';
  } else if (scenarioId === 'scen_poisoned_validator') {
    pOsmVal = 95.00;
    pMktVal = 95.10;
    title = 'Poisoned Validator Node (Adversarial Sybil Outlier)';
    desc = 'Validator Node 2 is compromised and submits a malicious +20% quote.';
  } else if (scenarioId === 'scen_validator_outage') {
    pOsmVal = 95.00;
    pMktVal = 94.90;
    title = 'Validator Infrastructure Outage (Quorum Stress)';
    desc = 'Network partition or infrastructure crash takes Nodes 4 and 5 offline.';
  } else if (scenarioId === 'scen_slow_drift') {
    pOsmVal = 95.00;
    pMktVal = 98.20;
    title = 'Slow Cumulative Drift (Stealth Manipulation)';
    desc = 'Adversary induces subtle price creep (+0.25% per tick) beneath single-tick thresholds.';
  } else if (scenarioId === 'scen_rwa_depeg') {
    pOsmVal = 100.00;
    pMktVal = 91.00;
    anchorPrice = 100.00;
    title = 'RWA Secondary Depeg (NAV Jump Divergence)';
    desc = 'Secondary liquidity collapses by -9% while physical redemption anchor remains at $100.00.';
  }

  // 5 Canonical Methodology Lanes
  const allValidators = [
    {
      validator_id: 'val-sim-1',
      lane_id: 'lane-1',
      operator_id: 'operator-alpha',
      role: 'PRICE_ESTIMATOR',
      is_price_estimator: true,
      methodology: 'KALMAN_INNOVATION_GATE',
      methodology_name: 'Recursive 1D Kalman Filter + Mahalanobis Innovation Gating',
      estimated_price: +(pMktVal - 0.05).toFixed(2),
      uncertainty_lower: +(pMktVal - 0.40).toFixed(2),
      uncertainty_upper: +(pMktVal + 0.40).toFixed(2),
      anomaly_score: scenarioId === 'scen_flash_spike' ? 0.95 : 0.05,
      decision: scenarioId === 'scen_flash_spike' ? 'INNOVATION_GATED' : 'OBSERVATION_ACCEPTED',
      reason_code: scenarioId === 'scen_flash_spike' ? 'MAHALANOBIS_GATE_TRIPPED' : 'INNOVATION_WITHIN_CHI2_BOUNDS',
      intermediate_metrics: {
        prior_state: 95.0,
        prior_covariance: 0.15,
        observation: scenarioId === 'scen_flash_spike' ? 106.50 : 95.10,
        innovation: scenarioId === 'scen_flash_spike' ? 11.50 : 0.10,
        innovation_variance: 0.25,
        kalman_gain: 0.60,
        posterior_state: +(pMktVal - 0.05).toFixed(2),
        posterior_covariance: 0.06,
        mahalanobis_d2: scenarioId === 'scen_flash_spike' ? 529.0 : 0.04,
        chi2_threshold: 6.635,
        alpha: 0.01,
        confidence_level: 0.99,
        gate_decision: scenarioId === 'scen_flash_spike' ? 'INNOVATION_GATED' : 'OBSERVATION_ACCEPTED',
        measurement_noise_r: 0.10,
        process_noise_q: 0.05
      },
      diagnostic_evidence: {
        is_accepted: scenarioId !== 'scen_flash_spike',
        mahalanobis_d2: scenarioId === 'scen_flash_spike' ? 529.0 : 0.04,
        chi2_threshold: 6.635,
        alpha: 0.01,
        confidence_level: 0.99,
      },
      status: 'SIMULATED' as const,
      strategy_id: 'strat-kalman-1d',
      strategy_name: 'Recursive 1D Kalman Filter + Mahalanobis Innovation Gating',
      observed_at: startTs + 900,
      source_ids: ['cex-binance-depth', 'coinbase-midpoint'],
      method_version: '1.0.0-stat'
    },
    {
      validator_id: 'val-sim-2',
      lane_id: 'lane-2',
      operator_id: 'operator-beta',
      role: 'PRICE_ESTIMATOR',
      is_price_estimator: true,
      methodology: 'HUBER_IRLS',
      methodology_name: 'Huber M-Estimation via Iteratively Reweighted Least Squares (IRLS)',
      estimated_price: scenarioId === 'scen_poisoned_validator' ? +(pMktVal * 1.20).toFixed(2) : +(pMktVal + 0.02).toFixed(2),
      uncertainty_lower: +(pMktVal - 0.35).toFixed(2),
      uncertainty_upper: +(pMktVal + 0.35).toFixed(2),
      anomaly_score: scenarioId === 'scen_poisoned_validator' ? 0.90 : 0.05,
      decision: scenarioId === 'scen_poisoned_validator' ? 'POISONED_OUTLIER_INJECTED' : 'ROBUST_LOCATION_CONVERGED',
      reason_code: scenarioId === 'scen_poisoned_validator' ? 'SYBIL_CORRUPTION_SIMULATED' : 'GAUSSIAN_EFFICIENCY_MAINTAINED',
      intermediate_metrics: {
        raw_observations: [pMktVal, pMktVal + 0.05, pMktVal - 0.05, pMktVal + 0.02, scenarioId === 'scen_poisoned_validator' ? pMktVal * 1.20 : pMktVal],
        initial_median: pMktVal,
        mad: 0.05,
        scale_s: 0.074,
        huber_k: 1.345,
        iterations: 3,
        converged: true,
        weights_table: [
          { price: pMktVal, residual: 0.0, std_residual: 0.0, weight: 1.0, is_outlier: false },
          { price: +(pMktVal + 0.05).toFixed(2), residual: 0.05, std_residual: 0.67, weight: 1.0, is_outlier: false },
          { price: +(pMktVal - 0.05).toFixed(2), residual: -0.05, std_residual: -0.67, weight: 1.0, is_outlier: false },
          { price: +(pMktVal + 0.02).toFixed(2), residual: 0.02, std_residual: 0.27, weight: 1.0, is_outlier: false },
          { price: scenarioId === 'scen_poisoned_validator' ? +(pMktVal * 1.20).toFixed(2) : pMktVal, residual: scenarioId === 'scen_poisoned_validator' ? 19.0 : 0.0, std_residual: scenarioId === 'scen_poisoned_validator' ? 256.0 : 0.0, weight: scenarioId === 'scen_poisoned_validator' ? 0.005 : 1.0, is_outlier: scenarioId === 'scen_poisoned_validator' }
        ],
        final_estimate: +(pMktVal + 0.01).toFixed(2),
        robust_dispersion: 0.074,
        standard_error: 0.035,
        outlier_count: scenarioId === 'scen_poisoned_validator' ? 1 : 0
      },
      diagnostic_evidence: {
        outlier_count: scenarioId === 'scen_poisoned_validator' ? 1 : 0,
        scale_s: 0.074,
        converged: true,
      },
      status: 'SIMULATED' as const,
      strategy_id: 'strat-huber-irls',
      strategy_name: 'Huber M-Estimation via IRLS',
      observed_at: startTs + 1800,
      source_ids: ['dex-uniswap-v3-pool', 'curve-tricrypto-feed'],
      method_version: '1.0.0-stat'
    },
    {
      validator_id: 'val-sim-3',
      lane_id: 'lane-3',
      operator_id: 'operator-gamma',
      role: 'UNCERTAINTY_CONSENSUS_MEASURE',
      is_price_estimator: false,
      methodology: 'JENSEN_SHANNON_DIVERGENCE',
      methodology_name: 'Pairwise Jensen-Shannon Divergence Matrix Analysis',
      estimated_price: null,
      uncertainty_lower: null,
      uncertainty_upper: null,
      anomaly_score: scenarioId === 'scen_poisoned_validator' ? 0.65 : 0.05,
      decision: scenarioId === 'scen_poisoned_validator' ? 'INFORMATIONAL_DISAGREEMENT' : 'INFORMATIONAL_CONSENSUS',
      reason_code: scenarioId === 'scen_poisoned_validator' ? 'LANE_OUTLIER_DIVERGENCE_DETECTED' : 'UNIFORM_CONSENSUS_ENTROPY',
      intermediate_metrics: {
        pairwise_jsd_matrix: [
          [0.0, 0.01, 0.01, 0.02, 0.01],
          [0.01, 0.0, 0.01, 0.02, 0.01],
          [0.01, 0.01, 0.0, 0.02, 0.01],
          [0.02, 0.02, 0.02, 0.0, 0.02],
          [0.01, 0.01, 0.01, 0.02, 0.0]
        ],
        mean_divergence_per_lane: {
          'lane-1': 0.012,
          'lane-2': scenarioId === 'scen_poisoned_validator' ? 0.48 : 0.012,
          'lane-3': 0.014,
          'lane-4': 0.018,
          'lane-5': 0.015
        },
        lane_weights: {
          'lane-1': 0.22,
          'lane-2': scenarioId === 'scen_poisoned_validator' ? 0.02 : 0.21,
          'lane-3': 0.21,
          'lane-4': 0.18,
          'lane-5': 0.20
        },
        divergent_lanes: scenarioId === 'scen_poisoned_validator' ? ['lane-2'] : [],
        informational_disagreement: scenarioId === 'scen_poisoned_validator' ? 0.32 : 0.015,
        grid_bins: 100,
        lane_ids: ['lane-1', 'lane-2', 'lane-3', 'lane-4', 'lane-5']
      },
      diagnostic_evidence: {
        informational_disagreement: scenarioId === 'scen_poisoned_validator' ? 0.32 : 0.015,
        consensus_price_hint: +(pMktVal - 0.02).toFixed(2),
        divergent_lanes: scenarioId === 'scen_poisoned_validator' ? ['lane-2'] : [],
      },
      status: 'SIMULATED' as const,
      strategy_id: 'strat-jsd-divergence',
      strategy_name: 'Pairwise Jensen-Shannon Divergence Matrix Analysis',
      observed_at: startTs + 2400,
      source_ids: ['aggregated-validator-distributions'],
      method_version: '1.0.0-stat'
    },
    {
      validator_id: 'val-sim-4',
      lane_id: 'lane-4',
      operator_id: 'operator-delta',
      role: 'RWA_STRUCTURAL_CHECK',
      is_price_estimator: false,
      methodology: 'ORNSTEIN_UHLENBECK_RWA',
      methodology_name: 'Ornstein-Uhlenbeck RWA Residual / Jump-Diffusion Analysis',
      estimated_price: null,
      uncertainty_lower: null,
      uncertainty_upper: null,
      anomaly_score: scenarioId === 'scen_rwa_depeg' ? 0.95 : 0.05,
      decision: scenarioId === 'scen_rwa_depeg' ? 'DIFFUSION_MODEL_INCONSISTENCY' : 'DIFFUSION_CONSISTENT',
      reason_code: scenarioId === 'scen_rwa_depeg' ? 'STRUCTURAL_RESIDUAL_ALERT' : 'OU_SPREAD_EQUILIBRIUM',
      intermediate_metrics: {
        is_rwa: isRwa,
        has_anchor: true,
        is_applicable: isRwa,
        spot_price: pMktVal,
        anchor_price: anchorPrice,
        log_spread: Math.log(pMktVal / anchorPrice),
        theta: 0.15,
        mu: 0.0,
        sigma: 0.02,
        dt: 1.0,
        expected_spread: 0.0,
        conditional_variance: 0.0003,
        conditional_std: 0.0173,
        standardized_residual: scenarioId === 'scen_rwa_depeg' ? -5.44 : -0.12,
        jump_threshold: 3.5,
        is_jump_candidate: scenarioId === 'scen_rwa_depeg',
        jump_candidate: scenarioId === 'scen_rwa_depeg',
        not_applicable_reason: null
      },
      diagnostic_evidence: {
        is_applicable: isRwa,
        spot_price: pMktVal,
        anchor_price: anchorPrice,
        standardized_residual: scenarioId === 'scen_rwa_depeg' ? -5.44 : -0.12,
        jump_threshold: 3.5,
        jump_candidate: scenarioId === 'scen_rwa_depeg',
      },
      status: 'SIMULATED' as const,
      strategy_id: 'strat-ou-rwa-jump',
      strategy_name: 'Ornstein-Uhlenbeck RWA Residual / Jump-Diffusion Analysis',
      observed_at: startTs + 2700,
      source_ids: ['paxg-clob-orderbook', 'custodian-nav-attestation'],
      method_version: '1.0.0-stat'
    },
    {
      validator_id: 'val-sim-5',
      lane_id: 'lane-5',
      operator_id: 'operator-epsilon',
      role: 'SEQUENTIAL_DRIFT_DETECTOR',
      is_price_estimator: false,
      methodology: 'PAGE_CUSUM_DRIFT',
      methodology_name: 'Page CUSUM Sequential Drift Detection Filter',
      estimated_price: null,
      uncertainty_lower: null,
      uncertainty_upper: null,
      anomaly_score: scenarioId === 'scen_slow_drift' ? 0.85 : 0.05,
      decision: scenarioId === 'scen_slow_drift' ? 'PERSISTENT_DRIFT_ALERT' : 'DRIFT_ABSENT_STABLE',
      reason_code: scenarioId === 'scen_slow_drift' ? 'CUSUM_UPWARD_ACCUMULATOR_TRIPPED' : 'ACCUMULATOR_BELOW_DECISION_INTERVAL',
      intermediate_metrics: {
        current_price: pMktVal,
        tick_volatility: 0.35,
        baseline_std: 0.35,
        standardized_increment: scenarioId === 'scen_slow_drift' ? 1.45 : 0.15,
        current_increment: scenarioId === 'scen_slow_drift' ? 1.45 : 0.15,
        s_pos: scenarioId === 'scen_slow_drift' ? 4.82 : 0.0,
        s_neg: 0.0,
        s_plus: scenarioId === 'scen_slow_drift' ? 4.82 : 0.0,
        s_minus: 0.0,
        drift_kappa: 0.5,
        kappa: 0.5,
        threshold_h: 4.0,
        drift_detected: scenarioId === 'scen_slow_drift',
        history_length: 24,
        recent_trajectory: [0.0, 0.2, 0.5, 1.1, 1.8, 2.4, 3.1, 3.9, scenarioId === 'scen_slow_drift' ? 4.82 : 0.0]
      },
      diagnostic_evidence: {
        s_pos: scenarioId === 'scen_slow_drift' ? 4.82 : 0.0,
        s_plus: scenarioId === 'scen_slow_drift' ? 4.82 : 0.0,
        threshold_h: 4.0,
        drift_detected: scenarioId === 'scen_slow_drift',
        tick_volatility: 0.35,
        standardized_increment: scenarioId === 'scen_slow_drift' ? 1.45 : 0.15,
      },
      status: 'SIMULATED' as const,
      strategy_id: 'strat-cusum-drift',
      strategy_name: 'Page CUSUM Sequential Drift Detection Filter',
      observed_at: startTs + 3000,
      source_ids: ['tick-history-kraken', 'tick-history-binance'],
      method_version: '1.0.0-stat'
    }
  ];

  // In outage scenario, Nodes 4 and 5 are down
  const activeValidators = scenarioId === 'scen_validator_outage'
    ? allValidators.slice(0, 3)
    : allValidators;

  const visibleValidators = activeValidators.filter(v => v.observed_at <= startTs + stepSeconds);
  const priceEstimators = visibleValidators.filter(v => v.is_price_estimator && v.estimated_price !== null && !v.decision.includes('GATED'));
  const pDecVal = priceEstimators.length > 0 
    ? +(priceEstimators.reduce((sum, v) => sum + (v.estimated_price || 0), 0) / priceEstimators.length).toFixed(2)
    : (visibleValidators.length >= 2 ? +(pMktVal - 0.02).toFixed(2) : null);

  const dOsmMkt = isFinalized ? +(Math.abs(pOsmVal - pMktVal) / pMktVal).toFixed(4) : null;
  const dDecMkt = (isFinalized && pDecVal) ? +(Math.abs(pDecVal - pMktVal) / pMktVal).toFixed(4) : null;
  const dOsmDec = pDecVal ? +(Math.abs(pOsmVal - pDecVal) / pDecVal).toFixed(4) : null;

  const isHealthy = scenarioId === 'scen_normal_consensus' || scenarioId === 'scen_gold_healthy_consensus_02';
  const oracleStatus = isHealthy ? 'HEALTHY_CONSENSUS' : 'SUSPECTED_INCONSISTENCY';
  const finalPrice = isFinalized ? (isHealthy ? pOsmVal : (pDecVal || pMktVal)) : null;

  const baselineCollat = +(pOsmVal * ltvFactor).toFixed(2);
  const aegisCollat = finalPrice ? +(finalPrice * ltvFactor).toFixed(2) : null;
  const diffCollat = aegisCollat !== null ? +(baselineCollat - aegisCollat).toFixed(2) : null;

  return {
    scenario_id: scenarioId,
    title,
    description: desc,
    asset: scenarioId === 'scen_rwa_depeg' ? 'PAXG / XAU (Tokenized Gold RWA)' : 'XAU/USD (Tokenized Gold)',
    window: {
      start_ts: startTs,
      end_ts: startTs + 3600,
      duration_seconds: 3600,
      elapsed_seconds: stepSeconds,
      is_finalized: isFinalized
    },
    p_osm: {
      value: pOsmVal,
      timestamp: startTs,
      source: 'multipli_osm_mock',
      status: 'SIMULATED'
    },
    validators: visibleValidators,
    p_dec: {
      value: pDecVal,
      aggregation: 'median_uncertainty_weighted',
      validator_count: visibleValidators.length,
      dispersion: scenarioId === 'scen_validator_outage' ? 0.028 : 0.0065,
      quorum_met: visibleValidators.length >= 3,
      status: 'SIMULATED',
      eligible_lane_ids: visibleValidators.filter(v => v.is_price_estimator).map(v => v.lane_id),
      lane_estimates: Object.fromEntries(visibleValidators.map(v => [v.lane_id, v.estimated_price]))
    },
    p_market: {
      value: isFinalized ? pMktVal : null,
      timestamp: isFinalized ? startTs + 3600 : null,
      source: 'simulated_binance_adapter',
      status: isFinalized ? 'SIMULATED' : 'PENDING',
      symbol: 'XAU/USD',
      is_offchain: true
    },
    evidence: {
      d_osm_market: dOsmMkt,
      d_dec_market: dDecMkt,
      d_osm_dec: dOsmDec,
      validator_dispersion: scenarioId === 'scen_validator_outage' ? 0.028 : 0.0065,
      agreement_ratio: visibleValidators.length / 5.0,
      oracle_status: isFinalized ? oracleStatus : 'PENDING_FINALIZATION',
      anomaly_score: isHealthy ? 0.05 : 0.78,
      reason_codes: isHealthy
        ? ['CONSISTENT_ORACLE_ALIGNMENT', 'STRONG_VALIDATOR_QUORUM_AGREEMENT']
        : ['OSM_DEVIATION_EXCEEDS_HIGH_THRESHOLD', 'VALIDATOR_REFERENCE_ALIGNED_WITH_MARKET'],
      lane_anomalies: {
        'lane-1': scenarioId === 'scen_flash_spike',
        'lane-2': scenarioId === 'scen_poisoned_validator',
        'lane-3': false,
        'lane-4': scenarioId === 'scen_rwa_depeg',
        'lane-5': scenarioId === 'scen_slow_drift'
      },
      conflict_indicators: {
        'osm_dec_divergence': (dOsmDec || 0) > 0.03,
        'osm_market_divergence': (dOsmMkt || 0) > 0.03,
        'dec_market_divergence': (dDecMkt || 0) > 0.03
      }
    },
    decision: {
      policy: isHealthy ? 'USE_OSM' : 'ROBUST_MEDIAN',
      decision: isHealthy ? 'VERIFIED' : 'RESTRICTED',
      final_price: finalPrice,
      selected_source: isHealthy ? 'P_OSM' : 'P_DEC',
      confidence: isHealthy ? 0.96 : 0.88,
      reason_codes: isHealthy ? ['OSM_CONSISTENCY_CONFIRMED'] : ['SUBSTITUTED_INCONSISTENT_OSM_WITH_DEC_REFERENCE'],
      policy_version: '0.2.0-stat-defense'
    },
    collateral: {
      ltv: ltvFactor,
      baseline_value: baselineCollat,
      aegis_value: aegisCollat,
      difference: diffCollat,
      risk_exposure_pct: diffCollat && diffCollat > 0 ? +((diffCollat / baselineCollat) * 100).toFixed(2) : 0,
      protected_capital: diffCollat && diffCollat > 0 ? diffCollat : 0
    }
  };
}
