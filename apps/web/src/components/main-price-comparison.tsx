import React from 'react';
import { SimulationSnapshot } from '@/lib/types';
import { 
  AlertTriangle, 
  CheckCircle2, 
  Layers, 
  Lock, 
  Activity, 
  ShieldCheck, 
  ShieldAlert,
  Clock,
  Coins
} from 'lucide-react';

interface MainPriceComparisonProps {
  snapshot: SimulationSnapshot;
  onInspectTarget?: (target: string) => void;
}

export const MainPriceComparison: React.FC<MainPriceComparisonProps> = ({
  snapshot,
  onInspectTarget,
}) => {
  const multipli = snapshot.multipli_observation;
  const consensus = snapshot.consensus;
  const market = snapshot.market_observation;
  const decision = snapshot.decision;

  const isHealthy = decision.state === 'HEALTHY_CONSENSUS';
  const isDeviation = decision.state === 'MULTIPLI_DEVIATION';
  const isHalted = decision.state === 'NO_CONSENSUS' || decision.protocol_state === 'HALTED';
  const isDegraded = decision.state === 'SOURCE_DEGRADED' || decision.state === 'ORACLE_INSTABILITY';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      
      {/* 1. Multipli OSM Price */}
      <div 
        onClick={() => onInspectTarget && onInspectTarget('MULTIPLI')}
        className="bg-surface border border-borderHairline hover:border-purple-400 p-4 rounded shadow-card cursor-pointer transition relative group"
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-purple-700">1. MULTIPLI OSM</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 font-semibold">
            {multipli?.price && multipli.price > 0 ? (isDeviation ? 'STALE / DELAYED' : '1-HR BUFFER') : 'UNAVAILABLE'}
          </span>
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {multipli?.price && multipli.price > 0 ? `$${multipli.price.toFixed(2)}` : '$0.00'}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-purple-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Target Oracle Feed</span>
          <span className="font-mono text-purple-800 font-medium">OSM Protected</span>
        </div>
      </div>

      {/* 2. Cross-Oracle Consensus */}
      <div 
        onClick={() => onInspectTarget && onInspectTarget('CONSENSUS')}
        className="bg-surface border border-borderHairline hover:border-blue-400 p-4 rounded shadow-card cursor-pointer transition relative group"
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-blue-600">2. ORACLE CONSENSUS</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            {consensus.cluster_size} FEEDS AGREE
          </span>
        </div>
        <div className="flex items-baseline justify-between">
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-mono font-bold text-blue-700 tnum">
              {consensus.consensus_price !== null && consensus.consensus_price > 0 
                ? `$${consensus.consensus_price.toFixed(2)}` 
                : 'No Consensus'}
            </span>
            {consensus.consensus_price !== null && (
              <span className="text-[11px] font-mono text-blue-500 font-medium">
                ({consensus.cluster_spread_pct.toFixed(2)}% spr)
              </span>
            )}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-blue-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Chainlink, Pyth, +4 More</span>
          <span className="font-mono text-blue-600 font-medium">Agreement Band &le;0.5%</span>
        </div>
      </div>

      {/* 3. Real-Time Spot Reference */}
      <div 
        onClick={() => onInspectTarget && onInspectTarget('MARKET')}
        className="bg-surface border border-borderHairline hover:border-amber-400 p-4 rounded shadow-card cursor-pointer transition relative group"
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-amber-700">3. SPOT REFERENCE</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
            REAL-TIME CLOB
          </span>
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {market?.price !== null && market?.price !== undefined ? `$${market.price.toFixed(2)}` : 'Streaming...'}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-amber-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>External Spot Market</span>
          <span className="font-mono text-slate-700">Instant Execution</span>
        </div>
      </div>

      {/* 4. AEGIS Authoritative Final Valuation */}
      <div 
        onClick={() => onInspectTarget && onInspectTarget('DECISION')}
        className={`bg-surface border p-4 rounded shadow-card cursor-pointer transition relative group ${
          isHalted
            ? 'border-rose-400 bg-rose-50/20'
            : isDeviation
            ? 'border-amber-400 bg-amber-50/20'
            : isDegraded
            ? 'border-amber-400 bg-amber-50/20'
            : isHealthy
            ? 'border-emerald-400 bg-emerald-50/20'
            : 'border-borderHairline'
        }`}
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-slate-900">4. AEGIS VALUATION</span>
          {isHalted ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300">
              <Lock className="w-3 h-3 text-rose-600" />
              HALTED
            </span>
          ) : isDeviation ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
              <AlertTriangle className="w-3 h-3 text-amber-600" />
              CONSERVATIVE MIN
            </span>
          ) : isDegraded ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
              <AlertTriangle className="w-3 h-3 text-amber-600" />
              RESTRICTED
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              HEALTHY
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {decision.final_price !== null ? `$${decision.final_price.toFixed(2)}` : 'Computing...'}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-slate-700 font-medium transition">
            Audit &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
          <span className="text-slate-500 font-mono">
            {decision.is_conservative_applied ? 'min(OSM, Consensus)' : 'Standard Valuation'}
          </span>
          <span className={`font-mono font-bold ${
            isHalted ? 'text-rose-700' : isDeviation ? 'text-amber-700' : 'text-emerald-700'
          }`}>
            {(decision.effective_ltv * 100).toFixed(0)}% LTV Cap
          </span>
        </div>
      </div>

    </div>
  );
};
