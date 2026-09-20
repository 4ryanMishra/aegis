import React from 'react';
import { OracleObservation, SimulationSnapshot } from '@/lib/types';
import { 
  Layers, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Wifi, 
  WifiOff, 
  Radio,
  ExternalLink,
  ShieldAlert,
  HelpCircle
} from 'lucide-react';

interface OracleFeedMatrixProps {
  snapshot: SimulationSnapshot;
  onInspectOracle?: (source: OracleObservation) => void;
}

export const OracleFeedMatrix: React.FC<OracleFeedMatrixProps> = ({
  snapshot,
  onInspectOracle,
}) => {
  const sources = snapshot.oracle_sources || [];
  const multipli = snapshot.multipli_observation;

  const allSources = multipli ? [multipli, ...sources] : sources;

  const getStatusBadge = (status: string, valid: boolean) => {
    if (!valid || status === 'FAILED') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
          <WifiOff className="w-3 h-3 text-rose-500" />
          FAILED
        </span>
      );
    }
    if (status === 'STALE') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
          <Clock className="w-3 h-3 text-amber-500" />
          STALE
        </span>
      );
    }
    if (status === 'DELAYED') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
          <Clock className="w-3 h-3 text-blue-500" />
          DELAYED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
        <Wifi className="w-3 h-3 text-emerald-500" />
        ACTIVE
      </span>
    );
  };

  const getClusterBadge = (clusterId?: string | null, isMultipli?: boolean) => {
    if (isMultipli) {
      return (
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 font-semibold">
          TARGET OSM
        </span>
      );
    }
    if (clusterId === 'A' || clusterId === 'CONSENSUS') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
          CLUSTER A
        </span>
      );
    }
    if (clusterId === 'OUTLIER') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300">
          <ShieldAlert className="w-3 h-3 text-rose-600" />
          OUTLIER
        </span>
      );
    }
    return (
      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
        OFFLINE
      </span>
    );
  };

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderHairline pb-2.5">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
            Multi-Oracle On-Chain Observation Matrix ({allSources.length} Feeds)
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
            Active
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
            Cluster Consensus
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
            Outlier
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-surfaceSubtle text-[10px] uppercase font-mono text-slate-500 tracking-wider">
              <th className="py-2 px-3 font-semibold">Oracle Network</th>
              <th className="py-2 px-3 font-semibold">Provider / Source ID</th>
              <th className="py-2 px-3 font-semibold text-right">Observed Price</th>
              <th className="py-2 px-3 font-semibold text-center">Age / Latency</th>
              <th className="py-2 px-3 font-semibold text-center">Status</th>
              <th className="py-2 px-3 font-semibold text-center">Cluster Assignment</th>
              <th className="py-2 px-3 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono">
            {allSources.map((source) => {
              const isMultipli = source.source_id === 'multipli_osm' || source.name.includes('Multipli');
              const isOutlier = source.cluster_id === 'OUTLIER';
              const inCluster = source.cluster_id === 'A' || source.cluster_id === 'CONSENSUS';

              return (
                <tr 
                  key={source.source_id}
                  className={`hover:bg-slate-50/80 transition-colors ${
                    isOutlier ? 'bg-rose-50/30' : inCluster ? 'bg-blue-50/10' : isMultipli ? 'bg-purple-50/20' : ''
                  }`}
                >
                  {/* Name */}
                  <td className="py-2.5 px-3 font-sans">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${
                        isOutlier ? 'bg-rose-500' : inCluster ? 'bg-blue-500' : isMultipli ? 'bg-purple-500' : 'bg-slate-400'
                      }`} />
                      <span className="font-semibold text-slate-800">{source.name}</span>
                      {source.has_confidence && (
                        <span className="text-[9px] font-mono px-1 py-0.2 bg-slate-100 text-slate-600 rounded">
                          &plusmn;${source.confidence?.toFixed(2) || '0.25'}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* ID */}
                  <td className="py-2.5 px-3 text-slate-500 text-[11px]">
                    {source.source_id}
                  </td>

                  {/* Price */}
                  <td className="py-2.5 px-3 text-right">
                    {source.price !== null && source.price > 0 ? (
                      <span className={`font-bold text-sm ${
                        isOutlier ? 'text-rose-700' : inCluster ? 'text-blue-700' : isMultipli ? 'text-purple-900' : 'text-slate-800'
                      }`}>
                        ${source.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    ) : (
                      <span className="text-slate-400 font-medium">REVERT / ZERO</span>
                    )}
                  </td>

                  {/* Age */}
                  <td className="py-2.5 px-3 text-center text-[11px] text-slate-500">
                    {source.age_seconds < 60 
                      ? `${source.age_seconds}s ago`
                      : `${Math.floor(source.age_seconds / 60)}m ${source.age_seconds % 60}s`}
                  </td>

                  {/* Status */}
                  <td className="py-2.5 px-3 text-center">
                    {getStatusBadge(source.status, source.valid)}
                  </td>

                  {/* Cluster */}
                  <td className="py-2.5 px-3 text-center">
                    {getClusterBadge(source.cluster_id, isMultipli)}
                  </td>

                  {/* Inspect Action */}
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => onInspectOracle && onInspectOracle(source)}
                      className="text-[11px] font-sans text-slate-400 hover:text-blue-600 font-medium transition"
                    >
                      Audit &rarr;
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer Info */}
      <div className="pt-2 border-t border-borderHairline flex items-center justify-between text-[11px] text-slate-500">
        <span>
          <strong>Clustering Rule:</strong> Max spread within agreement band &le; 0.50%. Median computed deterministically from largest cluster.
        </span>
        <span className="font-mono">
          Agreement Ratio: {(snapshot.consensus.agreement_ratio * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  );
};
