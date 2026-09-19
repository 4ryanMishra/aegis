import React from 'react';
import { ScenarioRecord } from '@/lib/types';
import { ShieldAlert, CheckCircle2, TrendingDown, Scale, FileText } from 'lucide-react';

interface DecisionPanelProps {
  scenario: ScenarioRecord;
}

export const DecisionPanel: React.FC<DecisionPanelProps> = ({ scenario }) => {
  const { evidence, decision, collateral, window } = scenario;

  const isFinalized = window.is_finalized;
  const isHealthy = evidence.oracle_status === 'HEALTHY_CONSENSUS';
  const hasInconsistency = evidence.oracle_status === 'SUSPECTED_INCONSISTENCY' || evidence.oracle_status === 'EVIDENCE_OF_ABNORMAL_DEVIATION';

  return (
    <div className="space-y-4">
      
      {/* 1. Evidence Engine Summary */}
      <div className="bg-surface border border-borderHairline rounded shadow-card p-4">
        <div className="flex items-center justify-between mb-3 border-b border-borderHairline pb-2.5">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-slate-500" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
              Evidence & Deviation Metrics
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

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div className="p-2 bg-surfaceSubtle rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 uppercase">d(OSM, Market)</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {evidence.d_osm_market !== null ? `${(evidence.d_osm_market * 100).toFixed(2)}%` : '--'}
            </div>
          </div>

          <div className="p-2 bg-surfaceSubtle rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 uppercase">d(DEC, Market)</div>
            <div className="font-mono font-bold text-blue-700 mt-0.5 tnum">
              {evidence.d_dec_market !== null ? `${(evidence.d_dec_market * 100).toFixed(2)}%` : '--'}
            </div>
          </div>

          <div className="p-2 bg-surfaceSubtle rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 uppercase">d(OSM, DEC)</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {evidence.d_osm_dec !== null ? `${(evidence.d_osm_dec * 100).toFixed(2)}%` : '--'}
            </div>
          </div>

          <div className="p-2 bg-surfaceSubtle rounded border border-borderHairline">
            <div className="text-[10px] text-slate-500 uppercase">Anomaly Score</div>
            <div className="font-mono font-bold text-slate-900 mt-0.5 tnum">
              {isFinalized ? `${evidence.anomaly_score.toFixed(2)} / 1.0` : '--'}
            </div>
          </div>
        </div>

        {/* Reason Codes */}
        <div className="mt-3 pt-2.5 border-t border-slate-100">
          <div className="text-[11px] font-semibold text-slate-500 mb-1.5 flex items-center gap-1">
            <FileText className="w-3 h-3" />
            Active Reason Codes:
          </div>
          <div className="flex flex-wrap gap-1.5">
            {evidence.reason_codes.map((code) => (
              <span 
                key={code}
                className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200"
              >
                {code}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* 2. Collateral Impact & Valuation Action */}
      <div className="bg-surface border border-borderHairline rounded shadow-card p-4">
        <div className="flex items-center justify-between mb-3 border-b border-borderHairline pb-2.5">
          <div className="flex items-center space-x-2">
            <Scale className="w-4 h-4 text-slate-500" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
              Protocol Collateral & Solvency Impact
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-500">
            LTV Factor: {Math.round(collateral.ltv * 100)}%
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          
          <div className="p-3 bg-slate-50 rounded border border-slate-200">
            <div className="text-[11px] text-slate-500 font-medium">Baseline Collateral Power</div>
            <div className="text-xl font-mono font-bold text-slate-900 mt-1 tnum">
              {collateral.baseline_value !== null ? `$${collateral.baseline_value.toFixed(2)}` : '--'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Based on unverified $P_{'{OSM}'}$
            </div>
          </div>

          <div className="p-3 bg-blue-50/50 rounded border border-blue-200">
            <div className="text-[11px] text-blue-800 font-medium">AEGIS Verified Power</div>
            <div className="text-xl font-mono font-bold text-blue-900 mt-1 tnum">
              {collateral.aegis_value !== null ? `$${collateral.aegis_value.toFixed(2)}` : 'Computing...'}
            </div>
            <div className="text-[10px] text-blue-600 mt-0.5">
              Based on verified valuation
            </div>
          </div>

          <div className={`p-3 rounded border ${
            collateral.difference && collateral.difference > 0
              ? 'bg-emerald-50 text-emerald-900 border-emerald-300'
              : 'bg-slate-50 text-slate-800 border-slate-200'
          }`}>
            <div className="text-[11px] font-medium">Risk Overstatement Avoided</div>
            <div className="text-xl font-mono font-bold mt-1 tnum">
              {collateral.difference !== null 
                ? collateral.difference > 0
                  ? `+$${collateral.difference.toFixed(2)}`
                  : '$0.00'
                : '--'}
            </div>
            <div className="text-[10px] mt-0.5 font-medium">
              {collateral.risk_exposure_pct !== null && collateral.risk_exposure_pct > 0
                ? `${collateral.risk_exposure_pct.toFixed(1)}% bad debt exposure prevented`
                : 'Zero divergence / aligned'}
            </div>
          </div>

        </div>

        <div className="mt-3 text-xs text-slate-600 bg-surfaceSubtle p-2.5 rounded border border-borderHairline">
          <p className="leading-relaxed">
            {hasInconsistency ? (
              <span>
                <strong className="text-amber-800">Risk Mitigation Active: </strong>
                Accepting delayed OSM ($100.00) would allow unbacked collateral borrowing at $60.00. AEGIS protocol valuation restricts borrowing to $55.80, insulating protocol solvency.
              </span>
            ) : isHealthy ? (
              <span>
                <strong className="text-emerald-800">Consensus Confirmed: </strong>
                All validator signals and external market observations confirm $P_{'{OSM}'}$ validity within safe bounds. Standard LTV applied.
              </span>
            ) : (
              <span>Verification window in progress. Gathering multi-source validator evidence...</span>
            )}
          </p>
        </div>

      </div>

    </div>
  );
};
