import React from 'react';
import { ScenarioRecord } from '@/lib/types';
import { Clock, CheckCircle2, Circle } from 'lucide-react';

interface VerificationTimelineProps {
  scenario: ScenarioRecord;
}

export const VerificationTimeline: React.FC<VerificationTimelineProps> = ({ scenario }) => {
  const { window, validators } = scenario;
  const elapsedMinutes = Math.round(window.elapsed_seconds / 60);
  const progressPercent = Math.min(100, Math.round((window.elapsed_seconds / window.duration_seconds) * 100));

  const milestones = [
    { minute: 0, label: 'T0: OSM Value Queued', desc: `$${scenario.p_osm.value.toFixed(2)} arrival` },
    { minute: 15, label: 'T+15m: Validator 1 Inflow', desc: 'Mean-reversion estimate' },
    { minute: 30, label: 'T+30m: Validator 2 Inflow', desc: 'Momentum indicator' },
    { minute: 40, label: 'T+40m: Validator 3 Inflow', desc: 'Cross-DEX VWAP' },
    { minute: 45, label: 'T+45m: Quorum Reached', desc: 'P_DEC median locked' },
    { minute: 60, label: 'T1: Final Valuation', desc: 'Market observed & settled' },
  ];

  return (
    <div className="bg-surface border border-borderHairline rounded p-4 shadow-card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            1-Hour Verification Window Timeline
          </span>
        </div>
        <div className="flex items-center space-x-3 text-xs font-mono">
          <span className="text-slate-500">Elapsed:</span>
          <span className="font-bold text-slate-900">{elapsedMinutes} / 60 min ({progressPercent}%)</span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
            window.is_finalized
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-blue-50 text-blue-700 border border-blue-200 animate-pulse'
          }`}>
            {window.is_finalized ? 'WINDOW FINALIZED' : 'VERIFICATION IN PROGRESS'}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative w-full h-2 bg-slate-100 rounded-full overflow-hidden mb-6">
        <div 
          className="h-full bg-slate-900 transition-all duration-300"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Milestone Points */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
        {milestones.map((m, idx) => {
          const isPassed = elapsedMinutes >= m.minute;
          const isCurrent = elapsedMinutes >= m.minute && (idx === milestones.length - 1 || elapsedMinutes < milestones[idx + 1].minute);

          return (
            <div 
              key={m.minute}
              className={`p-2 rounded border text-left transition ${
                isCurrent
                  ? 'border-blue-400 bg-blue-50/40 shadow-sm'
                  : isPassed
                  ? 'border-slate-200 bg-slate-50/50 text-slate-800'
                  : 'border-dashed border-slate-200 text-slate-400 bg-transparent'
              }`}
            >
              <div className="flex items-center space-x-1 mb-1">
                {isPassed ? (
                  <CheckCircle2 className={`w-3 h-3 ${isCurrent ? 'text-blue-600' : 'text-slate-700'}`} />
                ) : (
                  <Circle className="w-3 h-3 text-slate-300" />
                )}
                <span className="text-[11px] font-bold font-mono">
                  {m.minute === 0 ? 'T0' : m.minute === 60 ? 'T1' : `+${m.minute}m`}
                </span>
              </div>
              <div className="text-[11px] font-medium leading-tight truncate" title={m.label}>
                {m.label.split(': ')[1] || m.label}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5 truncate">
                {m.desc}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
