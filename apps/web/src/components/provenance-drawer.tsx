import React from 'react';
import { ScenarioRecord, OracleObservation } from '@/lib/types';
import { X, ShieldCheck, Database, Info, Layers, Radio, GitMerge, Scale } from 'lucide-react';

interface ProvenanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  inspectTarget: string | OracleObservation | null;
  scenario: ScenarioRecord;
}

export const ProvenanceDrawer: React.FC<ProvenanceDrawerProps> = ({
  isOpen,
  onClose,
  inspectTarget,
  scenario,
}) => {
  if (!isOpen || !inspectTarget) return null;

  let title = 'Cross-Oracle Audit Inspector';
  let statusBadge = 'ACTIVE';
  let details: { label: string; value: string; isMono?: boolean }[] = [];
  let sources: string[] = [];
  let selectedOracle: OracleObservation | null = null;

  if (typeof inspectTarget === 'string') {
    if (inspectTarget === 'MULTIPLI' || inspectTarget === 'P_OSM') {
      title = 'Multipli OSM — Target Delayed Oracle Feed';
      statusBadge = scenario.p_osm.status;
      details = [
        { label: 'Current Queued Price', value: `$${scenario.p_osm.value.toFixed(2)}`, isMono: true },
        { label: 'Arrival Timestamp', value: new Date(scenario.p_osm.timestamp * 1000).toISOString(), isMono: true },
        { label: 'Source Provider', value: scenario.p_osm.source },
        { label: 'Buffer Delay', value: '1-Hour Delayed Attestation Window' },
        { label: 'Description', value: scenario.p_osm.description || 'Target OSM feed cross-checked against independent oracle networks' },
      ];
      sources = ['multipli_osm_contract', 'multipli_price_buffer'];
    } else if (inspectTarget === 'CONSENSUS' || inspectTarget === 'P_DEC') {
      title = 'Cross-Oracle Price-Band Consensus Engine';
      statusBadge = scenario.p_dec.has_strong_consensus ? 'STRONG_CONSENSUS' : 'DEGRADED';
      details = [
        { label: 'Consensus Price (Median)', value: scenario.p_dec.consensus_price ? `$${scenario.p_dec.consensus_price.toFixed(2)}` : 'Pending Quorum', isMono: true },
        { label: 'Agreement Tolerance', value: '0.50% Maximum Spread Band', isMono: true },
        { label: 'Agreement Cluster Size', value: `${scenario.p_dec.cluster_size} of ${scenario.p_dec.total_eligible} eligible feeds` },
        { label: 'Agreement Ratio', value: `${(scenario.p_dec.agreement_ratio * 100).toFixed(1)}%`, isMono: true },
        { label: 'Internal Cluster Spread', value: `${scenario.p_dec.cluster_spread_pct.toFixed(2)}%`, isMono: true },
      ];
      sources = scenario.p_dec.cluster_members || ['chainlink_main', 'pyth_gold', 'chronicle_xau', 'redstone_gold', 'supra_gold', 'api3_gold'];
    } else if (inspectTarget === 'MARKET' || inspectTarget === 'P_MARKET') {
      title = 'Real-Time Spot Market Reference';
      statusBadge = scenario.p_market.status;
      details = [
        { label: 'Market Spot Price', value: scenario.p_market.value ? `$${scenario.p_market.value.toFixed(2)}` : 'Awaiting Tick', isMono: true },
        { label: 'Asset Symbol', value: scenario.p_market.symbol || 'XAU/USD' },
        { label: 'Attestation Source', value: scenario.p_market.source || 'simulated_binance_adapter' },
        { label: 'Data Type', value: scenario.p_market.is_offchain ? 'Continuous Spot Observation' : 'On-Chain Stream' },
      ];
      sources = ['binance_xau_clob', 'coinbase_xau_spot'];
    } else if (inspectTarget === 'DECISION') {
      title = 'AEGIS Risk Resolution & Authoritative Valuation';
      statusBadge = scenario.decision.state;
      details = [
        { label: 'Authoritative Valuation P_FINAL', value: scenario.decision.final_price ? `$${scenario.decision.final_price.toFixed(2)}` : 'Computing...', isMono: true },
        { label: 'Multipli Deviation', value: `${scenario.decision.multipli_deviation_pct.toFixed(2)}%`, isMono: true },
        { label: 'Conservative Rule min(OSM, Cons)', value: scenario.decision.is_conservative_applied ? 'ENFORCED' : 'NOT NEEDED', isMono: true },
        { label: 'Effective Max LTV Cap', value: `${(scenario.decision.effective_ltv * 100).toFixed(0)}%`, isMono: true },
        { label: 'Downstream Protocol State', value: scenario.decision.protocol_state, isMono: true },
      ];
      sources = ['aegis_consensus_engine', 'aegis_risk_decision_engine', 'aegis_price_router'];
    }
  } else {
    // Oracle observation object
    selectedOracle = inspectTarget as OracleObservation;
    title = `${selectedOracle.name} Oracle Feed`;
    statusBadge = selectedOracle.status;
    details = [
      { label: 'Provider Name', value: selectedOracle.name },
      { label: 'Source ID', value: selectedOracle.source_id, isMono: true },
      { 
        label: 'Observed Price', 
        value: selectedOracle.price !== null && selectedOracle.price !== undefined
          ? `$${selectedOracle.price.toFixed(2)}`
          : 'None / Revert', 
        isMono: true 
      },
      { 
        label: 'Latency / Age', 
        value: `${selectedOracle.age_seconds} seconds ago`, 
        isMono: true 
      },
      { label: 'Status', value: selectedOracle.status, isMono: true },
      { label: 'Cluster Assignment', value: selectedOracle.cluster_id || 'Excluded / Offline', isMono: true },
      { label: 'Native Confidence Bound', value: selectedOracle.has_confidence ? `±$${selectedOracle.confidence?.toFixed(2) || '0.25'}` : 'N/A (Point Estimate)', isMono: true },
      { label: 'On-Chain Valid', value: selectedOracle.valid ? 'YES (Valid Nonce & Timestamp)' : 'NO (Stale or Corrupted)', isMono: true },
    ];
    sources = [selectedOracle.source_id];
  }

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/30 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-xl bg-surface h-full shadow-2xl border-l border-borderHairline flex flex-col">
        
        {/* Drawer Header */}
        <div className="p-4 border-b border-borderHairline flex items-center justify-between bg-surfaceSubtle">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-slate-700" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
              Cross-Oracle Verification Audit Trail
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
              Deterministic on-chain telemetry and agreement clustering verification trace.
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
                Network Feeds & Adapters ({sources.length}):
              </div>
              <div className="space-y-1">
                {sources.map((src, i) => (
                  <div key={i} className="font-mono text-[11px] p-2 bg-slate-50 border border-borderHairline rounded text-slate-700 flex items-center justify-between">
                    <span>{src}</span>
                    <span className="text-[10px] text-emerald-600 font-bold">CONNECTED</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transparent Philosophy Note */}
          <div className="p-3 bg-blue-50/60 rounded border border-blue-200 text-blue-900 text-[11px] leading-relaxed">
            <div className="font-semibold flex items-center gap-1 mb-1">
              <Info className="w-3.5 h-3.5 text-blue-700" />
              Transparent Cross-Checking Rule:
            </div>
            AEGIS does not train off-chain predictive models or act as a black-box oracle. Instead, AEGIS performs transparent on-chain price-band agreement clustering across established oracle networks (Chainlink, Pyth, Chronicle, RedStone, Supra, API3) to cross-check Multipli OSM and enforce conservative valuation during flash drops or stale updates.
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
