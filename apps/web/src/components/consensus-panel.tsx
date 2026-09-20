import React from 'react';
import { ConsensusResult, RiskDecisionResult, OracleObservation } from '@/lib/types';
import { 
  ShieldCheck, 
  AlertTriangle, 
  GitMerge, 
  TrendingUp, 
  Percent, 
  CheckCircle2, 
  Radio, 
  Scale,
  ShieldAlert,
  Layers
} from 'lucide-react';

interface ConsensusPanelProps {
  consensus: ConsensusResult;
  decision: RiskDecisionResult;
  multipli?: OracleObservation | null;
}

export const ConsensusPanel: React.FC<ConsensusPanelProps> = ({
  consensus,
  decision,
  multipli,
}) => {
  const isHealthy = decision.state === 'HEALTHY_CONSENSUS' && consensus.has_strong_consensus;
  const hasOutliers = consensus.outlier_members.length > 0;
  const noConsensus = decision.state === 'NO_CONSENSUS' || decision.state === 'ORACLE_INSTABILITY' || !consensus.has_strong_consensus;
  const multipliDev = decision.multipli_deviation_pct;

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderHairline pb-2.5">
        <div className="flex items-center space-x-2">
          <GitMerge className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
            Price-Band Agreement Clustering Telemetry
          </h3>
        </div>
        <div className="flex items-center gap-1.5">
          {noConsensus ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300">
              <ShieldAlert className="w-3 h-3 text-rose-600" />
              NO DOMINANT CLUSTER
            </span>
          ) : hasOutliers ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
              <AlertTriangle className="w-3 h-3 text-amber-600" />
              OUTLIER DETECTED ({consensus.cluster_size}/{consensus.total_eligible} AGREE)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              STRONG AGREEMENT ({consensus.cluster_size}/{consensus.total_eligible} AGREE)
            </span>
          )}
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        {/* Metric 1: Consensus Median */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 uppercase font-mono flex items-center justify-between">
            <span>Consensus Price</span>
            <span className="text-blue-600 font-bold">MEDIAN</span>
          </div>
          <div className="font-mono font-bold text-base text-blue-900 mt-1 tnum">
            {consensus.has_strong_consensus && consensus.consensus_price !== null && consensus.consensus_price > 0
              ? `$${consensus.consensus_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : 'NO CONSENSUS'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {consensus.cluster_size} / {consensus.total_eligible} feeds agree
          </div>
        </div>

        {/* Metric 2: Agreement Strength */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 uppercase font-mono flex items-center justify-between">
            <span>Agreement Strength</span>
            <Percent className="w-3 h-3 text-slate-400" />
          </div>
          <div className={`font-mono font-bold text-base mt-1 tnum ${
            consensus.has_strong_consensus ? 'text-emerald-700' : 'text-rose-700'
          }`}>
            {consensus.has_strong_consensus ? `${(consensus.agreement_ratio * 100).toFixed(1)}%` : '0.0%'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {consensus.has_strong_consensus ? 'High (>= 60% Quorum)' : 'Insufficient Agreement'}
          </div>
        </div>

        {/* Metric 3: Cluster Spread */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 uppercase font-mono flex items-center justify-between">
            <span>Cluster Spread</span>
            <span className="text-slate-400 font-sans">&le;0.5% max</span>
          </div>
          <div className={`font-mono font-bold text-base mt-1 tnum ${
            consensus.cluster_spread_pct <= 0.20 ? 'text-emerald-700' : consensus.cluster_spread_pct <= 0.50 ? 'text-blue-700' : 'text-rose-700'
          }`}>
            {consensus.cluster_spread_pct.toFixed(2)}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {consensus.cluster_min && consensus.cluster_max
              ? `[$${consensus.cluster_min.toFixed(1)} - $${consensus.cluster_max.toFixed(1)}]`
              : 'N/A'}
          </div>
        </div>

        {/* Metric 4: Multipli Deviation */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 uppercase font-mono flex items-center justify-between">
            <span>Multipli Deviation</span>
            <span className="font-mono text-purple-700 font-bold">|OSM - MED|</span>
          </div>
          <div className={`font-mono font-bold text-base mt-1 tnum ${
            multipliDev > 3.0 ? 'text-rose-700' : multipliDev > 0.5 ? 'text-amber-700' : 'text-emerald-700'
          }`}>
            {multipliDev > 0 ? `${multipliDev.toFixed(2)}%` : '0.00%'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {multipli?.price ? `$${multipli.price.toFixed(2)} OSM` : 'No OSM Feed'}
          </div>
        </div>
      </div>

      {/* Cluster Details Footer */}
      <div className="bg-slate-50 p-2.5 rounded border border-slate-200/80 text-[11px] space-y-1.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-slate-700 font-bold">Cluster A (Agreement Band &le; 0.5%):</span>
          {consensus.cluster_members.length > 0 ? (
            consensus.cluster_members.map((id) => (
              <span key={id} className="font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 text-[10px] font-medium">
                {id.replace(/_/g, ' ')}
              </span>
            ))
          ) : (
            <span className="text-slate-400 font-mono">No dominant cluster formed</span>
          )}
        </div>

        {consensus.outlier_members.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-slate-200/60">
            <span className="text-amber-800 font-bold">Outliers (Outside Cluster):</span>
            {consensus.outlier_members.map((id) => (
              <span key={id} className="font-mono px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-medium">
                {id.replace(/_/g, ' ')} (Excluded from consensus median)
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
