import React from 'react';
import { ScenarioRecord } from '@/lib/types';
import { Clock, CheckCircle2, Circle } from 'lucide-react';

interface VerificationTimelineProps {
  scenario: ScenarioRecord;
}

export const VerificationTimeline: React.FC<VerificationTimelineProps> = ({ scenario }) => {
  const { window } = scenario;
  const elapsedMinutes = Math.round(window.elapsed_seconds / 60);
  const progressPercent = Math.min(100, Math.round((window.elapsed_seconds / window.duration_seconds) * 100));

  const milestones = [
    { minute: 0, label: 'T0: P_OSM Arrival', desc: `Queued $${scenario.p_osm.value.toFixed(2)}` },
    { minute: 15, label: 'T+15m: 5 Lanes Compute', desc: 'Kalman, Huber, JSD, OU, CUSUM' },
    { minute: 30, label: 'T+30m: Commit/Reveal', desc: 'Evidence ingestion & hash match' },
    { minute: 45, label: 'T+45m: P_DEC Aggregation', desc: 'Uncertainty-weighted median' },
    { minute: 50, label: 'T+50m: Evidence Engine', desc: 'Triangulation & conflict check' },
    { minute: 60, label: 'T1: Decision & P_FINAL', desc: 'Protocol interface updated' },
  ];

  return (
    <div className="bg-surface border border-borderHairline rounded p-4 shadow-card">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-3 gap-2">
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Canonical Verification Window Progression (60-Minute Lifecycle)
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
      <div className="relative w-full h-2 bg-slate-100 rounded-full overflow-hidden mb-5">
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
              className={`p-2.5 rounded border text-left transition ${
                isCurrent
                  ? 'border-blue-400 bg-blue-50/40 shadow-xs'
                  : isPassed
                  ? 'border-slate-200 bg-slate-50/50 text-slate-800'
                  : 'border-dashed border-slate-200 text-slate-400 bg-transparent'
              }`}
            >
              <div className="flex items-center space-x-1.5 mb-1">
                {isPassed ? (
                  <CheckCircle2 className={`w-3.5 h-3.5 ${isCurrent ? 'text-blue-600' : 'text-slate-700'}`} />
                ) : (
                  <Circle className="w-3.5 h-3.5 text-slate-300" />
                )}
                <span className="text-[11px] font-bold font-mono">
                  {m.minute === 0 ? 'T0' : m.minute === 60 ? 'T1' : `+${m.minute}m`}
                </span>
              </div>
              <div className="text-[11px] font-semibold leading-tight text-slate-900 truncate" title={m.label}>
                {m.label.split(': ')[1] || m.label}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5 truncate" title={m.desc}>
                {m.desc}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
