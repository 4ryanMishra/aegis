import React from 'react';
import { ScenarioRecord, ValidatorObservation } from '@/lib/types';
import { X, ShieldCheck, Database, Clock, Hash, Info, ExternalLink } from 'lucide-react';

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

  if (typeof inspectTarget === 'string') {
    if (inspectTarget === 'P_OSM') {
      title = 'P_OSM — Delayed Baseline Oracle Feed';
      statusBadge = scenario.p_osm.status;
      details = [
        { label: 'Current Queued Value', value: `$${scenario.p_osm.value.toFixed(2)}`, isMono: true },
        { label: 'Arrival Timestamp', value: new Date(scenario.p_osm.timestamp * 1000).toISOString(), isMono: true },
        { label: 'Source Provider', value: scenario.p_osm.source },
        { label: 'Validation Enclave', value: 'Multipli OSM Mock Enclave' },
        { label: 'Description', value: scenario.p_osm.description || 'Delayed Oracle entry' },
      ];
      sources = ['multipli_rwa_osm_feed'];
    } else if (inspectTarget === 'P_DEC') {
      title = 'P_DEC — Decentralized Reference Aggregate';
      statusBadge = scenario.p_dec.status;
      details = [
        { label: 'Aggregate Value', value: scenario.p_dec.value ? `$${scenario.p_dec.value.toFixed(2)}` : 'Pending', isMono: true },
        { label: 'Aggregation Methodology', value: scenario.p_dec.aggregation.toUpperCase() },
        { label: 'Validator Quorum', value: `${scenario.p_dec.validator_count} / 4 nodes reporting` },
        { label: 'Dispersion Metric (IQR)', value: scenario.p_dec.dispersion.toString(), isMono: true },
        { label: 'Quorum Condition Met', value: scenario.p_dec.quorum_met ? 'YES' : 'NO' },
      ];
      sources = scenario.validators.flatMap((v) => v.source_ids);
    } else if (inspectTarget === 'P_MARKET') {
      title = 'P_MARKET — External Market Observation';
      statusBadge = scenario.p_market.status;
      details = [
        { label: 'Market Observation', value: scenario.p_market.value ? `$${scenario.p_market.value.toFixed(2)}` : 'Awaiting T1', isMono: true },
        { label: 'Symbol / Asset', value: scenario.p_market.symbol || 'XAU/USD' },
        { label: 'Adapter', value: scenario.p_market.source || 'simulated_binance_adapter' },
        { label: 'Data Class', value: scenario.p_market.is_offchain ? 'OFF-CHAIN CEX OBSERVATION' : 'ON-CHAIN' },
      ];
      sources = ['binance_xau_offchain_api'];
    } else if (inspectTarget === 'DECISION') {
      title = 'Protocol Final Valuation & Decision';
      statusBadge = 'SIMULATED';
      details = [
        { label: 'Selected Valuation', value: scenario.decision.final_price ? `$${scenario.decision.final_price.toFixed(2)}` : 'Pending', isMono: true },
        { label: 'Selected Price Source', value: scenario.decision.selected_source },
        { label: 'Applied Policy', value: scenario.decision.policy },
        { label: 'Confidence Score', value: scenario.decision.confidence ? `${(scenario.decision.confidence * 100).toFixed(0)}%` : '--' },
        { label: 'Policy Version', value: scenario.decision.policy_version, isMono: true },
      ];
      sources = ['aegis_decision_engine_v0.1.0'];
    }
  } else {
    // Validator observation object
    const val = inspectTarget as ValidatorObservation;
    title = `Validator Node: ${val.validator_id}`;
    statusBadge = val.status;
    details = [
      { label: 'Estimated Price', value: `$${val.estimated_price.toFixed(2)}`, isMono: true },
      { label: 'Uncertainty Interval', value: `[ $${val.uncertainty_lower.toFixed(2)} - $${val.uncertainty_upper.toFixed(2)} ]`, isMono: true },
      { label: 'Strategy / Methodology', value: val.strategy_name },
      { label: 'Strategy ID', value: val.strategy_id, isMono: true },
      { label: 'Method Version', value: val.method_version, isMono: true },
      { label: 'Observed Timestamp', value: new Date(val.observed_at * 1000).toISOString(), isMono: true },
    ];
    sources = val.source_ids;
  }

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/30 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-surface h-full shadow-2xl border-l border-borderHairline flex flex-col">
        
        {/* Drawer Header */}
        <div className="p-4 border-b border-borderHairline flex items-center justify-between bg-surfaceSubtle">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-slate-700" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
              Provenance Inspector
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
              <h3 className="font-semibold text-slate-900 text-sm">{title}</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                {statusBadge}
              </span>
            </div>
            <p className="text-secondaryText text-[11px]">
              Cryptographic and methodological audit trace for this simulation node.
            </p>
          </div>

          {/* Key Attributes */}
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

          {/* Sources Set */}
          {sources.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1">
                <Database className="w-3.5 h-3.5" />
                Underlying Source Feeds ({sources.length}):
              </div>
              <div className="space-y-1">
                {sources.map((src, i) => (
                  <div key={i} className="font-mono text-[11px] p-2 bg-slate-50 border border-borderHairline rounded text-slate-700 flex items-center justify-between">
                    <span>{src}</span>
                    <span className="text-[10px] text-slate-400">SIMULATED</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Anti-Hallucination Guardrail Note */}
          <div className="p-3 bg-amber-50/60 rounded border border-amber-200 text-amber-900 text-[11px] leading-relaxed">
            <div className="font-semibold flex items-center gap-1 mb-1">
              <Info className="w-3.5 h-3.5 text-amber-700" />
              Anti-Hallucination & Research Notice:
            </div>
            This node output is produced by deterministic prototype simulations. External market observations represent off-chain API data and are not on-chain state. Final forecasting methodologies are pluggable and will be replaced by verified research models.
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
