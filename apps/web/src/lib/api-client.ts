import { ScenarioRecord, ScenarioListItem, SimulationSnapshot, OracleObservation, ConsensusResult, RiskDecisionResult, UserPositionState } from './types';

// Use relative path in browser for Next.js proxy rewrite, or direct backend port
const API_BASE_URL = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000');

export async function fetchSimulationState(): Promise<SimulationSnapshot> {
  const urls = [
    `${API_BASE_URL}/api/simulation/state`,
    'http://127.0.0.1:8000/api/simulation/state',
    'http://localhost:8000/api/simulation/state'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Try next endpoint fallback
    }
  }
  throw new Error('Failed to fetch simulation state from AEGIS backend');
}

export async function startSimulation(): Promise<SimulationSnapshot> {
  const urls = [
    `${API_BASE_URL}/api/simulation/start`,
    'http://127.0.0.1:8000/api/simulation/start',
    'http://localhost:8000/api/simulation/start'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, { method: 'POST', cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        return data.state;
      }
    } catch {}
  }
  throw new Error('Failed to start simulation');
}

export async function pauseSimulation(): Promise<SimulationSnapshot> {
  const urls = [
    `${API_BASE_URL}/api/simulation/pause`,
    'http://127.0.0.1:8000/api/simulation/pause',
    'http://localhost:8000/api/simulation/pause'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, { method: 'POST', cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        return data.state;
      }
    } catch {}
  }
  throw new Error('Failed to pause simulation');
}

export async function resetSimulation(scenarioId?: string, ltv?: number, seed?: number): Promise<SimulationSnapshot> {
  const urls = [
    `${API_BASE_URL}/api/simulation/reset`,
    'http://127.0.0.1:8000/api/simulation/reset',
    'http://localhost:8000/api/simulation/reset'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_id: scenarioId, ltv_factor: ltv, seed: seed || 42 }),
        cache: 'no-store'
      });
      if (res.ok) {
        const data = await res.json();
        return data.state;
      }
    } catch {}
  }
  throw new Error('Failed to reset simulation');
}

export async function stepSimulation(deltaSeconds: number = 600.0): Promise<SimulationSnapshot> {
  const urls = [
    `${API_BASE_URL}/api/simulation/step`,
    'http://127.0.0.1:8000/api/simulation/step',
    'http://localhost:8000/api/simulation/step'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delta_seconds: deltaSeconds }),
        cache: 'no-store'
      });
      if (res.ok) {
        const data = await res.json();
        return data.state;
      }
    } catch {}
  }
  throw new Error('Failed to step simulation');
}

export async function finalizeSimulation(): Promise<SimulationSnapshot> {
  const urls = [
    `${API_BASE_URL}/api/simulation/finalize`,
    'http://127.0.0.1:8000/api/simulation/finalize',
    'http://localhost:8000/api/simulation/finalize'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, { method: 'POST', cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        return data.state;
      }
    } catch {}
  }
  throw new Error('Failed to finalize simulation');
}

export async function configSimulation(speedMultiplier?: number, scenarioId?: string, ltv?: number): Promise<SimulationSnapshot> {
  const urls = [
    `${API_BASE_URL}/api/simulation/config`,
    'http://127.0.0.1:8000/api/simulation/config',
    'http://localhost:8000/api/simulation/config'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed_multiplier: speedMultiplier, scenario_id: scenarioId, ltv_factor: ltv }),
        cache: 'no-store'
      });
      if (res.ok) {
        const data = await res.json();
        return data.state;
      }
    } catch {}
  }
  throw new Error('Failed to configure simulation');
}

export async function updateSimulationPosition(
  collateralAmount?: number,
  debtAmount?: number,
  setMaxBorrow: boolean = false
): Promise<SimulationSnapshot> {
  const urls = [
    `${API_BASE_URL}/api/simulation/position`,
    'http://127.0.0.1:8000/api/simulation/position',
    'http://localhost:8000/api/simulation/position'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          collateral_amount: collateralAmount,
          debt_amount: debtAmount,
          set_max_borrow: setMaxBorrow,
        }),
        cache: 'no-store'
      });
      if (res.ok) {
        const data = await res.json();
        return data.state;
      }
    } catch {}
  }
  throw new Error('Failed to update simulation position');
}

export async function fetchScenarios(): Promise<ScenarioListItem[]> {
  const urls = [
    `${API_BASE_URL}/api/scenarios`,
    'http://127.0.0.1:8000/api/scenarios',
    'http://localhost:8000/api/scenarios'
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Try next endpoint fallback
    }
  }

  return [
    {
      scenario_id: 'scen_normal',
      title: 'Scenario A: Normal Operation (Multi-Oracle Agreement)',
      description: 'Multipli OSM ($4,050.00) and 6 on-chain oracle networks agree within ±0.03% (median $4,050.15). Healthy consensus verified, standard 80% LTV applied.',
      asset: 'Tokenized Gold (XAU/USD)',
      category: 'NORMAL',
      p_osm_initial: 4050.00,
      expected_market: 4050.00,
      ltv_default: 0.80
    },
    {
      scenario_id: 'scen_flash_crash',
      title: 'Scenario B: Multipli Delay During Fast Market Drop',
      description: 'Spot gold crashes 7.5% from $4,380 to $4,050. External oracles instantly reflect $4,050.85 while Multipli OSM is delayed at $4,380. AEGIS enforces min(P_OSM, P_CONSENSUS)=$4,050.85 and caps LTV at 50%, preventing bad debt.',
      asset: 'Tokenized Gold (XAU/USD)',
      category: 'FLASH_CRASH',
      p_osm_initial: 4380.00,
      expected_market: 4050.00,
      ltv_default: 0.80
    },
    {
      scenario_id: 'scen_poisoned_validator',
      title: 'Scenario C: Single Oracle Outlier Isolation (Sybil / Glitch)',
      description: 'An individual oracle feed glitches to an extreme $4,850.00. Deterministic price-band clustering excludes the outlier, maintaining robust consensus at $4,050.15.',
      asset: 'Tokenized Gold (XAU/USD)',
      category: 'POISONED_VALIDATOR',
      p_osm_initial: 4050.00,
      expected_market: 4050.00,
      ltv_default: 0.80
    },
    {
      scenario_id: 'scen_market_dislocation',
      title: 'Scenario D: Extreme Multi-Oracle Disagreement (Market Crisis)',
      description: 'Severe market disruption causes widespread oracle fragmentation ($3,800 to $4,200). No 3+ source cluster within 0.5% tolerance exists. AEGIS activates protective circuit breaker (HALT).',
      asset: 'Tokenized Gold (XAU/USD)',
      category: 'MARKET_DISLOCATION',
      p_osm_initial: 4050.00,
      expected_market: 4000.00,
      ltv_default: 0.80
    },
    {
      scenario_id: 'scen_osm_failure',
      title: 'Scenario E: Multipli Feed Degradation / Stale Feed',
      description: 'Multipli OSM feed becomes stale (>3,600s) or unavailable ($0.00). AEGIS falls back seamlessly to multi-oracle consensus ($4,050.10) under conservative 60% LTV.',
      asset: 'Tokenized Gold (XAU/USD)',
      category: 'OSM_FAILURE',
      p_osm_initial: 0.00,
      expected_market: 4050.00,
      ltv_default: 0.80
    }
  ];
}
