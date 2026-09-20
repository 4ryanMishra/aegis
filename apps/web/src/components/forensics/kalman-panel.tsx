import React from 'react';
import { ValidatorObservation, KalmanMetrics } from '@/lib/types';
import { Activity, ShieldAlert, CheckCircle2, Sliders, Info } from 'lucide-react';

interface KalmanPanelProps {
  validator: ValidatorObservation;
}

export const KalmanForensicPanel: React.FC<KalmanPanelProps> = ({ validator }) => {
  const metrics = (validator.intermediate_metrics || {}) as Partial<KalmanMetrics>;
  const isGated = validator.decision === 'OBSERVATION_GATED' || validator.decision === 'INNOVATION_GATED' || (metrics.mahalanobis_d2 || 0) > (metrics.chi2_threshold || 6.635);

  return (
    <div className="space-y-4 text-xs">
      {/* Header Banner */}
      <div className={`p-3 rounded border flex items-center justify-between ${
        isGated
          ? 'bg-amber-50/70 border-amber-300 text-amber-900'
          : 'bg-emerald-50/70 border-emerald-300 text-emerald-900'
      }`}>
        <div className="flex items-center space-x-2">
          {isGated ? <ShieldAlert className="w-4 h-4 text-amber-700" /> : <CheckCircle2 className="w-4 h-4 text-emerald-700" />}
          <div>
            <span className="font-bold uppercase tracking-wider text-[11px]">
              {isGated ? 'INNOVATION GATED / TRANSIENT SPIKE REJECTED' : 'INNOVATION ACCEPTED / GAUSSIAN UPDATE APPLIED'}
            </span>
            <div className="text-[10px] opacity-80 mt-0.5">
              Reason Code: <span className="font-mono font-semibold">{validator.reason_code}</span>
            </div>
          </div>
        </div>
        <div className="text-right font-mono">
          <div className="text-[10px] opacity-75">Mahalanobis D²</div>
          <div className="text-sm font-bold tnum">{(metrics.mahalanobis_d2 ?? 0).toFixed(3)}</div>
        </div>
      </div>

      {/* State Estimation Breakdown */}
      <div className="bg-surfaceSubtle p-3 rounded border border-borderHairline space-y-3">
        <div className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <Sliders className="w-3.5 h-3.5 text-slate-500" />
          Filter Telemetry & Innovation Analysis
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Prior State x̂(t|t-1)</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              ${(metrics.prior_state ?? 0).toFixed(2)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Prior Covariance P(t|t-1)</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {(metrics.prior_covariance ?? 0).toFixed(4)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Measurement z(t)</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              ${(metrics.observation ?? (validator.estimated_price ?? metrics.prior_state ?? 0)).toFixed(2)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Innovation ν(t) = z - x̂</div>
            <div className={`font-mono font-bold mt-0.5 tnum ${Math.abs(metrics.innovation ?? 0) > 1.0 ? 'text-amber-700' : 'text-slate-900'}`}>
              {(metrics.innovation ?? 0) >= 0 ? '+' : ''}{(metrics.innovation ?? 0).toFixed(3)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Innovation Var S(t)</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {((metrics.innovation_variance ?? metrics.innovation_covariance) ?? 0).toFixed(4)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Kalman Gain K(t)</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {(metrics.kalman_gain ?? 0).toFixed(4)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">χ²(1, 0.99) Gate (α={metrics.alpha ?? 0.01})</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {(metrics.chi2_threshold ?? 6.635).toFixed(3)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Posterior Cov P(t|t)</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {(metrics.posterior_covariance ?? 0).toFixed(4)}
            </div>
          </div>
        </div>
      </div>

      {/* Posterior Valuation Result */}
      <div className="p-3 bg-white rounded border border-slate-200 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase font-mono text-slate-500">Posterior State Estimate</div>
          <div className="text-xl font-mono font-bold text-slate-900 tnum">
            {validator.estimated_price !== null && validator.estimated_price !== undefined ? `$${validator.estimated_price.toFixed(2)}` : '--'}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase font-mono text-slate-500">95% Uncertainty Confidence Band</div>
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
          Lane 1 Security Role:
        </div>
        Rejects single-tick flash spikes before they corrupt downstream state. When Mahalanobis distance D² = ν²/S exceeds the χ²(1, 0.99) critical threshold ({(metrics.chi2_threshold ?? 6.635).toFixed(3)} at α={metrics.alpha ?? 0.01}), the filter gates the observation to prevent anomalous contamination.
      </div>
    </div>
  );
};
