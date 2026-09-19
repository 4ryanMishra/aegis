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
      scenario_id: 'scen_gold_osm_spike_01',
      title: 'Gold RWA — Stale / Manipulated OSM Spike',
      description: 'Baseline OSM pushes an anomalous $100.00 valuation at T0. 4 independent validator strategies converge around $93.00. At T1, market settles at $95.00, exposing a +5.26% OSM overstatement.',
      asset: 'XAU/USD (Tokenized Gold)',
      category: 'OSM_SPIKE',
      p_osm_initial: 100.0,
      expected_market: 95.0,
      ltv_default: 0.60
    },
    {
      scenario_id: 'scen_gold_healthy_consensus_02',
      title: 'Gold RWA — Healthy Multi-Source Consensus',
      description: 'Normal market conditions. Baseline OSM queues $95.20. Independent validators forecast between $94.90 and $95.30 (median $95.10). Market settles at $95.15.',
      asset: 'XAU/USD (Tokenized Gold)',
      category: 'HEALTHY',
      p_osm_initial: 95.2,
      expected_market: 95.15,
      ltv_default: 0.60
    },
    {
      scenario_id: 'scen_gold_high_volatility_03',
      title: 'Gold RWA — Intraday Flash Crash (Market Real-Move)',
      description: 'Macro liquidity event. OSM enters window at $98.00. Rapid validator updates capture falling prices at $88.50. Market settles at $88.00.',
      asset: 'XAU/USD (Tokenized Gold)',
      category: 'HIGH_VOLATILITY',
      p_osm_initial: 98.0,
      expected_market: 88.0,
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
  
  let pOsmVal = 100.0;
  let pMktVal = 95.0;
  let title = 'Gold RWA — Stale / Manipulated OSM Spike';
  let desc = 'Baseline OSM pushes an anomalous $100.00 valuation at T0.';

  if (scenarioId === 'scen_gold_healthy_consensus_02') {
    pOsmVal = 95.2;
    pMktVal = 95.15;
    title = 'Gold RWA — Healthy Multi-Source Consensus';
    desc = 'Normal market conditions with tightly aligned multi-source inputs.';
  } else if (scenarioId === 'scen_gold_high_volatility_03') {
    pOsmVal = 98.0;
    pMktVal = 88.0;
    title = 'Gold RWA — Intraday Flash Crash (Market Real-Move)';
    desc = 'Macro liquidity shock causing genuine spot divergence from stale OSM.';
  }

  const allValidators = [
    {
      validator_id: 'val_alpha',
      strategy_id: 'strat_mean_reversion_placeholder',
      strategy_name: 'Statistical Mean-Reversion Model (Placeholder)',
      estimated_price: +(pMktVal - 0.20).toFixed(2),
      uncertainty_lower: +(pMktVal - 1.80).toFixed(2),
      uncertainty_upper: +(pMktVal + 1.60).toFixed(2),
      observed_at: startTs + 900,
      source_ids: ['sim_orderbook_depth_feed_a', 'sim_historical_ticks_b'],
      method_version: '0.1.0-alpha',
      status: 'SIMULATED' as const
    },
    {
      validator_id: 'val_beta',
      strategy_id: 'strat_momentum_trend_placeholder',
      strategy_name: 'Order-Flow Momentum Indicator (Placeholder)',
      estimated_price: +(pMktVal + 0.10).toFixed(2),
      uncertainty_lower: +(pMktVal - 2.10).toFixed(2),
      uncertainty_upper: +(pMktVal + 1.90).toFixed(2),
      observed_at: startTs + 1800,
      source_ids: ['sim_cex_order_flow_c', 'sim_deriv_funding_rate_d'],
      method_version: '0.1.0-alpha',
      status: 'SIMULATED' as const
    },
    {
      validator_id: 'val_gamma',
      strategy_id: 'strat_cross_dex_vwap_placeholder',
      strategy_name: 'Cross-DEX Multi-Pool VWAP (Placeholder)',
      estimated_price: +(pMktVal - 0.15).toFixed(2),
      uncertainty_lower: +(pMktVal - 1.40).toFixed(2),
      uncertainty_upper: +(pMktVal + 1.50).toFixed(2),
      observed_at: startTs + 2400,
      source_ids: ['sim_uniswap_v3_pool_e', 'sim_curve_pool_f'],
      method_version: '0.1.0-alpha',
      status: 'SIMULATED' as const
    },
    {
      validator_id: 'val_delta',
      strategy_id: 'strat_robust_dispersion_placeholder',
      strategy_name: 'Trimmed Inter-Venue Dispersion Filter (Placeholder)',
      estimated_price: +(pMktVal + 0.05).toFixed(2),
      uncertainty_lower: +(pMktVal - 1.30).toFixed(2),
      uncertainty_upper: +(pMktVal + 1.40).toFixed(2),
      observed_at: startTs + 2700,
      source_ids: ['sim_lmax_feed_h', 'sim_kraken_feed_i'],
      method_version: '0.1.0-alpha',
      status: 'SIMULATED' as const
    }
  ];

  const visibleValidators = allValidators.filter(v => v.observed_at <= startTs + stepSeconds);
  const pDecVal = visibleValidators.length >= 3 ? +(pMktVal - 0.05).toFixed(2) : null;

  const dOsmMkt = isFinalized ? +(Math.abs(pOsmVal - pMktVal) / pMktVal).toFixed(4) : null;
  const dDecMkt = (isFinalized && pDecVal) ? +(Math.abs(pDecVal - pMktVal) / pMktVal).toFixed(4) : null;
  const dOsmDec = pDecVal ? +(Math.abs(pOsmVal - pDecVal) / pDecVal).toFixed(4) : null;

  const isHealthy = scenarioId === 'scen_gold_healthy_consensus_02';
  const oracleStatus = isHealthy ? 'HEALTHY_CONSENSUS' : 'SUSPECTED_INCONSISTENCY';
  const finalPrice = isFinalized ? (isHealthy ? pOsmVal : (pDecVal || pMktVal)) : null;

  const baselineCollat = +(pOsmVal * ltvFactor).toFixed(2);
  const aegisCollat = finalPrice ? +(finalPrice * ltvFactor).toFixed(2) : null;
  const diffCollat = aegisCollat !== null ? +(baselineCollat - aegisCollat).toFixed(2) : null;

  return {
    scenario_id: scenarioId,
    title,
    description: desc,
    asset: 'XAU/USD (Tokenized Gold)',
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
      aggregation: 'median',
      validator_count: visibleValidators.length,
      dispersion: 0.0085,
      quorum_met: visibleValidators.length >= 3,
      status: 'SIMULATED'
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
      validator_dispersion: 0.0085,
      agreement_ratio: 1.0,
      oracle_status: isFinalized ? oracleStatus : 'PENDING_FINALIZATION',
      anomaly_score: isHealthy ? 0.05 : 0.74,
      reason_codes: isHealthy
        ? ['CONSISTENT_ORACLE_ALIGNMENT', 'STRONG_VALIDATOR_QUORUM_AGREEMENT']
        : ['OSM_DEVIATION_EXCEEDS_HIGH_THRESHOLD', 'VALIDATOR_REFERENCE_ALIGNED_WITH_MARKET']
    },
    decision: {
      policy: 'NEAREST_TO_MARKET',
      final_price: finalPrice,
      selected_source: isHealthy ? 'P_OSM' : 'P_DEC',
      confidence: isHealthy ? 0.96 : 0.88,
      reason_codes: isHealthy ? ['OSM_CONSISTENCY_CONFIRMED'] : ['SUBSTITUTED_INCONSISTENT_OSM_WITH_DEC_REFERENCE'],
      policy_version: '0.1.0-mvp'
    },
    collateral: {
      ltv: ltvFactor,
      baseline_value: baselineCollat,
      aegis_value: aegisCollat,
      difference: diffCollat,
      risk_exposure_pct: diffCollat && diffCollat > 0 ? +((diffCollat / baselineCollat) * 100).toFixed(2) : 0
    }
  };
}
