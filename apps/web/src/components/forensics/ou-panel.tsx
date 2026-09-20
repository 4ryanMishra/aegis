import React from 'react';
import { ValidatorObservation, OUMetrics } from '@/lib/types';
import { TrendingDown, ShieldAlert, CheckCircle2, AlertOctagon, Info } from 'lucide-react';

interface OUPanelProps {
  validator: ValidatorObservation;
}

export const OUForensicPanel: React.FC<OUPanelProps> = ({ validator }) => {
  const metrics = (validator.intermediate_metrics || {}) as Partial<OUMetrics>;
  const isApplicable = metrics.is_applicable ?? (metrics.is_rwa && metrics.has_anchor);
  const threshold = metrics.jump_threshold ?? 3.5;
  const isJump = Boolean(metrics.is_jump_candidate || metrics.jump_candidate) || Math.abs(metrics.standardized_residual || 0) >= threshold;

  if (!isApplicable) {
    return (
      <div className="space-y-4 text-xs">
        <div className="p-4 rounded border border-slate-200 bg-slate-50 text-slate-700 space-y-2">
          <div className="flex items-center space-x-2">
            <AlertOctagon className="w-4 h-4 text-slate-400" />
            <span className="font-bold uppercase tracking-wider text-xs text-slate-800">
              Lane 4 OU Jump-Diffusion Analysis: NOT APPLICABLE
            </span>
          </div>
          <p className="text-[11px] leading-relaxed text-slate-600">
            {metrics.not_applicable_reason || 
              'This asset is not an anchored Real World Asset (RWA) or lacks a verified off-chain redemption NAV reference. Lane 4 safely returns neutral, non-distorting observation telemetry.'}
          </p>
        </div>

        <div className="p-3 bg-white rounded border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase font-mono text-slate-500">Diagnostic Role: Structural RWA Check</div>
            <div className="text-sm font-mono font-bold text-slate-900 mt-0.5 tnum">
              STATUS: NOT APPLICABLE
            </div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">
              Lane 4 only evaluates assets with verifiable redemption anchors.
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase font-mono text-slate-500">Secondary Spot Reference</div>
            <div className="text-xs font-mono font-semibold text-slate-700 tnum">
              ${(metrics.spot_price ?? 0).toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 text-xs">
      {/* Header Banner */}
      <div className={`p-3 rounded border flex items-center justify-between ${
        isJump
          ? 'bg-amber-50/70 border-amber-300 text-amber-900'
          : 'bg-emerald-50/70 border-emerald-300 text-emerald-900'
      }`}>
        <div className="flex items-center space-x-2">
          {isJump ? <ShieldAlert className="w-4 h-4 text-amber-700" /> : <CheckCircle2 className="w-4 h-4 text-emerald-700" />}
          <div>
            <span className="font-bold uppercase tracking-wider text-[11px]">
              {isJump ? 'STRUCTURAL RESIDUAL ALERT / JUMP CANDIDATE' : 'OU SPREAD EQUILIBRIUM (STATIONARY DIFFUSION)'}
            </span>
            <div className="text-[10px] opacity-80 mt-0.5">
              Reason Code: <span className="font-mono font-semibold">{validator.reason_code}</span>
            </div>
          </div>
        </div>
        <div className="text-right font-mono">
          <div className="text-[10px] opacity-75">Standardized Residual z_OU</div>
          <div className={`text-sm font-bold tnum ${isJump ? 'text-amber-800' : 'text-slate-900'}`}>
            {(metrics.standardized_residual ?? -0.12).toFixed(2)} σ
          </div>
        </div>
      </div>

      {/* RWA Anchor & Spread Diagnostics */}
      <div className="bg-surfaceSubtle p-3 rounded border border-borderHairline space-y-3">
        <div className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <TrendingDown className="w-3.5 h-3.5 text-slate-500" />
          RWA Redemption Anchor vs Secondary Market Spread
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Secondary Spot Price</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              ${(metrics.spot_price ?? (validator.estimated_price ?? 0)).toFixed(2)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Physical NAV / Par Anchor</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              ${(metrics.anchor_price ?? 100.00).toFixed(2)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Log Spread S_t = ln(P/Anchor)</div>
            <div className={`font-mono font-bold mt-0.5 tnum ${Math.abs(metrics.log_spread ?? 0) > 0.05 ? 'text-amber-700' : 'text-slate-900'}`}>
              {((metrics.log_spread ?? -0.001) * 100).toFixed(2)}%
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Jump Threshold |z| ≥ {threshold.toFixed(1)}</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {isJump ? 'TRIPPED (JUMP)' : 'WITHIN BOUNDS'}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Reversion Speed θ</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {(metrics.theta ?? 0.15).toFixed(3)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Spread Volatility σ</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {(metrics.sigma ?? 0.02).toFixed(4)}
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Expected Spread E[S_t]</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {((metrics.expected_spread ?? 0.0) * 100).toFixed(2)}%
            </div>
          </div>
          <div className="p-2 bg-white rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 font-mono">Conditional Std σ_cond</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {((metrics.conditional_std ?? Math.sqrt(metrics.conditional_variance ?? 0.0003)) * 100).toFixed(2)}%
            </div>
          </div>
        </div>
      </div>

      {/* Valuation / Diagnostic Output */}
      <div className="p-3 bg-white rounded border border-slate-200 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase font-mono text-slate-500">Diagnostic Role: Structural RWA Spread Check</div>
          <div className="text-sm font-mono font-bold text-slate-900 mt-0.5 tnum">
            {metrics.standardized_residual != null
              ? `z_OU = ${(metrics.standardized_residual).toFixed(2)} σ`
              : 'Residual Analysis'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">
            Lane 4 does not output a spot price to P_DEC; feeds Evidence Engine directly.
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase font-mono text-slate-500">Secondary Spot vs Par Anchor</div>
          <div className="text-xs font-mono font-semibold text-slate-700 tnum">
            ${(metrics.spot_price ?? 0).toFixed(2)} / ${(metrics.anchor_price ?? 100).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Methodology Guardrail Note */}
      <div className="p-2.5 bg-slate-50 rounded border border-borderHairline text-slate-600 text-[11px] leading-relaxed">
        <div className="font-semibold text-slate-800 flex items-center gap-1 mb-0.5">
          <Info className="w-3 h-3 text-slate-500" />
          Lane 4 Security Role & Mathematical Bound:
        </div>
        Models the secondary market spread relative to physical redemption anchor via continuous-time Ornstein-Uhlenbeck mean reversion. If the standardized residual exceeds |z| ≥ {threshold.toFixed(1)} under the configured threshold, it flags a structural residual alert / jump candidate to trigger protective collateral actions in the Decision Engine.
      </div>
    </div>
  );
};
