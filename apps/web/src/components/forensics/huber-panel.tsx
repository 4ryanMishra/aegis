import React from 'react';
import { ValidatorObservation, HuberMetrics, HuberWeightRecord } from '@/lib/types';
import { ShieldAlert, CheckCircle2, Table, Info } from 'lucide-react';

interface HuberPanelProps {
  validator: ValidatorObservation;
}

export const HuberForensicPanel: React.FC<HuberPanelProps> = ({ validator }) => {
  const metrics = (validator.intermediate_metrics || {}) as Partial<HuberMetrics>;
  const weightsTable = metrics.weights_table || [];
  const hasOutliers = (metrics.outlier_count || 0) > 0;

  return (
    <div className="space-y-4 text-xs">
      {/* Header Banner */}
      <div className={`p-3 rounded border flex items-center justify-between ${
        hasOutliers
          ? 'bg-amber-50/70 border-amber-300 text-amber-900'
          : 'bg-emerald-50/70 border-emerald-300 text-emerald-900'
      }`}>
        <div className="flex items-center space-x-2">
          {hasOutliers ? <ShieldAlert className="w-4 h-4 text-amber-700" /> : <CheckCircle2 className="w-4 h-4 text-emerald-700" />}
          <div>
            <span className="font-bold uppercase tracking-wider text-[11px]">
              {hasOutliers ? `${metrics.outlier_count} OUTLIER(S) ATTENUATED VIA LINEAR LOSS` : 'ROBUST LOCATION CONVERGED (GAUSSIAN REGIME)'}
            </span>
            <div className="text-[10px] opacity-80 mt-0.5">
              Reason Code: <span className="font-mono font-semibold">{validator.reason_code}</span>
            </div>
          </div>
        </div>
        <div className="text-right font-mono">
          <div className="text-[10px] opacity-75">IRLS Iterations</div>
          <div className="text-sm font-bold tnum">{metrics.iterations ?? 1} (converged)</div>
        </div>
      </div>

      {/* Scale & Estimator Parameters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Sample Median μ̃₀</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            ${(metrics.initial_median ?? (validator.estimated_price ?? 0)).toFixed(2)}
          </div>
        </div>
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">MAD Scale s = 1.4826·MAD</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            {(metrics.scale_s ?? 0.05).toFixed(4)}
          </div>
        </div>
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Huber Tuning k (95%)</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            {(metrics.huber_k ?? 1.345).toFixed(3)}
          </div>
        </div>
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Robust Standard Error</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            {(metrics.standard_error ?? 0.02).toFixed(4)}
          </div>
        </div>
      </div>

      {/* IRLS Weights Table */}
      <div className="bg-surface border border-borderHairline rounded overflow-hidden">
        <div className="px-3 py-2 bg-surfaceSubtle border-b border-borderHairline flex items-center justify-between">
          <div className="flex items-center space-x-1.5 font-semibold text-slate-700 text-[11px] uppercase tracking-wider">
            <Table className="w-3.5 h-3.5 text-slate-500" />
            <span>Feed Observations & IRLS Attenuation Weights</span>
          </div>
          <span className="font-mono text-[10px] text-slate-500">
            w(r) = 1 if |r| ≤ k else k / |r|
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-borderHairline text-[10px] font-mono text-slate-500 uppercase">
                <th className="py-2 px-3">Feed Quote</th>
                <th className="py-2 px-3 text-right">Residual (z - μ̂)</th>
                <th className="py-2 px-3 text-right">Std Residual (r)</th>
                <th className="py-2 px-3 text-right">IRLS Weight</th>
                <th className="py-2 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderHairline font-mono text-[11px]">
              {weightsTable.length > 0 ? (
                weightsTable.map((w: HuberWeightRecord, idx: number) => (
                  <tr key={idx} className={w.is_outlier ? 'bg-amber-50/50' : 'hover:bg-slate-50/60'}>
                    <td className="py-2 px-3 font-bold text-slate-900 tnum">
                      ${w.price.toFixed(2)}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-700 tnum">
                      {w.residual >= 0 ? '+' : ''}{w.residual.toFixed(3)}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-700 tnum">
                      {w.std_residual >= 0 ? '+' : ''}{w.std_residual.toFixed(2)}
                    </td>
                    <td className="py-2 px-3 text-right font-bold tnum">
                      <span className={`px-1.5 py-0.5 rounded ${w.weight < 0.5 ? 'bg-amber-100 text-amber-900' : 'text-slate-900'}`}>
                        {w.weight.toFixed(4)}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-center">
                      {w.is_outlier ? (
                        <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
                          ATTENUATED OUTLIER
                        </span>
                      ) : (
                        <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                          GAUSSIAN EFFICIENCY
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-slate-400">
                    No discrete observation weights table recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Final Valuation Result */}
      <div className="p-3 bg-white rounded border border-slate-200 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase font-mono text-slate-500">Huber Robust Location Estimate</div>
          <div className="text-xl font-mono font-bold text-slate-900 tnum">
            {validator.estimated_price !== null && validator.estimated_price !== undefined ? `$${validator.estimated_price.toFixed(2)}` : '--'}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase font-mono text-slate-500">95% Asymptotic Confidence Band</div>
          <div className="text-xs font-mono font-semibold text-slate-700 tnum">
            {validator.uncertainty_lower !== null && validator.uncertainty_upper !== null && validator.uncertainty_lower !== undefined && validator.uncertainty_upper !== undefined
              ? `[$${validator.uncertainty_lower.toFixed(2)} – $${validator.uncertainty_upper.toFixed(2)}]`
              : '--'}
          </div>
        </div>
      </div>

      {/* Methodology Guardrail Note */}
      <div className="p-2.5 bg-slate-50 rounded border border-borderHairline text-slate-600 text-[11px] leading-relaxed">
        <div className="font-semibold text-slate-800 flex items-center gap-1 mb-0.5">
          <Info className="w-3 h-3 text-slate-500" />
          Lane 2 Security Role & Mathematical Bound:
        </div>
        Transitions from quadratic loss (Gaussian efficiency) to linear loss (bounded influence) when standardized residual exceeds k=1.345. Outliers have bounded non-zero influence rather than being arbitrarily trimmed, resisting both Sybil poisoning and multi-source dispersion collapse.
      </div>
    </div>
  );
};
