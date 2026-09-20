import React from 'react';
import { SimulationEvent } from '@/lib/types';
import { Terminal, Shield, Activity, Radio, AlertCircle } from 'lucide-react';

interface LiveEventFeedProps {
  events: SimulationEvent[];
  isRunning: boolean;
}

export const LiveEventFeed: React.FC<LiveEventFeedProps> = ({ events, isRunning }) => {
  const getCategoryBadge = (cat: string, severity: string) => {
    switch (cat.toUpperCase()) {
      case 'MARKET':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'KALMAN':
        return 'bg-indigo-100 text-indigo-800 border-indigo-300';
      case 'HUBER':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'JSD':
        return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'OU':
        return 'bg-teal-100 text-teal-800 border-teal-300';
      case 'CUSUM':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'AGGREGATOR':
        return 'bg-cyan-100 text-cyan-800 border-cyan-300';
      case 'EVIDENCE':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'PROTOCOL':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  const getSeverityDot = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
      case 'ALERT':
        return 'bg-rose-500 animate-ping';
      case 'WARNING':
        return 'bg-amber-500';
      case 'SUCCESS':
        return 'bg-emerald-500';
      default:
        return 'bg-slate-400';
    }
  };

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4 flex flex-col h-[280px]">
      <div className="flex items-center justify-between pb-2.5 border-b border-borderHairline mb-2">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-slate-700" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
            Live Oracle Event Stream
          </h3>
        </div>
        <div className="flex items-center space-x-2 text-[10px] font-mono text-slate-500">
          {isRunning && (
            <span className="flex items-center gap-1 text-emerald-600 font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              STREAMING
            </span>
          )}
          <span>{events.length} events</span>
        </div>
      </div>

      {/* Scrollable Event List */}
      <div className="flex-1 overflow-y-auto font-mono text-[11px] space-y-1.5 pr-1 scrollbar-thin">
        {events.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-400 text-xs italic font-sans">
            Awaiting verification window events...
          </div>
        ) : (
          events.map((ev, idx) => (
            <div
              key={idx}
              className={`p-1.5 rounded flex items-start space-x-2 border transition ${
                idx === 0
                  ? 'bg-slate-50 border-slate-300 text-slate-900 shadow-2xs'
                  : 'bg-white/60 border-slate-100 text-slate-700'
              }`}
            >
              <span className="text-[10px] text-slate-400 font-mono whitespace-nowrap mt-0.5">
                {ev.timestamp}
              </span>
              <span
                className={`text-[9px] font-bold px-1.5 py-0.2 rounded border uppercase tracking-wider whitespace-nowrap ${getCategoryBadge(
                  ev.category,
                  ev.severity
                )}`}
              >
                {ev.category}
              </span>
              <span className="flex-1 leading-snug break-words">
                {ev.message}
              </span>
              <span
                className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${getSeverityDot(
                  ev.severity
                )}`}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
};
