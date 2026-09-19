import React from 'react';
import { ScenarioRecord } from '@/lib/types';
import { AlertTriangle, CheckCircle2, HelpCircle, Layers, ArrowRight } from 'lucide-react';

interface OracleStripProps {
  scenario: ScenarioRecord;
  onInspect: (target: string) => void;
}

export const OracleStrip: React.FC<OracleStripProps> = ({ scenario, onInspect }) => {
  const { p_osm, p_dec, p_market, decision, evidence, window } = scenario;

  const isFinalized = window.is_finalized;
  const isHealthy = evidence.oracle_status === 'HEALTHY_CONSENSUS';
  const hasInconsistency = evidence.oracle_status === 'SUSPECTED_INCONSISTENCY' || evidence.oracle_status === 'EVIDENCE_OF_ABNORMAL_DEVIATION';

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
      
      {/* 1. P_OSM Card */}
      <div 
        onClick={() => onInspect('P_OSM')}
        className="bg-surface border border-borderHairline hover:border-slate-400 p-4 rounded shadow-card cursor-pointer transition relative group"
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-slate-500">P_OSM</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
            {p_osm.status}
          </span>
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            ${p_osm.value.toFixed(2)}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-slate-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>Queued at T0</span>
          <span className="font-mono text-slate-700">Delayed Baseline</span>
        </div>
      </div>

      {/* 2. P_DEC Card */}
      <div 
        onClick={() => onInspect('P_DEC')}
        className="bg-surface border border-borderHairline hover:border-slate-400 p-4 rounded shadow-card cursor-pointer transition relative group"
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-blue-600">P_DEC</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
            {p_dec.status}
          </span>
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {p_dec.value !== null ? `$${p_dec.value.toFixed(2)}` : 'Gathering...'}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-slate-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>{p_dec.validator_count} Validators</span>
          <span className="font-mono text-slate-700">Robust Median</span>
        </div>
      </div>

      {/* 3. P_MARKET Card */}
      <div 
        onClick={() => onInspect('P_MARKET')}
        className="bg-surface border border-borderHairline hover:border-slate-400 p-4 rounded shadow-card cursor-pointer transition relative group"
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-slate-500">P_MARKET</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
            {p_market.is_offchain ? 'OFF-CHAIN API' : 'ON-CHAIN'}
          </span>
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {p_market.value !== null ? `$${p_market.value.toFixed(2)}` : 'Pending T1'}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-slate-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <span>{isFinalized ? 'Observed at T1' : 'Awaiting End of Hour'}</span>
          <span className="font-mono text-slate-700">External Market</span>
        </div>
      </div>

      {/* 4. FINAL PROTOCOL VALUATION */}
      <div 
        onClick={() => onInspect('DECISION')}
        className={`bg-surface border p-4 rounded shadow-card cursor-pointer transition relative group ${
          hasInconsistency && isFinalized
            ? 'border-amber-400 bg-amber-50/20'
            : isHealthy && isFinalized
            ? 'border-emerald-400 bg-emerald-50/20'
            : 'border-borderHairline'
        }`}
      >
        <div className="flex items-center justify-between text-xs text-secondaryText mb-1.5">
          <span className="font-mono font-semibold tracking-wider text-slate-900">FINAL VALUATION</span>
          {isFinalized ? (
            hasInconsistency ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
                <AlertTriangle className="w-3 h-3" />
                ADAPTED
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                <CheckCircle2 className="w-3 h-3" />
                VERIFIED
              </span>
            )
          ) : (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
              PENDING
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-mono font-bold text-slate-900 tnum">
            {decision.final_price !== null ? `$${decision.final_price.toFixed(2)}` : 'Computing...'}
          </div>
          <span className="text-xs text-slate-400 group-hover:text-slate-700 font-medium transition">
            Inspect &rarr;
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
          <span className="text-slate-500">Selected Source:</span>
          <span className="font-mono font-bold text-slate-800">{decision.selected_source}</span>
        </div>
      </div>

    </div>
  );
};
