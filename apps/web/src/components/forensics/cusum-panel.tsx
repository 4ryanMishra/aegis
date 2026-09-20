import React from 'react';
import { ValidatorObservation, CUSUMMetrics } from '@/lib/types';
import { LineChart, ShieldAlert, CheckCircle2, TrendingUp, Info } from 'lucide-react';

interface CUSUMPanelProps {
  validator: ValidatorObservation;
}

export const CUSUMForensicPanel: React.FC<CUSUMPanelProps> = ({ validator }) => {
  const metrics = (validator.intermediate_metrics || {}) as Partial<CUSUMMetrics>;
  const thresholdH = metrics.threshold_h ?? 4.0;
  const sPlus = metrics.s_pos ?? (metrics as any).s_plus ?? 0.0;
  const sMinus = metrics.s_neg ?? (metrics as any).s_minus ?? 0.0;
  const isDrift = Boolean(metrics.drift_detected) || sPlus >= thresholdH || sMinus >= thresholdH;
  const trajectory = metrics.recent_trajectory || [0.0, 0.2, 0.4, 0.8, 1.2, 1.8, 2.5, 3.2, sPlus];
  const stepIncrement = metrics.standardized_increment ?? (metrics as any).current_increment ?? 0.0;
  const tickVol = metrics.tick_volatility ?? metrics.baseline_std ?? 0.35;
  const kappa = metrics.drift_kappa ?? (metrics as any).kappa ?? 0.5;

  return (
    <div className="space-y-4 text-xs">
      {/* Header Banner */}
      <div className={`p-3 rounded border flex items-center justify-between ${
        isDrift
          ? 'bg-amber-50/70 border-amber-300 text-amber-900'
          : 'bg-emerald-50/70 border-emerald-300 text-emerald-900'
      }`}>
        <div className="flex items-center space-x-2">
          {isDrift ? <ShieldAlert className="w-4 h-4 text-amber-700" /> : <CheckCircle2 className="w-4 h-4 text-emerald-700" />}
          <div>
            <span className="font-bold uppercase tracking-wider text-[11px]">
              {isDrift ? 'PERSISTENT LATENT DRIFT DETECTED (PAGE CUSUM ALARM)' : 'DRIFT ABSENT / SEQUENTIAL ACCUMULATOR STABLE'}
            </span>
            <div className="text-[10px] opacity-80 mt-0.5">
              Reason Code: <span className="font-mono font-semibold">{validator.reason_code}</span>
            </div>
          </div>
        </div>
        <div className="text-right font-mono">
          <div className="text-[10px] opacity-75">Upward Accumulator S⁺</div>
          <div className={`text-sm font-bold tnum ${isDrift ? 'text-amber-800' : 'text-slate-900'}`}>
            {sPlus.toFixed(2)} / {thresholdH.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Accumulator Diagnostics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Tick Volatility σ</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            ${tickVol.toFixed(4)}
          </div>
        </div>
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Step Increment y_k</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            {stepIncrement >= 0 ? '+' : ''}{stepIncrement.toFixed(2)} σ
          </div>
        </div>
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Drift Allowance κ</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            {kappa.toFixed(2)} σ
          </div>
        </div>
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 font-mono">Decision Threshold h</div>
          <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
            {thresholdH.toFixed(1)} σ
          </div>
        </div>
      </div>

      {/* Interactive Accumulator Trajectory SVG Chart */}
      <div className="bg-surface border border-borderHairline rounded p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-1.5 font-semibold text-slate-700 text-[11px] uppercase tracking-wider">
            <LineChart className="w-3.5 h-3.5 text-slate-500" />
            <span>Sequential Accumulator Trajectory S⁺(t) vs Alarm Threshold h</span>
          </div>
          <span className="font-mono text-[10px] text-slate-500">
            History: {metrics.history_length ?? trajectory.length} observations
          </span>
        </div>

        {/* SVG Sparkline */}
        <div className="h-28 w-full relative bg-slate-50/50 rounded border border-slate-100 p-2">
          <svg className="w-full h-full overflow-visible" viewBox="0 0 400 100" preserveAspectRatio="none">
            {/* Threshold Line */}
            <line
              x1="0"
              y1="20"
              x2="400"
              y2="20"
              stroke="#ef4444"
              strokeDasharray="4 4"
              strokeWidth="1.5"
            />
            <text x="395" y="15" textAnchor="end" fill="#ef4444" fontSize="9" fontFamily="monospace" fontWeight="bold">
              h = {thresholdH.toFixed(1)}
            </text>

            {/* Zero Base Line */}
            <line
              x1="0"
              y1="90"
              x2="400"
              y2="90"
              stroke="#cbd5e1"
              strokeWidth="1"
            />
            <text x="5" y="98" fill="#94a3b8" fontSize="8" fontFamily="monospace">
              0.0
            </text>

            {/* Trajectory Polyline */}
            {trajectory.length > 1 && (
              <polyline
                fill="none"
                stroke={isDrift ? '#d97706' : '#2563eb'}
                strokeWidth="2.5"
                points={trajectory
                  .map((val, idx) => {
                    const x = (idx / (trajectory.length - 1)) * 400;
                    // Scale: 0 -> y=90, thresholdH (4.0) -> y=20
                    const y = Math.max(5, 90 - (val / (thresholdH * 1.2)) * 80);
                    return `${x},${y}`;
                  })
                  .join(' ')}
              />
            )}

            {/* Trajectory Points */}
            {trajectory.map((val, idx) => {
              const x = (idx / (trajectory.length - 1)) * 400;
              const y = Math.max(5, 90 - (val / (thresholdH * 1.2)) * 80);
              return (
                <circle
                  key={idx}
                  cx={x}
                  cy={y}
                  r="3"
                  fill={val >= thresholdH ? '#ef4444' : isDrift ? '#d97706' : '#2563eb'}
                />
              );
            })}
          </svg>
        </div>

        <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-slate-500">
          <span>Window Start (t-History)</span>
          <span className={isDrift ? 'text-amber-800 font-bold' : 'text-slate-700 font-bold'}>
            Current S⁺ = {sPlus.toFixed(2)} ({isDrift ? 'THRESHOLD BREACHED' : 'SUB-THRESHOLD'})
          </span>
          <span>Observation T(now)</span>
        </div>
      </div>

      {/* Diagnostic Sequential Drift Output */}
      <div className="p-3 bg-white rounded border border-slate-200 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase font-mono text-slate-500">Diagnostic Role: Sequential Drift Detector</div>
          <div className="text-sm font-mono font-bold text-slate-900 mt-0.5 tnum">
            {`S⁺ = ${sPlus.toFixed(2)} (Threshold h = ${thresholdH.toFixed(1)})`}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">
            Lane 5 does not output a spot price to P_DEC; feeds Evidence Engine directly.
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase font-mono text-slate-500">Monitoring Regime</div>
          <div className="text-xs font-mono font-semibold text-slate-700 tnum">
            {isDrift ? 'ACCUMULATOR TRIPPED' : 'STATIONARY NOISE'}
          </div>
        </div>
      </div>

      {/* Methodology Guardrail Note */}
      <div className="p-2.5 bg-slate-50 rounded border border-borderHairline text-slate-600 text-[11px] leading-relaxed">
        <div className="font-semibold text-slate-800 flex items-center gap-1 mb-0.5">
          <Info className="w-3 h-3 text-slate-500" />
          Lane 5 Security Role & Mathematical Bound:
        </div>
        Detects persistent small-magnitude price drift (stealth manipulation). Single-tick deviation filters miss insidious +0.2% tick creeping, but Page CUSUM accumulates standardized price increments over time: S⁺ = max(0, S⁺_{'{k-1}'} + y_k - κ) with y_k = (P_k - P_{'{k-1}'}) / σ_k, triggering an early alarm when persistent directional increments cross h=4.0.
      </div>
    </div>
  );
};
