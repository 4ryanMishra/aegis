import React from 'react';
import { SimulationSnapshot } from '@/lib/types';
import { 
  GitMerge, 
  ArrowRight, 
  ShieldAlert, 
  Scale, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingDown, 
  Lock,
  Layers,
  Radio
} from 'lucide-react';

interface CausalChainPanelProps {
  snapshot: SimulationSnapshot;
}

export const CausalChainPanel: React.FC<CausalChainPanelProps> = ({ snapshot }) => {
  const pos = snapshot.position;
  const dec = snapshot.decision;
  const consensus = snapshot.consensus;
  const multipli = snapshot.multipli_observation;
  const market = snapshot.market_observation;

  const protocolState = dec.protocol_state || 'NORMAL';
  const isHalted = protocolState === 'HALTED' || dec.state === 'ORACLE_INSTABILITY' || dec.state === 'NO_CONSENSUS';
  const isDeviation = dec.state === 'MULTIPLI_DEVIATION';
  const isMarketCorroborated = dec.state === 'MARKET_CORROBORATED';
  const hasStrongConsensus = consensus.has_strong_consensus;

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderHairline pb-2.5">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            End-to-End On-Chain Causal Chain: Oracle Observations &rarr; Risk Policy &rarr; Vault Solvency
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
          DETERMINISTIC PIPELINE
        </span>
      </div>

      {/* 5-Step Pipeline Flow */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 text-xs">
        
        {/* Step 1: Multi-Oracle Observations */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>1. Multi-Oracle</span>
              <Radio className="w-3 h-3 text-slate-400" />
            </div>
            <div className="font-mono font-bold text-slate-900 mt-1">
              {snapshot.oracle_sources?.length || 6} Networks
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
              Spot: ${market?.price ? market.price.toFixed(2) : '4320.00'}
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200 text-[10px] text-slate-600">
            Chainlink, Pyth, +4 More
          </div>
        </div>

        {/* Step 2: Price-Band Clustering */}
        <div className={`p-2.5 rounded border flex flex-col justify-between ${
          hasStrongConsensus ? 'bg-surfaceSubtle border-borderHairline' : 'bg-rose-50/40 border-rose-200'
        }`}>
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>2. Clustering</span>
              <GitMerge className="w-3 h-3 text-slate-400" />
            </div>
            <div className={`font-mono font-bold mt-1 ${hasStrongConsensus ? 'text-blue-700' : 'text-rose-700'}`}>
              {hasStrongConsensus && consensus.consensus_price ? `$${consensus.consensus_price.toFixed(2)}` : 'No Consensus'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
              {hasStrongConsensus
                ? `${consensus.cluster_size}/${consensus.total_eligible} agree (<=0.5%)`
                : 'Bimodal Split (3 vs 3)'}
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200 text-[10px] text-slate-600">
            Spread: {hasStrongConsensus ? `${consensus.cluster_spread_pct.toFixed(2)}%` : 'Dispersed'}
          </div>
        </div>

        {/* Step 3: Multipli Deviation Cross-Check */}
        <div className={`p-2.5 rounded border flex flex-col justify-between ${
          isHalted ? 'bg-rose-50/40 border-rose-200' : isDeviation ? 'bg-amber-50/40 border-amber-200' : 'bg-surfaceSubtle border-borderHairline'
        }`}>
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>3. OSM Check</span>
              <Scale className="w-3 h-3 text-slate-400" />
            </div>
            <div className={`font-mono font-bold mt-1 ${
              isHalted ? 'text-rose-700' : dec.multipli_deviation_pct > 0.5 ? 'text-amber-700' : 'text-emerald-700'
            }`}>
              {isHalted ? 'DISLOCATED' : `${dec.multipli_deviation_pct.toFixed(2)}% Δ`}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
              OSM: ${multipli?.price ? multipli.price.toFixed(2) : '0.00'}
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200 text-[10px] text-slate-600">
            {isHalted ? 'Unresolved Split' : isDeviation ? 'Deviation Alert' : 'In Agreement'}
          </div>
        </div>

        {/* Step 4: Decision & Valuation */}
        <div className={`p-2.5 rounded border flex flex-col justify-between ${
          isHalted ? 'bg-rose-50/40 border-rose-200' : isDeviation ? 'bg-amber-50/40 border-amber-200' : 'bg-surfaceSubtle border-borderHairline'
        }`}>
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>4. Valuation</span>
              {isHalted ? <Lock className="w-3 h-3 text-rose-500" /> : <CheckCircle2 className="w-3 h-3 text-emerald-500" />}
            </div>
            <div className={`font-mono font-bold mt-1 ${isHalted ? 'text-rose-700' : 'text-slate-900'}`}>
              {isHalted ? 'LOCKED (0.00)' : `$${dec.final_price?.toFixed(2) || '--'}`}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5 truncate" title={dec.selected_source}>
              {isHalted ? 'Circuit Breaker' : isDeviation ? 'min(OSM, Cons)' : isMarketCorroborated ? 'Market Corroborated' : 'OSM Consensus'}
            </div>
          </div>
          <div className="mt-2 pt-1 border-t border-slate-200 text-[10px] font-bold text-slate-700">
            LTV: {(dec.effective_ltv * 100).toFixed(0)}%
          </div>
        </div>

        {/* Step 5: Downstream Vault Solvency */}
        <div className={`p-2.5 rounded border flex flex-col justify-between ${
          pos?.position_status === 'HEALTHY' 
            ? 'bg-emerald-50/50 border-emerald-200' 
            : pos?.position_status === 'RESTRICTED'
            ? 'bg-amber-50/50 border-amber-200'
            : 'bg-rose-50/50 border-rose-200'
        }`}>
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase">
              <span>5. Vault Health</span>
              {pos?.position_status === 'HEALTHY' ? (
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              ) : isHalted ? (
                <Lock className="w-3 h-3 text-rose-600" />
              ) : (
                <AlertTriangle className="w-3 h-3 text-amber-600" />
              )}
            </div>
            <div className="font-mono font-bold text-slate-900 mt-1">
              ${pos ? pos.max_borrow_capacity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'} Cap
            </div>
            <div className="text-[10px] font-mono mt-0.5 text-slate-600">
              Debt: ${pos ? pos.debt_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '28,000.00'}
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
