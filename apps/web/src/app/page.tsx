'use client';

import React, { useState, useEffect } from 'react';
import { ScenarioRecord, ScenarioListItem, ValidatorObservation } from '@/lib/types';
import { fetchScenarios, runScenario } from '@/lib/api-client';
import { TerminalHeader } from '@/components/terminal-header';
import { OracleStrip } from '@/components/oracle-strip';
import { VerificationTimeline } from '@/components/verification-timeline';
import { ValidatorMatrix } from '@/components/validator-matrix';
import { ComparisonChart } from '@/components/comparison-chart';
import { DecisionPanel } from '@/components/decision-panel';
import { ProvenanceDrawer } from '@/components/provenance-drawer';

export default function RiskTerminalPage() {
  const [scenarios, setScenarios] = useState<ScenarioListItem[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('scen_normal_consensus');
  const [currentScenario, setCurrentScenario] = useState<ScenarioRecord | null>(null);
  const [ltv, setLtv] = useState<number>(0.60);
  const [stepSeconds, setStepSeconds] = useState<number>(3600);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [inspectTarget, setInspectTarget] = useState<string | ValidatorObservation | null>(null);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load scenarios on mount
  useEffect(() => {
    async function init() {
      try {
        setErrorMsg(null);
        const list = await fetchScenarios();
        setScenarios(list);
        if (list.length > 0) {
          setSelectedScenarioId(list[0].scenario_id);
        }
      } catch (err: any) {
        console.error('Failed to init scenarios:', err);
        setErrorMsg(err?.message || 'Failed to connect to backend on http://127.0.0.1:8000');
      }
    }
    init();
  }, []);

  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  // Run simulation when scenario, LTV, step, or manual trigger changes
  useEffect(() => {
    async function loadData() {
      if (!selectedScenarioId) return;
      setIsLoading(true);
      try {
        setErrorMsg(null);
        const record = await runScenario(selectedScenarioId, ltv, stepSeconds);
        setCurrentScenario(record);
      } catch (err: any) {
        console.error('Failed to run scenario:', err);
        setErrorMsg(err?.message || 'Failed to execute scenario verification');
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [selectedScenarioId, ltv, stepSeconds, refreshTrigger]);

  const handleReset = () => {
    setStepSeconds(0);
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleStep = () => {
    setStepSeconds((prev) => {
      const next = Math.min(3600, prev + 900);
      return next === prev && prev < 3600 ? prev + 900 : (prev >= 3600 ? 900 : next);
    });
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleFinalize = () => {
    setStepSeconds(3600); // 60 min
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleInspect = (target: string | ValidatorObservation) => {
    setInspectTarget(target);
    setIsDrawerOpen(true);
  };

  if (errorMsg && !currentScenario) {
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

  if (!currentScenario) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-xs font-mono text-slate-500">
        INITIALIZING AEGIS VERIFICATION RUNTIME...
      </div>
    );
  }

  const elapsedMinutes = Math.round(currentScenario.window.elapsed_seconds / 60);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      
      {/* Top Application Header */}
      <TerminalHeader
        scenarios={scenarios}
        selectedScenarioId={selectedScenarioId}
        onSelectScenario={(id) => {
          setSelectedScenarioId(id);
          setStepSeconds(3600);
        }}
        ltv={ltv}
        onChangeLtv={setLtv}
        onReset={handleReset}
        onStep={handleStep}
        onFinalize={handleFinalize}
        elapsedMinutes={elapsedMinutes}
        isFinalized={currentScenario.window.is_finalized}
        isLoading={isLoading}
      />

      {/* Main Terminal Workspace */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-6 space-y-5">
        
        {/* Scenario Overview Banner */}
        <div className="bg-surface border border-borderHairline p-3.5 rounded flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-900 text-sm">{currentScenario.title}</span>
              <span className="font-mono text-slate-500">[{currentScenario.asset}]</span>
            </div>
            <p className="text-secondaryText mt-0.5 leading-relaxed">
              {currentScenario.description}
            </p>
          </div>
          <div className="text-[11px] font-mono text-slate-500 bg-slate-50 px-3 py-1.5 rounded border border-borderHairline whitespace-nowrap">
            WINDOW ID: {currentScenario.scenario_id}
          </div>
        </div>

        {/* 1. Oracle State Strip */}
        <OracleStrip
          scenario={currentScenario}
          onInspect={handleInspect}
        />

        {/* 2. Verification Window Progression Timeline */}
        <VerificationTimeline
          scenario={currentScenario}
        />

        {/* 3. Main Operational Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          {/* Left Column: Validator Matrix & Valuation Chart (7 cols) */}
          <div className="lg:col-span-7 space-y-5">
            <ValidatorMatrix
              validators={currentScenario.validators}
              onInspectValidator={handleInspect}
            />
            <ComparisonChart
              scenario={currentScenario}
            />
          </div>

          {/* Right Column: Evidence Engine & Collateral Impact (5 cols) */}
          <div className="lg:col-span-5">
            <DecisionPanel
              scenario={currentScenario}
            />
          </div>

        </div>

      </main>

      {/* Provenance Audit Drawer */}
      <ProvenanceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        inspectTarget={inspectTarget}
        scenario={currentScenario}
      />

      {/* Footer */}
      <footer className="border-t border-borderHairline bg-surface px-6 py-3 text-[11px] text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <span className="font-bold text-slate-800 font-mono">AEGIS v0.1.0-mvp</span>
          <span>&bull;</span>
          <span>Rethinking Blockchain Oracles Research Prototype</span>
        </div>
        <div className="flex items-center space-x-4">
          <span className="font-mono">P_OSM: Baseline</span>
          <span className="font-mono">P_DEC: Validator Aggregate</span>
          <span className="font-mono">P_MARKET: Off-Chain Observation</span>
        </div>
      </footer>

    </div>
  );
}
