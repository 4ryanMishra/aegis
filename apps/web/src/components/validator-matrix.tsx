import React from 'react';
import { ValidatorObservation } from '@/lib/types';
import { Layers, Database, ExternalLink, ShieldAlert, CheckCircle2, Cpu } from 'lucide-react';

interface ValidatorMatrixProps {
  validators: ValidatorObservation[];
  onInspectValidator: (val: ValidatorObservation) => void;
}

export const ValidatorMatrix: React.FC<ValidatorMatrixProps> = ({
  validators,
  onInspectValidator,
}) => {
  const getPrimaryMetric = (v: ValidatorObservation) => {
    const m = v.intermediate_metrics || {};
    const meth = v.methodology || v.strategy_id || '';

    if (meth.includes('KALMAN') || meth.includes('kalman')) {
      const d2 = m.mahalanobis_d2 ?? 0;
      return `D² = ${d2.toFixed(2)} (χ²: 3.84)`;
    } else if (meth.includes('HUBER') || meth.includes('huber')) {
      const outliers = m.outlier_count ?? 0;
      const s = m.scale_s ?? 0;
      return `Outliers: ${outliers} | s: ${s.toFixed(3)}`;
    } else if (meth.includes('JENSEN') || meth.includes('jsd')) {
      const dMean = m.mean_divergence_per_lane?.[v.lane_id] ?? 0.012;
      return `D̄_JS: ${dMean.toFixed(3)}`;
    } else if (meth.includes('ORNSTEIN') || meth.includes('ou')) {
      if (!m.is_rwa || !m.has_anchor) return 'N/A (Unanchored)';
      const z = m.standardized_residual ?? 0;
      return `z_OU = ${z.toFixed(2)} σ`;
    } else if (meth.includes('PAGE_CUSUM') || meth.includes('cusum')) {
      const sPos = m.s_pos ?? 0;
      const h = m.threshold_h ?? 4.0;
      return `S⁺ = ${sPos.toFixed(2)} / ${h.toFixed(1)}`;
    }
    return '--';
  };

  const getStatusBadge = (v: ValidatorObservation) => {
    const isAnomalous = v.anomaly_score > 0.4 || v.decision.includes('GATED') || v.decision.includes('OUTLIER') || v.decision.includes('ALERT') || v.decision.includes('CANDIDATE') || v.decision.includes('DISAGREEMENT');

    if (isAnomalous) {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-300">
          <ShieldAlert className="w-3 h-3 text-amber-600" />
          {v.decision.replace(/_/g, ' ')}
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
        {v.decision ? v.decision.replace(/_/g, ' ') : 'VERIFIED'}
      </span>
    );
  };

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-borderHairline flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-slate-700" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900">
              Statistical Defense Stack & Methodology Matrix
            </h3>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Five methodology lanes, each capable of being operated by multiple independent validator nodes.
            <span className="opacity-75 font-mono ml-1">(Current MVP simulation: 1 simulated node per lane).</span>
          </p>
        </div>
        <span className="text-[11px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 self-start sm:self-auto">
          {validators.length} / 5 Lanes Active
        </span>
      </div>

      {validators.length === 0 ? (
        <div className="p-8 text-center text-xs text-secondaryText">
          Awaiting validator evidence submissions as verification window advances...
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-surfaceSubtle border-b border-borderHairline text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 px-3">Lane & Node</th>
                <th className="py-2.5 px-3">Statistical Methodology</th>
                <th className="py-2.5 px-3 text-right">Price Estimate</th>
                <th className="py-2.5 px-3 text-center">95% Uncertainty</th>
                <th className="py-2.5 px-3">Primary Forensic Metric</th>
                <th className="py-2.5 px-3 text-center">Defense Decision</th>
                <th className="py-2.5 px-3 text-right">Forensic Telemetry</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderHairline">
              {validators.map((v) => (
                <tr 
                  key={v.validator_id}
                  className="hover:bg-slate-50/80 transition cursor-pointer group"
                  onClick={() => onInspectValidator(v)}
                >
                  <td className="py-2.5 px-3">
                    <div className="font-mono font-bold text-slate-900">
                      {v.lane_id.toUpperCase()}
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      {v.validator_id} &bull; {v.operator_id}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-slate-700">
                    <div className="font-medium text-slate-900 truncate max-w-[220px]" title={v.methodology_name}>
                      {v.methodology_name}
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      {v.methodology}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900 tnum">
                    ${v.estimated_price.toFixed(2)}
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono text-slate-500 text-[11px] tnum">
                    [${v.uncertainty_lower.toFixed(2)} &ndash; ${v.uncertainty_upper.toFixed(2)}]
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-slate-700">
                    <span className="bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
                      {getPrimaryMetric(v)}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {getStatusBadge(v)}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        onInspectValidator(v);
                      }}
                      className="px-2 py-1 bg-slate-100 group-hover:bg-slate-900 text-slate-600 group-hover:text-white rounded border border-slate-200 group-hover:border-slate-900 transition text-[11px] font-medium flex items-center gap-1 ml-auto"
                      title="Inspect Forensic Telemetry"
                    >
                      <span>Inspect</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
