import React from 'react';
import { ScenarioListItem } from '@/lib/types';
import { ShieldCheck, Play, RotateCcw, FastForward, Sliders } from 'lucide-react';

interface TerminalHeaderProps {
  scenarios: ScenarioListItem[];
  selectedScenarioId: string;
  onSelectScenario: (id: string) => void;
  ltv: number;
  onChangeLtv: (ltv: number) => void;
  onReset: () => void;
  onStep: () => void;
  onFinalize: () => void;
  elapsedMinutes: number;
  isFinalized: boolean;
  isLoading: boolean;
}

export const TerminalHeader: React.FC<TerminalHeaderProps> = ({
  scenarios,
  selectedScenarioId,
  onSelectScenario,
  ltv,
  onChangeLtv,
  onReset,
  onStep,
  onFinalize,
  elapsedMinutes,
  isFinalized,
  isLoading,
}) => {
  return (
    <header className="bg-surface border-b border-borderHairline px-6 py-3.5 sticky top-0 z-30 shadow-subtle">
      <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        
        {/* Brand & Environment */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded bg-slate-900 flex items-center justify-center text-white font-bold text-sm tracking-wider">
              Æ
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base tracking-tight text-slate-900 font-mono">AEGIS</span>
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                  SIMULATED PROTOTYPE
                </span>
              </div>
              <p className="text-xs text-secondaryText font-medium">
                Adaptive Oracle Verification & Collateral Risk Engine
              </p>
            </div>
          </div>
        </div>

        {/* Controls & Configuration Bar */}
        <div className="flex flex-wrap items-center gap-3">
          
          {/* Scenario Selector */}
          <div className="flex items-center bg-surfaceSubtle border border-borderHairline rounded px-2.5 py-1.5">
            <label className="text-xs font-semibold text-slate-500 mr-2 uppercase tracking-wider">
              Scenario:
            </label>
            <select
              value={selectedScenarioId}
              onChange={(e) => onSelectScenario(e.target.value)}
              disabled={isLoading}
              className="bg-transparent text-xs font-medium text-slate-900 focus:outline-none cursor-pointer max-w-[240px] truncate"
            >
              {scenarios.map((scen) => (
                <option key={scen.scenario_id} value={scen.scenario_id}>
                  {scen.title}
                </option>
              ))}
            </select>
          </div>

          {/* LTV Factor Setting */}
          <div className="flex items-center bg-surfaceSubtle border border-borderHairline rounded px-2.5 py-1.5 space-x-2">
            <Sliders className="w-3.5 h-3.5 text-slate-500" />
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              LTV:
            </label>
            <span className="text-xs font-mono font-bold text-slate-900">
              {Math.round(ltv * 100)}%
            </span>
            <input
              type="range"
              min="0.30"
              max="0.90"
              step="0.05"
              value={ltv}
              onChange={(e) => onChangeLtv(parseFloat(e.target.value))}
              className="w-16 h-1.5 bg-slate-300 rounded-lg appearance-none cursor-pointer accent-slate-900"
            />
          </div>

          {/* Verification Window Step Controls */}
          <div className="flex items-center space-x-1.5 border-l border-borderHairline pl-3">
            
            <button
              onClick={onReset}
              disabled={isLoading}
              title="Reset simulation to T0"
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded border border-borderHairline transition text-xs flex items-center gap-1 font-medium"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>T0 (Reset)</span>
            </button>

            <button
              onClick={onStep}
              disabled={isLoading}
              title="Advance verification window by +15 minutes"
              className="px-2.5 py-1.5 text-slate-700 bg-white hover:bg-slate-50 rounded border border-borderHairline transition text-xs flex items-center gap-1 font-medium"
            >
              <FastForward className="w-3.5 h-3.5 text-blue-600" />
              <span>+15m Step</span>
            </button>

            <button
              onClick={onFinalize}
              disabled={isLoading}
              title="Run complete 60-minute verification window and observe market"
              className="px-3 py-1.5 text-white bg-slate-900 hover:bg-slate-800 rounded transition text-xs flex items-center gap-1.5 font-medium shadow-subtle"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isFinalized ? 'Re-Finalize (1hr)' : 'Finalize Window (1hr)'}</span>
            </button>

          </div>

        </div>

      </div>
    </header>
  );
};
