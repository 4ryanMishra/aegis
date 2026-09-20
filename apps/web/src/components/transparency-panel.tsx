import React from 'react';
import { SimulationSnapshot } from '@/lib/types';
import { 
  ShieldCheck, 
  ShieldAlert, 
  AlertTriangle, 
  Scale, 
  FileText, 
  HelpCircle, 
  CheckCircle2, 
  Lock, 
  ArrowRight 
} from 'lucide-react';

interface TransparencyPanelProps {
  snapshot: SimulationSnapshot;
}

export const TransparencyPanel: React.FC<TransparencyPanelProps> = ({ snapshot }) => {
  const { consensus, decision, position, multipli_observation } = snapshot;

  const isHealthy = decision.state === 'HEALTHY_CONSENSUS';
  const isDeviation = decision.state === 'MULTIPLI_DEVIATION';
  const isHalted = decision.state === 'NO_CONSENSUS' || decision.protocol_state === 'HALTED';
  const isDegraded = decision.state === 'SOURCE_DEGRADED';

  // Capital calculation
  const multipliPrice = multipli_observation?.price || 0;
  const finalPrice = decision.final_price || 0;
  const colAmount = position?.collateral_amount || 10.0;
  const unverifiedValuation = multipliPrice * colAmount;
  const aegisValuation = finalPrice * colAmount;
  const avoidedOverstatement = Math.max(0, unverifiedValuation - aegisValuation);

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderHairline pb-2.5">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900">
            Transparency & Audit Rationale ("Why AEGIS Decided This")
          </h3>
        </div>
        <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${
          isHalted
            ? 'bg-rose-50 text-rose-800 border-rose-300'
            : isDeviation || isDegraded
            ? 'bg-amber-50 text-amber-800 border-amber-300'
            : 'bg-emerald-50 text-emerald-800 border-emerald-300'
        }`}>
          {decision.state.replace(/_/g, ' ')}
        </span>
      </div>

      {/* Decision Rationale Box */}
      <div className="p-3 bg-surfaceSubtle rounded border border-borderHairline text-xs space-y-2">
        <div className="font-semibold text-slate-800 flex items-center gap-1.5">
          <Scale className="w-4 h-4 text-slate-500" />
          <span>Decision Rationale & Safety Directive:</span>
        </div>
        <p className="text-slate-700 leading-relaxed">
          {decision.policy_rationale || 'Consensus within normal parameters. Multipli feed consistent with multi-oracle agreement cluster.'}
        </p>
      </div>

      {/* 4-Step Mathematical Verification Audit */}
      <div className="space-y-2 text-xs">
        <div className="text-[10px] uppercase font-mono text-slate-500 font-semibold">
          Deterministic Execution Audit Trail:
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
          {/* Step 1 */}
          <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
            <div className="text-[10px] text-slate-500 uppercase flex items-center justify-between">
              <span>Step 1: Agreement Clustering</span>
              <span className="text-blue-600 font-bold">&le;0.5% Band</span>
            </div>
            <div className="text-slate-800 font-bold mt-1">
              {consensus.cluster_size} of {consensus.total_eligible} Feeds in Agreement
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Cluster Spread: {consensus.cluster_spread_pct.toFixed(2)}% | Median: ${consensus.consensus_price?.toFixed(2) || '--'}
            </div>
          </div>

          {/* Step 2 */}
          <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
            <div className="text-[10px] text-slate-500 uppercase flex items-center justify-between">
              <span>Step 2: Multipli Deviation Check</span>
              <span className="text-purple-700 font-bold">|OSM - Cons|</span>
            </div>
            <div className={`font-bold mt-1 ${decision.multipli_deviation_pct > 0.5 ? 'text-amber-700' : 'text-emerald-700'}`}>
              {decision.multipli_deviation_pct.toFixed(2)}% Multipli Divergence
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Threshold: 0.50% &bull; {decision.multipli_deviation_pct > 0.5 ? 'Threshold Exceeded' : 'Within Tolerance'}
            </div>
          </div>

          {/* Step 3 */}
          <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
            <div className="text-[10px] text-slate-500 uppercase flex items-center justify-between">
              <span>Step 3: Valuation Rule Applied</span>
              <span className="text-slate-600 font-bold">min(P_osm, P_cons)</span>
            </div>
            <div className="text-slate-900 font-bold mt-1">
              P_FINAL = ${decision.final_price?.toFixed(2) || '--'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              {decision.is_conservative_applied 
                ? `Enforced min($${multipliPrice.toFixed(2)}, $${consensus.consensus_price?.toFixed(2)})`
                : 'Standard Multipli consensus valuation'}
            </div>
          </div>

          {/* Step 4 */}
          <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
            <div className="text-[10px] text-slate-500 uppercase flex items-center justify-between">
              <span>Step 4: Solvency & LTV Action</span>
              <span className="text-emerald-700 font-bold">LTV Cap</span>
            </div>
            <div className={`font-bold mt-1 ${decision.effective_ltv < 0.8 ? 'text-amber-700' : 'text-emerald-700'}`}>
              {(decision.effective_ltv * 100).toFixed(0)}% Effective Max LTV
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              State: {decision.protocol_state} &bull; Headroom: ${position?.borrowing_headroom.toFixed(2) || '0.00'}
            </div>
          </div>
        </div>
      </div>

      {/* Protocol Solvency Protection Summary */}
      {avoidedOverstatement > 0 && (
        <div className="bg-emerald-50/70 border border-emerald-300 p-3 rounded text-xs text-emerald-950 space-y-1">
          <div className="font-bold flex items-center gap-1.5 text-emerald-900">
            <ShieldCheck className="w-4 h-4 text-emerald-700" />
            <span>Bad Debt Prevention Impact:</span>
          </div>
          <p className="text-[11px] leading-relaxed text-emerald-800">
            If the downstream protocol had accepted unverified Multipli OSM ($ {multipliPrice.toFixed(2)}), this vault would have overstated collateral value by <strong>+${avoidedOverstatement.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>, allowing unsafe borrowing up to ${(unverifiedValuation * 0.8).toFixed(2)}. AEGIS prevented protocol insolvency by immediately restricting valuation to ${aegisValuation.toFixed(2)} and enforcing a 50% LTV cap.
          </p>
        </div>
      )}
    </div>
  );
};
