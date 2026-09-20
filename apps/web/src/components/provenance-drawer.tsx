import React from 'react';
import { ScenarioRecord, ValidatorObservation } from '@/lib/types';
import { 
  KalmanForensicPanel, 
  HuberForensicPanel, 
  JSDForensicPanel, 
  OUForensicPanel, 
  CUSUMForensicPanel 
} from './forensics';
import { X, ShieldCheck, Database, Info, Layers, Cpu } from 'lucide-react';

interface ProvenanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  inspectTarget: string | ValidatorObservation | null;
  scenario: ScenarioRecord;
}

export const ProvenanceDrawer: React.FC<ProvenanceDrawerProps> = ({
  isOpen,
  onClose,
  inspectTarget,
  scenario,
}) => {
  if (!isOpen || !inspectTarget) return null;

  let title = 'Provenance & Audit Trail';
  let statusBadge = 'SIMULATED';
  let details: { label: string; value: string; isMono?: boolean }[] = [];
  let sources: string[] = [];
  let selectedValidator: ValidatorObservation | null = null;

  if (typeof inspectTarget === 'string') {
    if (inspectTarget === 'P_OSM') {
      title = 'P_OSM — Delayed Baseline Oracle Feed';
      statusBadge = scenario.p_osm.status;
      details = [
        { label: 'Current Queued Value', value: `$${scenario.p_osm.value.toFixed(2)}`, isMono: true },
        { label: 'Arrival Timestamp', value: new Date(scenario.p_osm.timestamp * 1000).toISOString(), isMono: true },
        { label: 'Source Provider', value: scenario.p_osm.source },
        { label: 'Validation Enclave', value: 'Multipli OSM Mock Enclave' },
        { label: 'Description', value: scenario.p_osm.description || 'Existing OSM 1-hour delay buffer' },
      ];
      sources = ['multipli_rwa_osm_feed'];
    } else if (inspectTarget === 'P_DEC') {
      title = 'P_DEC — Decentralized Reference Aggregate';
      statusBadge = scenario.p_dec.status;
      details = [
        { label: 'Aggregate Value', value: scenario.p_dec.value ? `$${scenario.p_dec.value.toFixed(2)}` : 'Pending Quorum', isMono: true },
        { label: 'Aggregation Methodology', value: 'Uncertainty-Weighted Median Blend' },
        { label: 'Active Quorum', value: `${scenario.p_dec.validator_count} / 5 methodology lanes reporting` },
        { label: 'Dispersion Metric (Norm MAD)', value: scenario.p_dec.dispersion.toFixed(4), isMono: true },
        { label: 'Quorum Condition Met (N ≥ 3)', value: scenario.p_dec.quorum_met ? 'YES' : 'NO' },
      ];
      sources = scenario.validators.flatMap((v) => v.source_ids || []);
    } else if (inspectTarget === 'P_MARKET') {
      title = 'P_MARKET — External Market Observation';
      statusBadge = scenario.p_market.status;
      details = [
        { label: 'Market Observation', value: scenario.p_market.value ? `$${scenario.p_market.value.toFixed(2)}` : 'Awaiting T1 (End of Hour)', isMono: true },
        { label: 'Symbol / Asset', value: scenario.p_market.symbol || 'XAU/USD' },
        { label: 'Adapter', value: scenario.p_market.source || 'simulated_binance_adapter' },
        { label: 'Data Class', value: scenario.p_market.is_offchain ? 'OFF-CHAIN CEX OBSERVATION' : 'ON-CHAIN' },
      ];
      sources = ['binance_xau_offchain_api', 'coinbase_xau_clob'];
    } else if (inspectTarget === 'DECISION') {
      title = 'Protocol Final Valuation & Policy Action';
      statusBadge = 'SIMULATED';
      details = [
        { label: 'Selected Final Price P_FINAL', value: scenario.decision.final_price ? `$${scenario.decision.final_price.toFixed(2)}` : 'Computing...', isMono: true },
        { label: 'Selected Price Source', value: scenario.decision.selected_source },
        { label: 'Decision State', value: scenario.decision.decision || scenario.decision.policy },
        { label: 'Applied Policy', value: String(scenario.decision.policy) },
        { label: 'Confidence Score', value: scenario.decision.confidence ? `${(scenario.decision.confidence * 100).toFixed(0)}%` : '--' },
        { label: 'Policy Version', value: scenario.decision.policy_version, isMono: true },
      ];
      sources = ['aegis_evidence_engine_v0.2.0', 'aegis_decision_engine_v0.2.0'];
    }
  } else {
    // Validator observation object
    selectedValidator = inspectTarget as ValidatorObservation;
    title = `${selectedValidator.methodology_name}`;
    statusBadge = selectedValidator.status;
    details = [
      { label: 'Lane ID', value: String(selectedValidator.lane_id).toUpperCase(), isMono: true },
      { label: 'Functional Role', value: selectedValidator.is_price_estimator ? 'Price Estimator (P_DEC eligible)' : 'Diagnostic Evidence', isMono: false },
      { label: 'Simulated Validator Node', value: selectedValidator.validator_id, isMono: true },
      { label: 'Simulated Operator', value: selectedValidator.operator_id, isMono: true },
      { 
        label: 'Price Estimate', 
        value: selectedValidator.estimated_price !== null && selectedValidator.estimated_price !== undefined
          ? `$${selectedValidator.estimated_price.toFixed(2)}`
          : 'None (Diagnostic Lane)', 
        isMono: true 
      },
      { 
        label: '95% Uncertainty Band', 
        value: selectedValidator.uncertainty_lower !== null && selectedValidator.uncertainty_upper !== null && selectedValidator.uncertainty_lower !== undefined && selectedValidator.uncertainty_upper !== undefined
          ? `[ $${selectedValidator.uncertainty_lower.toFixed(2)} - $${selectedValidator.uncertainty_upper.toFixed(2)} ]`
          : 'None (Diagnostic Lane)', 
        isMono: true 
      },
      { label: 'Methodology Key', value: selectedValidator.methodology, isMono: true },
      { label: 'Decision Flag', value: selectedValidator.decision, isMono: true },
      { label: 'Reason Code', value: selectedValidator.reason_code, isMono: true },
    ];
    sources = selectedValidator.source_ids || [];
  }

  const renderForensicContent = () => {
    if (!selectedValidator) return null;

    const meth = selectedValidator.methodology || selectedValidator.strategy_id || '';

    if (meth.includes('KALMAN') || meth.includes('kalman')) {
      return <KalmanForensicPanel validator={selectedValidator} />;
    } else if (meth.includes('HUBER') || meth.includes('huber')) {
      return <HuberForensicPanel validator={selectedValidator} />;
    } else if (meth.includes('JENSEN') || meth.includes('jsd')) {
      return <JSDForensicPanel validator={selectedValidator} />;
    } else if (meth.includes('ORNSTEIN') || meth.includes('ou')) {
      return <OUForensicPanel validator={selectedValidator} />;
    } else if (meth.includes('CUSUM') || meth.includes('cusum')) {
      return <CUSUMForensicPanel validator={selectedValidator} />;
    }

    return (
      <div className="p-4 bg-slate-50 border border-slate-200 rounded text-slate-600 text-xs">
        Forensic telemetry inspection for this methodology lane is recorded in intermediate metrics.
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/30 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-2xl bg-surface h-full shadow-2xl border-l border-borderHairline flex flex-col">
        
        {/* Drawer Header */}
        <div className="p-4 border-b border-borderHairline flex items-center justify-between bg-surfaceSubtle">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-slate-700" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
              Quantitative Methodology Forensics & Provenance
            </h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="p-5 space-y-5 overflow-y-auto flex-1 text-xs">
          
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-semibold text-slate-900 text-sm leading-snug">{title}</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 ml-2">
                {statusBadge}
              </span>
            </div>
            <p className="text-secondaryText text-[11px]">
              Forensic telemetry and mathematical audit trace for this component in the AEGIS verification pipeline.
            </p>
          </div>

          {/* Canonical Terminology Notice for Validators */}
          {selectedValidator && (
            <div className="p-2.5 bg-blue-50/60 rounded border border-blue-200 text-blue-900 text-[11px] leading-relaxed">
              <div className="font-semibold flex items-center gap-1 mb-0.5">
                <Cpu className="w-3.5 h-3.5 text-blue-700" />
                Methodology Invariant:
              </div>
              Five methodology lanes, each capable of being operated by multiple independent validator nodes.
              <span className="opacity-80 block text-[10px] mt-0.5">
                (Current MVP simulation: 1 simulated node per lane).
              </span>
            </div>
          )}

          {/* Dedicated Forensic Math Panel */}
          {selectedValidator ? (
            renderForensicContent()
          ) : (
            /* Key Attributes for Oracle entities */
            <div className="bg-surfaceSubtle rounded border border-borderHairline p-3 space-y-2.5">
              {details.map((d) => (
                <div key={d.label} className="flex items-start justify-between">
                  <span className="text-slate-500 font-medium">{d.label}</span>
                  <span className={`text-slate-900 text-right ${d.isMono ? 'font-mono font-semibold' : 'font-medium'}`}>
                    {d.value}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Sources Set */}
          {sources.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1">
                <Database className="w-3.5 h-3.5" />
                Input Feeds & Market Adapters ({sources.length}):
              </div>
              <div className="space-y-1">
                {sources.map((src, i) => (
                  <div key={i} className="font-mono text-[11px] p-2 bg-slate-50 border border-borderHairline rounded text-slate-700 flex items-center justify-between">
                    <span>{src}</span>
                    <span className="text-[10px] text-slate-400">FEED OK</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Anti-Hallucination Guardrail Note */}
          <div className="p-3 bg-amber-50/60 rounded border border-amber-200 text-amber-900 text-[11px] leading-relaxed">
            <div className="font-semibold flex items-center gap-1 mb-1">
              <Info className="w-3.5 h-3.5 text-amber-700" />
              Epistemic Humility & Threat Notice:
            </div>
            Each methodology is an evidence producer, not an unquestionable truth source. All statistical defenses produce bounded probabilistic evidence and may suffer from correlated upstream anomalies, delayed regime detection, or sample starvation during extreme market stress.
          </div>

        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-borderHairline bg-surfaceSubtle flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-medium transition"
          >
            Close Inspector
          </button>
        </div>

      </div>
    </div>
  );
};
