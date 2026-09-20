import React from 'react';
import { SimulationSnapshot, TimelineMarker } from '@/lib/types';
import { Clock, Play, Pause, AlertTriangle, ShieldCheck, ShieldAlert, FastForward, RotateCcw, CheckCircle2 } from 'lucide-react';

interface SimulationTimelineProps {
  snapshot: SimulationSnapshot;
  onTogglePlay?: () => void;
  onStep?: () => void;
  onReset?: () => void;
  onFinalize?: () => void;
}

export const SimulationTimeline: React.FC<SimulationTimelineProps> = ({
  snapshot,
  onTogglePlay,
  onStep,
  onReset,
  onFinalize,
}) => {
  const tSec = snapshot.simulation_time_seconds || 0;
  const duration = snapshot.window_duration_seconds || 3600;
  const progressPct = Math.min(100, Math.max(0, (tSec / duration) * 100));
  const isRunning = snapshot.is_running;
  const isFinalized = snapshot.is_finalized;

  const decisionState = snapshot.decision?.state || 'HEALTHY_CONSENSUS';
  const protocolState = snapshot.decision?.protocol_state || 'NORMAL';

  // Dynamic color theme based on active authoritative protocol state
  const getProgressColor = () => {
    if (protocolState === 'HALTED' || decisionState === 'ORACLE_INSTABILITY' || decisionState === 'NO_CONSENSUS') {
      return 'bg-rose-600';
    }
    if (protocolState === 'RESTRICTED' || decisionState === 'MULTIPLI_DEVIATION') {
      return 'bg-amber-500';
    }
    return 'bg-emerald-600';
  };

  const getTrackBorderColor = () => {
    if (protocolState === 'HALTED') return 'border-rose-200 bg-rose-50/30';
    if (protocolState === 'RESTRICTED') return 'border-amber-200 bg-amber-50/30';
    return 'border-borderHairline bg-surface';
  };

  const markers: TimelineMarker[] = snapshot.timeline_markers || [
    { time_seconds: 0, time_formatted: "00:00", title: "T+00 START", description: "Verification Window Opens", severity: "INFO" },
    { time_seconds: 900, time_formatted: "15:00", title: "T+15 MID-1", description: "Consensus Clustering Check", severity: "INFO" },
    { time_seconds: 1800, time_formatted: "30:00", title: "T+30 MID-2", description: "Multipli Deviation Check", severity: "INFO" },
    { time_seconds: 2700, time_formatted: "45:00", title: "T+45 MID-3", description: "Market Triangulation", severity: "INFO" },
    { time_seconds: 3600, time_formatted: "60:00", title: "T+60 FINAL", description: "Settlement Finalization", severity: "SUCCESS" },
  ];

  const ticks = [
    { label: '0m', timeFormatted: 'T+00:00', pct: 0 },
    { label: '15m', timeFormatted: 'T+15:00', pct: 25 },
    { label: '30m', timeFormatted: 'T+30:00', pct: 50 },
    { label: '45m', timeFormatted: 'T+45:00', pct: 75 },
    { label: '60m', timeFormatted: 'T+60:00', pct: 100 },
  ];

  return (
    <div className={`border rounded shadow-card p-4 transition-all duration-300 ${getTrackBorderColor()}`}>
      
      {/* Top Meta Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div className="flex items-center space-x-2.5">
          <Clock className={`w-4 h-4 ${isRunning ? 'text-blue-600 animate-pulse' : 'text-slate-500'}`} />
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-xs uppercase tracking-wider text-slate-900 font-mono">
                SIMULATION TIMELINE &amp; VERIFICATION WINDOW
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-600 font-bold">
                {snapshot.speed_multiplier}x ACCELERATED
              </span>
              {isRunning && (
                <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  PLAYHEAD ADVANCING
                </span>
              )}
            </div>
            <p className="text-[11px] text-secondaryText">
              Deterministic 60-minute oracle verification progression (1 real second &approx; {snapshot.speed_multiplier} simulated seconds)
            </p>
          </div>
        </div>

        {/* Current Time Clock Display */}
        <div className="flex items-center space-x-3 text-right">
          <div className="font-mono text-xs">
            <span className="text-slate-400 font-medium">SIM TIME: </span>
            <span className="font-bold text-slate-900 text-sm bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              T+{snapshot.simulation_time_formatted}
            </span>
            <span className="text-slate-400 font-medium ml-1.5">/ T+60:00 ({progressPct.toFixed(1)}%)</span>
          </div>

          {/* Quick Step Button */}
          {onStep && (
            <button
              onClick={onStep}
              disabled={isFinalized}
              title="Debug: Step ahead by +15 simulated minutes"
              className="text-[11px] font-mono px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-300 font-semibold flex items-center gap-1 transition"
            >
              <FastForward className="w-3 h-3" />
              <span>+15m</span>
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar with Moving Playhead */}
      <div className="relative my-6 px-1">
        
        {/* Base Track */}
        <div className="h-3 w-full bg-slate-200 rounded-full overflow-hidden relative shadow-inner">
          {/* Active Fill */}
          <div
            className={`h-full transition-all duration-300 ${getProgressColor()}`}
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Moving Playhead Marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-20 transition-all duration-300 pointer-events-none"
          style={{ left: `${progressPct}%` }}
        >
          <div className="flex flex-col items-center">
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-900 text-white shadow-md mb-1 whitespace-nowrap">
              ● T+{snapshot.simulation_time_formatted}
            </span>
            <div className={`w-4 h-4 rounded-full border-2 border-white shadow-md ${getProgressColor()} ${isRunning ? 'animate-ping' : ''}`} />
          </div>
        </div>

        {/* 5 Major Interval Tick Lines */}
        <div className="absolute top-0 left-0 w-full h-3 pointer-events-none flex justify-between px-0.5">
          {ticks.map((t) => (
            <div
              key={t.label}
              className="w-0.5 h-full bg-white/80"
              style={{ left: `${t.pct}%` }}
            />
          ))}
        </div>

      </div>

      {/* Milestones / Event Markers Strip */}
      <div className="grid grid-cols-5 gap-1.5 pt-2 border-t border-slate-100 text-xs font-mono">
        {markers.slice(0, 5).map((m, idx) => {
          const isPassed = tSec >= m.time_seconds;
          const isCurrent = tSec >= m.time_seconds && (idx === markers.length - 1 || tSec < markers[idx + 1].time_seconds);

          let badgeColor = 'bg-slate-50 text-slate-500 border-slate-200';
          if (isPassed) {
            if (m.severity === 'CRITICAL') badgeColor = 'bg-rose-100 text-rose-800 border-rose-300 font-bold';
            else if (m.severity === 'ALERT') badgeColor = 'bg-amber-100 text-amber-800 border-amber-300 font-bold';
            else if (m.severity === 'WARNING') badgeColor = 'bg-amber-50 text-amber-700 border-amber-200 font-semibold';
            else if (m.severity === 'SUCCESS') badgeColor = 'bg-emerald-100 text-emerald-800 border-emerald-300 font-bold';
            else badgeColor = 'bg-blue-50 text-blue-800 border-blue-200 font-semibold';
          }

          return (
            <div
              key={idx}
              className={`p-2 rounded border transition-all ${badgeColor} ${
                isCurrent ? 'ring-2 ring-slate-900 ring-offset-1 shadow-sm' : ''
              }`}
            >
              <div className="flex items-center justify-between text-[10px] mb-0.5">
                <span className="font-bold">{m.time_formatted}</span>
                {isPassed && <CheckCircle2 className="w-2.5 h-2.5 shrink-0" />}
              </div>
              <div className="font-bold text-[11px] truncate" title={m.title}>
                {m.title}
              </div>
              <div className="text-[9px] text-slate-500 font-sans truncate mt-0.5" title={m.description}>
                {m.description}
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
};
