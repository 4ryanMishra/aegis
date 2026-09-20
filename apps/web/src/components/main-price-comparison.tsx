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

  const protocolState = decision.protocol_state || 'NORMAL';
  const isHalted = protocolState === 'HALTED' || decision.state === 'ORACLE_INSTABILITY' || decision.state === 'NO_CONSENSUS';
  const isRestricted = protocolState === 'RESTRICTED' || decision.state === 'MULTIPLI_DEVIATION' || decision.state === 'MARKET_CORROBORATED';
  const isNormal = protocolState === 'NORMAL' && !isHalted && !isRestricted;

  const isMultipliOutside = decision.multipli_deviation_pct > 0.50 || decision.state === 'MULTIPLI_DEVIATION';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      
      {/* 1. Multipli OSM Price Card */}
      <div 
        onClick={() => onInspectTarget && onInspectTarget('MULTIPLI')}
        className={`bg-surface border p-4 rounded shadow-card cursor-pointer transition relative group ${
          isMultipliOutside ? 'border-amber-300 hover:border-amber-400 bg-amber-50/10' : 'border-borderHairline hover:border-purple-400'
        }`}
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-purple-700">1. MULTIPLI OSM</span>
          {isHalted ? (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300 font-bold">
              DISLOCATED
            </span>
          ) : isMultipliOutside ? (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 font-bold">
              OUTSIDE CONSENSUS (+{decision.multipli_deviation_pct.toFixed(1)}%)
            </span>
          ) : (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
              IN AGREEMENT
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {multipli?.price && multipli.price > 0 ? `$${multipli.price.toFixed(2)}` : '$0.00'}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-purple-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>OSM 1-Hr Delay Buffer</span>
          <span className={isMultipliOutside ? 'text-amber-700 font-bold' : 'text-purple-700 font-medium'}>
            Dev: {decision.multipli_deviation_pct > 0 ? `+${decision.multipli_deviation_pct.toFixed(2)}%` : '0.00%'}
          </span>
        </div>
      </div>

      {/* 2. Cross-Oracle Consensus Card */}
      <div 
        onClick={() => onInspectTarget && onInspectTarget('CONSENSUS')}
        className={`bg-surface border p-4 rounded shadow-card cursor-pointer transition relative group ${
          consensus.has_strong_consensus ? 'border-borderHairline hover:border-blue-400' : 'border-rose-300 bg-rose-50/10'
        }`}
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-blue-600">2. ORACLE CONSENSUS</span>
          {consensus.has_strong_consensus ? (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              {consensus.cluster_size} / {consensus.total_eligible} FEEDS AGREE
            </span>
          ) : (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300 font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
              NO DOMINANT CLUSTER
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between">
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-mono font-bold text-blue-700 tnum">
              {consensus.has_strong_consensus && consensus.consensus_price && consensus.consensus_price > 0
                ? `$${consensus.consensus_price.toFixed(2)}` 
                : 'No Consensus'}
            </span>
            {consensus.has_strong_consensus && (
              <span className="text-[11px] font-mono text-blue-500 font-medium">
                ({consensus.cluster_spread_pct.toFixed(2)}% spr)
              </span>
            )}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-blue-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>Agreement Band &le; 0.5%</span>
          <span className={consensus.has_strong_consensus ? 'text-blue-600 font-medium' : 'text-rose-600 font-bold'}>
            Strength: {consensus.has_strong_consensus ? 'High' : 'None'}
          </span>
        </div>
      </div>

      {/* 3. Real-Time Spot Reference Card */}
      <div 
        onClick={() => onInspectTarget && onInspectTarget('MARKET')}
        className={`bg-surface border p-4 rounded shadow-card cursor-pointer transition relative group ${
          decision.market_reference_used ? 'border-emerald-400 bg-emerald-50/15' : 'border-borderHairline hover:border-amber-400'
        }`}
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-amber-700">3. SPOT REFERENCE</span>
          {decision.market_reference_used ? (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold flex items-center gap-1">
              <CheckCircle2 className="w-2.5 h-2.5" />
              USED / CORROBORATED
            </span>
          ) : isHalted ? (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-semibold">
              DISPUTE MONITORING
            </span>
          ) : (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 font-medium">
              AVAILABLE (NOT REQUIRED)
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {market?.price !== null && market?.price !== undefined ? `$${market.price.toFixed(2)}` : 'Streaming...'}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-amber-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>Terminal Market CLOB</span>
          <span className="text-slate-700">Instant Cross-Check</span>
        </div>
      </div>

      {/* 4. AEGIS Authoritative Final Valuation Card */}
      <div 
        onClick={() => onInspectTarget && onInspectTarget('DECISION')}
        className={`bg-surface border p-4 rounded shadow-card cursor-pointer transition relative group ${
          isHalted
            ? 'border-rose-400 bg-rose-50/20'
            : isRestricted
            ? 'border-amber-400 bg-amber-50/20'
            : 'border-emerald-400 bg-emerald-50/20'
        }`}
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-slate-900">4. AEGIS VALUATION</span>
          {isHalted ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300">
              <Lock className="w-3 h-3 text-rose-600" />
              HALTED (CIRCUIT BREAKER)
            </span>
          ) : isRestricted ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
              <AlertTriangle className="w-3 h-3 text-amber-600" />
              RESTRICTED MODE
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              NORMAL VALUATION
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {isHalted ? (
              <span className="text-rose-700">LOCKED (0.00)</span>
            ) : decision.final_price !== null ? (
              `$${decision.final_price.toFixed(2)}`
            ) : (
              'Computing...'
            )}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-slate-700 font-medium transition">
            Audit &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
          <span className="text-slate-500 truncate max-w-[140px]" title={decision.selected_source}>
            Src: {decision.selected_source?.replace(/_/g, ' ') || 'Consensus'}
          </span>
          <span className={`font-bold ${
            isHalted ? 'text-rose-700' : isRestricted ? 'text-amber-700' : 'text-emerald-700'
          }`}>
            {(decision.effective_ltv * 100).toFixed(0)}% LTV Cap
          </span>
        </div>
      </div>

    </div>
  );
};
