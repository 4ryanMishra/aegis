import React from 'react';
import { HelpCircle, ShieldCheck, AlertTriangle, Info, CheckCircle2, Lock } from 'lucide-react';
import { OracleStatus, DecisionResult, CollateralImpact } from '@/lib/types';

interface SystemInterpretationProps {
  interpretation: string;
  oracleStatus: OracleStatus | string;
  decision: DecisionResult;
  collateral: CollateralImpact;
  isFinalized: boolean;
  simulationTimeFormatted: string;
}

export const SystemInterpretation: React.FC<SystemInterpretationProps> = ({
  interpretation,
  oracleStatus,
  decision,
  collateral,
  isFinalized,
  simulationTimeFormatted,
}) => {
  const getIcon = () => {
    if (oracleStatus === 'HALTED_CIRCUIT_BREAKER' || decision.action === 'HALT') {
      return <Lock className="w-4 h-4 text-rose-600 shrink-0" />;
    }
    if (oracleStatus === 'HEALTHY_CONSENSUS' || decision.action === 'ALLOW') {
      return <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />;
    }
    return <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />;
  };

  const getBorderColor = () => {
    if (oracleStatus === 'HALTED_CIRCUIT_BREAKER' || decision.action === 'HALT') {
      return 'border-rose-300 bg-rose-50/50';
    }
    if (oracleStatus === 'HEALTHY_CONSENSUS') {
      return 'border-emerald-300 bg-emerald-50/50';
    }
    return 'border-amber-300 bg-amber-50/50';
  };

  return (
    <div className={`border rounded shadow-card p-4 transition ${getBorderColor()}`}>
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-borderHairline">
        <div className="flex items-center space-x-2">
          {getIcon()}
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
            System Risk Interpretation & Oracle Reasoning
          </h3>
        </div>
        <span className="text-[10px] font-mono text-slate-500">
          T+{simulationTimeFormatted}
        </span>
      </div>

      <p className="text-xs text-slate-800 leading-relaxed font-sans">
        {interpretation}
      </p>

      {/* Metric highlight badges */}
      <div className="mt-3 pt-2.5 border-t border-slate-200/70 flex flex-wrap items-center gap-3 text-[11px] font-mono">
        <div className="flex items-center space-x-1">
          <span className="text-slate-500">STATUS:</span>
          <span className="font-bold text-slate-900">{String(oracleStatus).replace(/_/g, ' ')}</span>
        </div>
        <span className="text-slate-300">&bull;</span>
        <div className="flex items-center space-x-1">
          <span className="text-slate-500">ACTION:</span>
          <span className="font-bold text-slate-900">{decision.action}</span>
        </div>
        <span className="text-slate-300">&bull;</span>
        <div className="flex items-center space-x-1">
          <span className="text-slate-500">SOURCE:</span>
          <span className="font-bold text-blue-700">{decision.selected_source}</span>
        </div>
        {collateral.difference && collateral.difference > 0 ? (
          <>
            <span className="text-slate-300">&bull;</span>
            <div className="flex items-center space-x-1 text-emerald-700 font-bold">
              <span>PROTECTED:</span>
              <span>+${collateral.difference.toFixed(2)}/unit</span>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
};
