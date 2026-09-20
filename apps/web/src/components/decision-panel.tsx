import React from 'react';
import { ScenarioRecord } from '@/lib/types';
import { ShieldAlert, CheckCircle2, AlertTriangle, Scale, FileText, Activity, ShieldCheck, Lock } from 'lucide-react';

interface DecisionPanelProps {
  scenario: ScenarioRecord;
}

export const DecisionPanel: React.FC<DecisionPanelProps> = ({ scenario }) => {
  const { evidence, decision, collateral, window } = scenario;

  const isFinalized = window.is_finalized;
  const isHealthy = evidence.oracle_status === 'HEALTHY_CONSENSUS';
  const hasInconsistency = evidence.oracle_status !== 'HEALTHY_CONSENSUS' && evidence.oracle_status !== 'PENDING_FINALIZATION';
  const laneAnomalies = evidence.lane_anomalies || {};

  const getDecisionBadge = () => {
    const dec = decision.decision || decision.policy;
    if (dec === 'HALTED' || dec === 'CIRCUIT_BREAKER_HALT') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-300">
          <Lock className="w-3.5 h-3.5 text-rose-600" />
          CIRCUIT BREAKER HALT
        </span>
      );
    }
    if (dec === 'RESTRICTED' || dec === 'RESTRICT_COLLATERAL_CEILING' || dec === 'DISPUTED') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-300">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          {String(dec).replace(/_/g, ' ')}
        </span>
      );
    }
    if (dec === 'VERIFIED') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          VERIFIED
        </span>
      );
    }
    return (
      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
        {String(dec).replace(/_/g, ' ')}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      
      {/* 1. Evidence Engine Summary */}
      <div className="bg-surface border border-borderHairline rounded shadow-card p-4">
        <div className="flex items-center justify-between mb-3 border-b border-borderHairline pb-2.5">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-slate-500" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
              Evidence Engine Triangulation & Lane Anomalies
            </h3>
          </div>
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${
            isFinalized
              ? isHealthy
                ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                : 'bg-amber-50 text-amber-800 border-amber-300'
              : 'bg-slate-100 text-slate-600 border-slate-200'
          }`}>
            {evidence.oracle_status.replace(/_/g, ' ')}
          </span>
        </div>

        {/* 3 Triangular Deviations */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div className="p-2 bg-surfaceSubtle rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 uppercase font-mono">d(OSM, Market)</div>
            <div className={`font-mono font-bold mt-0.5 tnum ${evidence.d_osm_market && evidence.d_osm_market > 0.03 ? 'text-amber-800' : 'text-slate-900'}`}>
              {evidence.d_osm_market !== null ? `${(evidence.d_osm_market * 100).toFixed(2)}%` : '--'}
            </div>
          </div>

          <div className="p-2 bg-surfaceSubtle rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 uppercase font-mono">d(DEC, Market)</div>
            <div className="font-mono font-bold text-blue-700 mt-0.5 tnum">
              {evidence.d_dec_market !== null ? `${(evidence.d_dec_market * 100).toFixed(2)}%` : '--'}
            </div>
          </div>

          <div className="p-2 bg-surfaceSubtle rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 uppercase font-mono">d(OSM, DEC)</div>
            <div className={`font-mono font-bold mt-0.5 tnum ${evidence.d_osm_dec && evidence.d_osm_dec > 0.03 ? 'text-amber-800' : 'text-slate-900'}`}>
              {evidence.d_osm_dec !== null ? `${(evidence.d_osm_dec * 100).toFixed(2)}%` : '--'}
            </div>
          </div>

          <div className="p-2 bg-surfaceSubtle rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 uppercase font-mono">Anomaly Score</div>
            <div className={`font-mono font-bold mt-0.5 tnum ${evidence.anomaly_score > 0.5 ? 'text-amber-800' : 'text-slate-900'}`}>
              {isFinalized ? `${evidence.anomaly_score.toFixed(2)} / 1.0` : '--'}
            </div>
          </div>
        </div>

        {/* 5 Lane Anomaly Status Bar */}
        <div className="mt-3 pt-2.5 border-t border-slate-100">
          <div className="text-[10px] uppercase font-mono text-slate-500 mb-1.5 flex items-center gap-1">
            <Activity className="w-3 h-3 text-slate-400" />
            Methodology Lane Defense Status:
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 text-[10px] font-mono">
            {[
              { id: 'lane-1', name: 'L1: Kalman', flagged: laneAnomalies['lane-1'] },
              { id: 'lane-2', name: 'L2: Huber', flagged: laneAnomalies['lane-2'] },
              { id: 'lane-3', name: 'L3: JSD', flagged: laneAnomalies['lane-3'] },
              { id: 'lane-4', name: 'L4: OU RWA', flagged: laneAnomalies['lane-4'] },
              { id: 'lane-5', name: 'L5: CUSUM', flagged: laneAnomalies['lane-5'] },
            ].map((lane) => (
              <div
                key={lane.id}
                className={`px-1.5 py-1 rounded border flex items-center justify-between ${
                  lane.flagged
                    ? 'bg-amber-100 text-amber-900 border-amber-300 font-bold'
                    : 'bg-slate-50 text-slate-600 border-slate-200'
                }`}
              >
                <span>{lane.name}</span>
                <span>{lane.flagged ? 'ALERT' : 'OK'}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Active Reason Codes */}
        {evidence.reason_codes.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-slate-100">
            <div className="text-[10px] font-mono text-slate-500 mb-1 flex items-center gap-1 uppercase">
              <FileText className="w-3 h-3 text-slate-400" />
              Active Diagnostic Reason Codes:
            </div>
            <div className="flex flex-wrap gap-1">
              {evidence.reason_codes.map((code) => (
                <span 
                  key={code}
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200"
                >
                  {code}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 2. Protocol Financial Consequence / Capital Protection Panel */}
      <div className="bg-surface border border-borderHairline rounded shadow-card p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-borderHairline pb-2.5">
          <div className="flex items-center space-x-2">
            <Scale className="w-4 h-4 text-slate-700" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900">
              Protocol Financial Consequence & Solvency
            </h3>
          </div>
          <span className="text-[10px] uppercase font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
            SIMULATION ONLY
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-600">Deterministic Policy Action:</span>
          {getDecisionBadge()}
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
          
          <div className="p-3 bg-slate-50 rounded border border-slate-200">
            <div className="text-[10px] text-slate-500 uppercase font-mono">Baseline Collateral Power</div>
            <div className="text-xl font-mono font-bold text-slate-900 mt-1 tnum">
              {collateral.baseline_value !== null ? `$${collateral.baseline_value.toFixed(2)}` : '--'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Based on unverified P_OSM
            </div>
          </div>

          <div className="p-3 bg-blue-50/50 rounded border border-blue-200">
            <div className="text-[10px] text-blue-800 uppercase font-mono">AEGIS Protected Power</div>
            <div className="text-xl font-mono font-bold text-blue-900 mt-1 tnum">
              {collateral.aegis_value !== null ? `$${collateral.aegis_value.toFixed(2)}` : 'Computing...'}
            </div>
            <div className="text-[10px] text-blue-600 mt-0.5">
              Based on verified P_FINAL
            </div>
          </div>

          <div className={`p-3 rounded border ${
            collateral.difference && collateral.difference > 0
              ? 'bg-emerald-50 text-emerald-900 border-emerald-300'
              : 'bg-slate-50 text-slate-800 border-slate-200'
          }`}>
            <div className="text-[10px] uppercase font-mono">Capital at Risk Prevented</div>
            <div className="text-xl font-mono font-bold mt-1 tnum">
              {collateral.difference !== null 
                ? collateral.difference > 0
                  ? `+$${collateral.difference.toFixed(2)}`
                  : '$0.00'
                : '--'}
            </div>
            <div className="text-[10px] mt-0.5 font-medium">
              {collateral.risk_exposure_pct !== null && collateral.risk_exposure_pct > 0
                ? `${collateral.risk_exposure_pct.toFixed(1)}% avoided over-borrowing`
                : 'Zero collateral divergence'}
            </div>
          </div>

        </div>

        {/* Narrative Risk Explainer */}
        <div className="text-xs text-slate-700 bg-surfaceSubtle p-3 rounded border border-borderHairline leading-relaxed">
          {hasInconsistency ? (
            <div>
              <strong className="text-slate-900">Capital Protection Active: </strong>
              Accepting stale/manipulated P_OSM (${scenario.p_osm.value.toFixed(2)}) would permit unbacked borrowing up to ${collateral.baseline_value?.toFixed(2)} per unit collateral. 
              AEGIS verification restricts borrow power to ${collateral.aegis_value?.toFixed(2)}, preventing protocol insolvency and bad debt creation.
            </div>
          ) : isHealthy ? (
            <div>
              <strong className="text-emerald-900">Multi-Methodology Consensus Confirmed: </strong>
              All five methodology lanes and off-chain market observations confirm P_OSM consistency. Standard protocol borrowing limits applied.
            </div>
          ) : (
            <div>
              Verification window in progress. Gathering and aggregating 5 methodology lane signals...
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
