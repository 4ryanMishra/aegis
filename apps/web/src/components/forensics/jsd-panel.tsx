import React from 'react';
import { ValidatorObservation, JSDMetrics } from '@/lib/types';
import { Network, ShieldAlert, CheckCircle2, Grid, Info } from 'lucide-react';

interface JSDPanelProps {
  validator: ValidatorObservation;
}

export const JSDForensicPanel: React.FC<JSDPanelProps> = ({ validator }) => {
  const metrics = (validator.intermediate_metrics || {}) as Partial<JSDMetrics>;
  const matrix = metrics.pairwise_jsd_matrix || [];
  const meanDiv = metrics.mean_divergence_per_lane || {};
  const laneWeights = metrics.lane_weights || {};
  const divergentLanes = metrics.divergent_lanes || [];
  const hasDivergence = divergentLanes.length > 0 || (metrics.informational_disagreement || 0) > 0.15;

  const lanes = ['Lane 1', 'Lane 2', 'Lane 3', 'Lane 4', 'Lane 5'];

  return (
    <div className="space-y-4 text-xs">
      {/* Header Banner */}
      <div className={`p-3 rounded border flex items-center justify-between ${
        hasDivergence
          ? 'bg-amber-50/70 border-amber-300 text-amber-900'
          : 'bg-emerald-50/70 border-emerald-300 text-emerald-900'
      }`}>
        <div className="flex items-center space-x-2">
          {hasDivergence ? <ShieldAlert className="w-4 h-4 text-amber-700" /> : <CheckCircle2 className="w-4 h-4 text-emerald-700" />}
          <div>
            <span className="font-bold uppercase tracking-wider text-[11px]">
              {hasDivergence ? `INFORMATIONAL DIVERGENCE: ${divergentLanes.join(', ')} ISOLATED` : 'INFORMATIONAL CONSENSUS (UNIFORM ENTROPY OVERLAP)'}
            </span>
            <div className="text-[10px] opacity-80 mt-0.5">
              Reason Code: <span className="font-mono font-semibold">{validator.reason_code}</span>
            </div>
          </div>
        </div>
        <div className="text-right font-mono">
          <div className="text-[10px] opacity-75">Global Disagreement</div>
          <div className="text-sm font-bold tnum">{(metrics.informational_disagreement ?? 0.015).toFixed(4)}</div>
        </div>
      </div>

      {/* Overview Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Evaluation Grid</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            {metrics.grid_bins ?? 100} Discrete Bins
          </div>
        </div>
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Divergent Lanes Isolated</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            {divergentLanes.length > 0 ? divergentLanes.join(', ') : 'None (All in Consensus)'}
          </div>
        </div>
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Metric Property</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            Symmetric, Bounded [0, 1]
          </div>
        </div>
      </div>

      {/* Pairwise JSD Heatmap Matrix Table */}
      <div className="bg-surface border border-borderHairline rounded overflow-hidden">
        <div className="px-3 py-2 bg-surfaceSubtle border-b border-borderHairline flex items-center justify-between">
          <div className="flex items-center space-x-1.5 font-semibold text-slate-700 text-[11px] uppercase tracking-wider">
            <Grid className="w-3.5 h-3.5 text-slate-500" />
            <span>Pairwise Jensen-Shannon Divergence Matrix D_JS(P_i || P_j)</span>
          </div>
          <span className="font-mono text-[10px] text-slate-500">
            D_JS ∈ [0.0, 1.0]
          </span>
        </div>

        <div className="overflow-x-auto p-2">
          <table className="w-full text-center border-collapse text-xs font-mono">
            <thead>
              <tr className="text-[10px] text-slate-500 border-b border-borderHairline">
                <th className="py-2 px-2 text-left">Lane</th>
                {lanes.map((l, idx) => (
                  <th key={idx} className="py-2 px-2 font-semibold">{l}</th>
                ))}
                <th className="py-2 px-2 text-right">Mean D_JS</th>
                <th className="py-2 px-2 text-right">Consensus Weight</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderHairline text-[11px]">
              {lanes.map((l, rowIdx) => {
                const laneId = `lane-${rowIdx + 1}`;
                const mean = meanDiv[laneId] ?? (matrix[rowIdx] ? matrix[rowIdx].reduce((a, b) => a + b, 0) / matrix[rowIdx].length : 0.01);
                const weight = laneWeights[laneId] ?? 0.20;
                const isDiv = divergentLanes.includes(laneId);

                return (
                  <tr key={rowIdx} className={isDiv ? 'bg-amber-50/60' : 'hover:bg-slate-50/60'}>
                    <td className="py-2 px-2 text-left font-bold text-slate-900">
                      {l}
                    </td>
                    {lanes.map((_, colIdx) => {
                      const val = matrix[rowIdx]?.[colIdx] ?? (rowIdx === colIdx ? 0.0 : 0.015);
                      let cellBg = 'text-slate-700';
                      if (val > 0.3) cellBg = 'bg-amber-200/70 text-amber-900 font-bold';
                      else if (val > 0.1) cellBg = 'bg-amber-100/50 text-amber-800';

                      return (
                        <td key={colIdx} className={`py-1.5 px-2 tnum rounded-xs ${cellBg}`}>
                          {val.toFixed(3)}
                        </td>
                      );
                    })}
                    <td className="py-2 px-2 text-right font-bold text-slate-900 tnum">
                      {mean.toFixed(3)}
                    </td>
                    <td className="py-2 px-2 text-right font-bold text-slate-900 tnum">
                      <span className={`px-1.5 py-0.5 rounded ${weight < 0.1 ? 'bg-amber-100 text-amber-900' : 'bg-slate-100 text-slate-700'}`}>
                        {(weight * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Final Valuation Result */}
      <div className="p-3 bg-white rounded border border-slate-200 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase font-mono text-slate-500">Information-Consensus Valuation</div>
          <div className="text-xl font-mono font-bold text-slate-900 tnum">
            ${validator.estimated_price.toFixed(2)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase font-mono text-slate-500">95% Uncertainty Confidence Band</div>
          <div className="text-xs font-mono font-semibold text-slate-700 tnum">
            [${validator.uncertainty_lower.toFixed(2)} &ndash; ${validator.uncertainty_upper.toFixed(2)}]
          </div>
        </div>
      </div>

      {/* Methodology Guardrail Note */}
      <div className="p-2.5 bg-slate-50 rounded border border-borderHairline text-slate-600 text-[11px] leading-relaxed">
        <div className="font-semibold text-slate-800 flex items-center gap-1 mb-0.5">
          <Info className="w-3 h-3 text-slate-500" />
          Lane 3 Security Role & Mathematical Bound:
        </div>
        Evaluates the geometric probability overlap between all methodology uncertainty distributions. Even if an adversarial node crafts a plausible point quote, divergence in distribution shape trips D_JS and attenuates its consensus weight w_i = exp(-γ · D̄_JS).
      </div>
    </div>
  );
};
