import React from 'react';
import { SimulationSnapshot } from '@/lib/types';
import { 
  GitCommit, 
  ArrowRight, 
  ShieldAlert, 
  Scale, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingDown, 
  Lock,
  Layers
} from 'lucide-react';

interface CausalChainPanelProps {
  snapshot: SimulationSnapshot;
}

export const CausalChainPanel: React.FC<CausalChainPanelProps> = ({ snapshot }) => {
  const pos = snapshot.position;
  const ev = snapshot.evidence;
  const dec = snapshot.decision;
  const pOsm = snapshot.p_osm;
  const pMarket = snapshot.p_market;
  const pDec = snapshot.p_dec;

  const isHalted = dec.action === 'HALT' || dec.dispute_status === 'HALTED' || ev.oracle_status === 'HALTED_CIRCUIT_BREAKER';
  const isRestricted = dec.action === 'HAIRCUT' || dec.dispute_status === 'RESTRICTED' || ev.oracle_status === 'EVIDENCE_OF_ABNORMAL_DEVIATION';

  const deviationPct = pMarket.value && pOsm.value 
    ? Math.abs((pOsm.value - pMarket.value) / pMarket.value) * 100 
    : 0;

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderHairline pb-2.5">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-slate-500" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            End-to-End Causal Chain: Oracle Evidence → Protocol Risk
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
          DETERMINISTIC PIPELINE
        </span>
      </div>

      {/* Interactive 5-Step Flowchart */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 text-xs">
        
        {/* Step 1: Market Observation */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>1. Market Stream</span>
              <TrendingDown className="w-3 h-3 text-slate-400" />
            </div>
            <div className="font-mono font-bold text-slate-900 mt-1">
              ${pMarket.value ? pMarket.value.toFixed(2) : '--'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
              P_OSM: ${pOsm.value.toFixed(2)}
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200 text-[10px] text-slate-600">
            {deviationPct > 3.0 ? (
              <span className="text-amber-700 font-bold">{deviationPct.toFixed(1)}% Deviation</span>
            ) : (
              <span className="text-emerald-700 font-semibold">In Tolerance (≤3%)</span>
            )}
          </div>
        </div>

        {/* Step 2: Evidence Engine */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>2. Multi-Lane</span>
              <ShieldAlert className="w-3 h-3 text-slate-400" />
            </div>
            <div className="font-mono font-bold text-slate-900 mt-1">
              Score: {ev.anomaly_score.toFixed(2)}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
              Status: {ev.oracle_status.replace(/_/g, ' ')}
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200 text-[10px] text-slate-600">
            {ev.reason_codes?.[0] ? ev.reason_codes[0].slice(0, 18) : 'Nominal'}
          </div>
        </div>

        {/* Step 3: Oracle Decision */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>3. Decision</span>
              <Scale className="w-3 h-3 text-slate-400" />
            </div>
            <div className={`font-mono font-bold mt-1 ${
              isHalted ? 'text-rose-700' : isRestricted ? 'text-amber-700' : 'text-emerald-700'
            }`}>
              {dec.dispute_status || 'VERIFIED'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
              Source: {dec.selected_source}
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200 text-[10px] text-slate-600">
            Final: ${dec.final_price !== null ? dec.final_price.toFixed(2) : (pDec.value ? pDec.value.toFixed(2) : '--')}
          </div>
        </div>

        {/* Step 4: Protocol Policy */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>4. Risk Policy</span>
              {isHalted ? <Lock className="w-3 h-3 text-rose-500" /> : <CheckCircle2 className="w-3 h-3 text-emerald-500" />}
            </div>
            <div className="font-mono font-bold text-slate-900 mt-1">
              {pos ? `${(pos.effective_ltv * 100).toFixed(0)}% LTV` : '80% LTV'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
              {pos?.protocol_state || 'NORMAL'} Mode
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200 text-[10px] text-slate-600">
            {isHalted ? 'Minting Frozen' : isRestricted ? 'Haircut (-30%)' : 'Standard LTV'}
          </div>
        </div>

        {/* Step 5: Position Impact */}
        <div className={`p-2.5 rounded border flex flex-col justify-between ${
          pos?.position_status === 'HEALTHY' 
            ? 'bg-emerald-50/50 border-emerald-200' 
            : pos?.position_status === 'RESTRICTED'
            ? 'bg-amber-50/50 border-amber-200'
            : 'bg-surfaceSubtle border-borderHairline'
        }`}>
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>5. Vault Health</span>
              {pos?.position_status === 'HEALTHY' ? (
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-3 h-3 text-amber-600" />
              )}
            </div>
            <div className="font-mono font-bold text-slate-900 mt-1">
              {pos ? `$${pos.max_borrow_capacity.toFixed(2)} Cap` : '--'}
            </div>
            <div className="text-[10px] font-mono mt-0.5 text-slate-600">
              Debt: ${pos?.debt_amount.toFixed(2) || '700.00'}
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200/80 text-[10px] font-bold text-slate-700">
            Status: {pos?.position_status || 'HEALTHY'}
          </div>
        </div>

      </div>
    </div>
  );
};
