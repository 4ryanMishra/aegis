import React from 'react';
import { ScenarioListItem } from '@/lib/types';
import { Play, Pause, RotateCcw, FastForward, CheckCircle2, Sliders, Activity, Clock, ShieldAlert, Cpu } from 'lucide-react';

interface TerminalHeaderProps {
  scenarios: ScenarioListItem[];
  selectedScenarioId: string;
  onSelectScenario: (id: string) => void;
  ltv: number;
  onChangeLtv: (ltv: number) => void;
  onReset: () => void;
  onStep: () => void;
  onFinalize: () => void;
  onTogglePlay: () => void;
  isRunning: boolean;
  isPaused: boolean;
  simulationTimeFormatted: string;
  elapsedMinutes: number;
  speedMultiplier: number;
  onChangeSpeed: (speed: number) => void;
  activeValidatorsCount: number;
  totalValidatorsCount: number;
  totalObservations: number;
  currentBlock: string;
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
  onTogglePlay,
  isRunning,
  isPaused,
  simulationTimeFormatted,
  elapsedMinutes,
  speedMultiplier,
  onChangeSpeed,
  activeValidatorsCount,
  totalValidatorsCount,
  totalObservations,
  currentBlock,
  isFinalized,
  isLoading,
}) => {
  return (
    <header className="bg-surface border-b border-borderHairline px-6 py-3 sticky top-0 z-30 shadow-subtle">
      <div className="max-w-[1600px] mx-auto flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3">
        
        {/* Brand & Live Telemetry Badges */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded bg-slate-900 flex items-center justify-center text-white font-bold text-sm tracking-wider shadow-sm">
              Æ
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base tracking-tight text-slate-900 font-mono">AEGIS</span>
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                  SIMULATED PROTOTYPE
                </span>
                {isRunning && (
                  <span className="inline-flex items-center gap-1 text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    LIVE MONITORING
                  </span>
                )}
              </div>
              <p className="text-[11px] text-secondaryText font-medium">
                Continuous Oracle Risk Engine & Valuation Triangulation
              </p>
            </div>
          </div>

          {/* Operational Telemetry Pill */}
          <div className="hidden lg:flex items-center space-x-3 bg-slate-50 border border-borderHairline rounded-md px-3 py-1.5 text-[11px] font-mono text-slate-600">
            <div className="flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-slate-400">WINDOW:</span>
              <span className="font-bold text-slate-900">{simulationTimeFormatted} / 60:00</span>
            </div>
            <span className="text-slate-300">|</span>
            <div className="flex items-center space-x-1.5">
              <Cpu className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-slate-400">NODES:</span>
              <span className="font-bold text-blue-700">{activeValidatorsCount}/{totalValidatorsCount} ACTIVE</span>
            </div>
            <span className="text-slate-300">|</span>
            <div className="flex items-center space-x-1.5">
              <Activity className="w-3.5 h-3.5 text-emerald-600" />
              <span className="text-slate-400">OBS:</span>
              <span className="font-bold text-slate-800">{totalObservations}</span>
            </div>
            <span className="text-slate-300">|</span>
            <span className="text-slate-500">{currentBlock}</span>
          </div>
        </div>

        {/* Controls & Configuration Bar */}
        <div className="flex flex-wrap items-center gap-2.5">
          
          {/* Scenario Selector */}
          <div className="flex items-center bg-surfaceSubtle border border-borderHairline rounded px-2.5 py-1.5">
            <label className="text-[11px] font-semibold text-slate-500 mr-2 uppercase tracking-wider">
              Scenario:
            </label>
            <select
              value={selectedScenarioId}
              onChange={(e) => onSelectScenario(e.target.value)}
              disabled={isLoading}
              className="bg-transparent text-xs font-semibold text-slate-900 focus:outline-none cursor-pointer max-w-[210px] truncate"
            >
              {scenarios.map((scen) => (
                <option key={scen.scenario_id} value={scen.scenario_id}>
                  {scen.title}
                </option>
              ))}
            </select>
          </div>

          {/* Speed Multiplier Selector */}
          <div className="flex items-center bg-surfaceSubtle border border-borderHairline rounded px-2 py-1 space-x-1 text-xs">
            <span className="text-[10px] font-semibold text-slate-500 uppercase">Speed:</span>
            {[30, 60, 120].map((spd) => (
              <button
                key={spd}
                onClick={() => onChangeSpeed(spd)}
                className={`px-1.5 py-0.5 text-[10px] font-mono rounded font-semibold transition ${
                  speedMultiplier === spd
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-200'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>

          {/* LTV Factor Setting */}
          <div className="flex items-center bg-surfaceSubtle border border-borderHairline rounded px-2.5 py-1.5 space-x-1.5">
            <Sliders className="w-3.5 h-3.5 text-slate-500" />
            <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
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
              className="w-14 h-1.5 bg-slate-300 rounded-lg appearance-none cursor-pointer accent-slate-900"
            />
          </div>

          {/* PRIMARY SIMULATION CONTROL BUTTONS */}
          <div className="flex items-center space-x-1.5 border-l border-borderHairline pl-2.5">
            
            {/* Start / Pause Continuous Simulation */}
            <button
              onClick={onTogglePlay}
              disabled={isLoading || isFinalized}
              title={isRunning ? "Pause continuous verification simulation" : "Start continuous real-time oracle verification"}
              className={`px-3 py-1.5 rounded transition text-xs flex items-center gap-1.5 font-bold shadow-sm ${
                isRunning
                  ? 'bg-amber-600 hover:bg-amber-700 text-white'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white'
              }`}
            >
              {isRunning ? (
                <>
                  <Pause className="w-3.5 h-3.5 fill-current" />
                  <span>PAUSE</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>START MONITORING</span>
                </>
              )}
            </button>

            {/* Reset */}
            <button
              onClick={onReset}
              disabled={isLoading}
              title="Reset simulation to T0"
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded border border-borderHairline transition text-xs flex items-center gap-1 font-medium"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Reset</span>
            </button>

            {/* Advance +15m Step (Advanced/Demo Control) */}
            <button
              onClick={onStep}
              disabled={isLoading || isFinalized}
              title="Advance verification window by +15 minutes (Demo Control)"
              className="px-2 py-1.5 text-slate-700 bg-white hover:bg-slate-50 rounded border border-borderHairline transition text-xs flex items-center gap-1 font-medium"
            >
              <FastForward className="w-3.5 h-3.5 text-blue-600" />
              <span>+15m</span>
            </button>

            {/* Finalize Window */}
            <button
              onClick={onFinalize}
              disabled={isLoading}
              title="Immediately resolve full 60-minute verification window"
              className="px-2.5 py-1.5 text-white bg-slate-900 hover:bg-slate-800 rounded transition text-xs flex items-center gap-1.5 font-semibold shadow-subtle"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>{isFinalized ? 'Finalized' : 'Finalize'}</span>
            </button>

          </div>

        </div>

      </div>
    </header>
  );
};
