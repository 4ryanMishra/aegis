'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  ScenarioListItem,
  ValidatorObservation,
  SimulationSnapshot,
  ScenarioRecord,
} from '@/lib/types';
import {
  fetchScenarios,
  fetchSimulationState,
  startSimulation,
  pauseSimulation,
  resetSimulation,
  stepSimulation,
  finalizeSimulation,
  configSimulation,
  updateSimulationPosition,
} from '@/lib/api-client';
import { TerminalHeader } from '@/components/terminal-header';
import { OracleStrip } from '@/components/oracle-strip';
import { VerificationTimeline } from '@/components/verification-timeline';
import { ValidatorMatrix } from '@/components/validator-matrix';
import { ComparisonChart } from '@/components/comparison-chart';
import { DecisionPanel } from '@/components/decision-panel';
import { ProvenanceDrawer } from '@/components/provenance-drawer';
import { LiveEventFeed } from '@/components/live-event-feed';
import { SystemInterpretation } from '@/components/system-interpretation';
import { UserPositionCard } from '@/components/user-position-card';
import { CausalChainPanel } from '@/components/causal-chain-panel';

export default function RiskTerminalPage() {
  const [scenarios, setScenarios] = useState<ScenarioListItem[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('scen_normal');
  const [snapshot, setSnapshot] = useState<SimulationSnapshot | null>(null);
  const [ltv, setLtv] = useState<number>(0.80);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(60);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [inspectTarget, setInspectTarget] = useState<string | ValidatorObservation | null>(null);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load scenarios and initial simulation state on mount
  useEffect(() => {
    async function init() {
      try {
        setErrorMsg(null);
        const [list, initialState] = await Promise.all([
          fetchScenarios(),
          fetchSimulationState().catch(() => null),
        ]);
        setScenarios(list);
        if (initialState) {
          setSnapshot(initialState);
          setSelectedScenarioId(initialState.scenario_id);
          setLtv(initialState.ltv);
          setSpeedMultiplier(initialState.speed_multiplier);
        } else if (list.length > 0) {
          setSelectedScenarioId(list[0].scenario_id);
          if (list[0].ltv_default) setLtv(list[0].ltv_default);
          const fresh = await resetSimulation(list[0].scenario_id, list[0].ltv_default || 0.80);
          setSnapshot(fresh);
        }
      } catch (err: any) {
        console.error('Failed to init scenarios:', err);
        setErrorMsg(err?.message || 'Failed to connect to backend on http://127.0.0.1:8000');
      }
    }
    init();
  }, []);

  // Continuous Simulation Polling Loop
  // Polls backend snapshot every 600ms when is_running is true
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    if (snapshot?.is_running && !snapshot?.is_finalized) {
      intervalId = setInterval(async () => {
        try {
          const freshState = await fetchSimulationState();
          setSnapshot(freshState);
        } catch (err) {
          console.error('Simulation poll error:', err);
        }
      }, 600);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [snapshot?.is_running, snapshot?.is_finalized]);

  // Handler: Start / Pause Toggle
  const handleTogglePlay = async () => {
    if (!snapshot) return;
    try {
      if (snapshot.is_running) {
        const fresh = await pauseSimulation();
        setSnapshot(fresh);
      } else {
        const fresh = await startSimulation();
        setSnapshot(fresh);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to toggle simulation play state');
    }
  };

  // Handler: Reset Simulation
  const handleReset = async () => {
    setIsLoading(true);
    try {
      const fresh = await resetSimulation(selectedScenarioId, ltv);
      setSnapshot(fresh);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to reset simulation');
    } finally {
      setIsLoading(false);
    }
  };

  // Handler: Step +15m (Advanced Demo Control)
  const handleStep = async () => {
    setIsLoading(true);
    try {
      const fresh = await stepSimulation(900.0);
      setSnapshot(fresh);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to step simulation');
    } finally {
      setIsLoading(false);
    }
  };

  // Handler: Finalize Window
  const handleFinalize = async () => {
    setIsLoading(true);
    try {
      const fresh = await finalizeSimulation();
      setSnapshot(fresh);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to finalize simulation');
    } finally {
      setIsLoading(false);
    }
  };

  // Handler: Scenario Selection
  const handleSelectScenario = async (id: string) => {
    setSelectedScenarioId(id);
    const matched = scenarios.find((s) => s.scenario_id === id);
    const newLtv = matched?.ltv_default || 0.80;
    setLtv(newLtv);
    setIsLoading(true);
    try {
      const fresh = await resetSimulation(id, newLtv);
      setSnapshot(fresh);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to switch scenario');
    } finally {
      setIsLoading(false);
    }
  };

  // Handler: Speed Change
  const handleChangeSpeed = async (speed: number) => {
    setSpeedMultiplier(speed);
    try {
      const fresh = await configSimulation(speed, selectedScenarioId, ltv);
      setSnapshot(fresh);
    } catch (err: any) {
      console.error('Failed to change speed:', err);
    }
  };

  // Handler: LTV Change
  const handleChangeLtv = async (newLtv: number) => {
    setLtv(newLtv);
    try {
      const fresh = await configSimulation(speedMultiplier, selectedScenarioId, newLtv);
      setSnapshot(fresh);
    } catch (err: any) {
      console.error('Failed to change LTV:', err);
    }
  };

  // Handler: Position Updates (Deposit / Borrow)
  const handleUpdatePosition = async (collateralAmount?: number, debtAmount?: number, setMaxBorrow?: boolean) => {
    try {
      const fresh = await updateSimulationPosition(collateralAmount, debtAmount, setMaxBorrow);
      setSnapshot(fresh);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to update position');
    }
  };

  const handleInspect = (target: string | ValidatorObservation) => {
    setInspectTarget(target);
    setIsDrawerOpen(true);
  };

  if (errorMsg && !snapshot) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center">
        <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg max-w-lg shadow-sm">
          <p className="font-semibold text-sm mb-1">AEGIS Backend Connection Error</p>
          <p className="font-mono text-xs text-red-600 mb-4">{errorMsg}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-medium rounded transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-xs font-mono text-slate-500">
        INITIALIZING AEGIS VERIFICATION ENGINE RUNTIME...
      </div>
    );
  }

  // Cast snapshot to ScenarioRecord for child components that expect it
  const scenarioRecord: ScenarioRecord = {
    scenario_id: snapshot.scenario_id,
    title: snapshot.title,
    description: snapshot.description,
    asset: snapshot.asset,
    window: {
      start_ts: 1774000000,
      end_ts: 1774000000 + snapshot.window_duration_seconds,
      duration_seconds: snapshot.window_duration_seconds,
      elapsed_seconds: snapshot.simulation_time_seconds,
      is_finalized: snapshot.is_finalized,
    },
    p_osm: snapshot.p_osm,
    validators: snapshot.validators,
    p_dec: snapshot.p_dec,
    p_market: snapshot.p_market,
    evidence: snapshot.evidence,
    decision: snapshot.decision,
    collateral: snapshot.collateral,
    intermediate_telemetry: snapshot.lane_telemetry,
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      
      {/* Top Application Header */}
      <TerminalHeader
        scenarios={scenarios}
        selectedScenarioId={selectedScenarioId}
        onSelectScenario={handleSelectScenario}
        ltv={ltv}
        onChangeLtv={handleChangeLtv}
        onReset={handleReset}
        onStep={handleStep}
        onFinalize={handleFinalize}
        onTogglePlay={handleTogglePlay}
        isRunning={snapshot.is_running}
        isPaused={snapshot.is_paused}
        simulationTimeFormatted={snapshot.simulation_time_formatted}
        elapsedMinutes={snapshot.elapsed_minutes}
        speedMultiplier={speedMultiplier}
        onChangeSpeed={handleChangeSpeed}
        activeValidatorsCount={snapshot.active_validators_count}
        totalValidatorsCount={snapshot.total_validators_count}
        totalObservations={snapshot.total_observations}
        currentBlock={snapshot.current_block}
        isFinalized={snapshot.is_finalized}
        isLoading={isLoading}
      />

      {/* Main Terminal Workspace */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-6 space-y-5">
        
        {/* Scenario Overview Banner */}
        <div className="bg-surface border border-borderHairline p-3.5 rounded flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-900 text-sm">{snapshot.title}</span>
              <span className="font-mono text-slate-500">[{snapshot.asset}]</span>
            </div>
            <p className="text-secondaryText mt-0.5 leading-relaxed">
              {snapshot.description}
            </p>
          </div>
          <div className="text-[11px] font-mono text-slate-500 bg-slate-50 px-3 py-1.5 rounded border border-borderHairline whitespace-nowrap">
            WINDOW ID: {snapshot.scenario_id}
          </div>
        </div>

        {/* 1. Oracle State Strip */}
        <OracleStrip
          scenario={scenarioRecord}
          uncertaintyHalfWidth={snapshot.p_dec_uncertainty_half_width}
          onInspect={handleInspect}
        />

        {/* 2. Causal Chain Pipeline (Oracle Evidence -> Risk State -> Position Health) */}
        <CausalChainPanel
          snapshot={snapshot}
        />

        {/* 3. Verification Window Progression Timeline */}
        <VerificationTimeline
          scenario={scenarioRecord}
        />

        {/* 4. Main Operational Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          {/* Left Column: Collateral Position, Valuation Chart & Validator Matrix (7 cols) */}
          <div className="lg:col-span-7 space-y-5">
            
            {/* Downstream RWAUSD Collateral Vault Card */}
            <UserPositionCard
              position={snapshot.position}
              snapshot={snapshot}
              onUpdatePosition={handleUpdatePosition}
            />

            {/* Live Time Series Stream Chart */}
            <ComparisonChart
              scenario={scenarioRecord}
              timeSeries={snapshot.time_series}
              uncertaintyHalfWidth={snapshot.p_dec_uncertainty_half_width}
            />

            {/* Validator Matrix */}
            <ValidatorMatrix
              validators={scenarioRecord.validators}
              onInspectValidator={handleInspect}
            />

          </div>

          {/* Right Column: Interpretation, Live Events & Decision Panel (5 cols) */}
          <div className="lg:col-span-5 space-y-5">
            
            {/* Dynamic System Interpretation ("What Just Happened?") */}
            <SystemInterpretation
              interpretation={snapshot.interpretation}
              oracleStatus={snapshot.evidence.oracle_status}
              decision={snapshot.decision}
              collateral={snapshot.collateral}
              isFinalized={snapshot.is_finalized}
              simulationTimeFormatted={snapshot.simulation_time_formatted}
            />

            {/* Live Event Stream Panel */}
            <LiveEventFeed
              events={snapshot.events}
              isRunning={snapshot.is_running}
            />

            {/* Decision & Collateral Impact Panel */}
            <DecisionPanel
              scenario={scenarioRecord}
            />

          </div>

        </div>

      </main>

      {/* Provenance Audit Drawer */}
      <ProvenanceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        inspectTarget={inspectTarget}
        scenario={scenarioRecord}
      />

      {/* Footer */}
      <footer className="border-t border-borderHairline bg-surface px-6 py-3 text-[11px] text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <span className="font-bold text-slate-800 font-mono">AEGIS v0.1.0-mvp</span>
          <span>&bull;</span>
          <span>Adaptive Oracle Verification Engine Research Prototype</span>
        </div>
        <div className="flex items-center space-x-4 font-mono">
          <span>P_OSM: Baseline</span>
          <span>P_DEC: Validator Median</span>
          <span>P_MARKET: Off-Chain Observation</span>
        </div>
      </footer>

    </div>
  );
}
