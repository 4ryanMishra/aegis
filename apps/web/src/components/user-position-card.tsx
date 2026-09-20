import React, { useState, useEffect } from 'react';
import { UserPositionState, SimulationSnapshot } from '@/lib/types';
import { 
  Coins, 
  ArrowDownRight, 
  ArrowUpRight, 
  ShieldCheck, 
  AlertTriangle, 
  Lock, 
  Percent, 
  DollarSign, 
  Wallet,
  Sparkles,
  Info
} from 'lucide-react';

interface UserPositionCardProps {
  position?: UserPositionState;
  snapshot: SimulationSnapshot;
  onUpdatePosition: (collateralAmount?: number, debtAmount?: number, setMaxBorrow?: boolean) => Promise<void>;
}

export const UserPositionCard: React.FC<UserPositionCardProps> = ({
  position,
  snapshot,
  onUpdatePosition,
}) => {
  // Default fallback if position not yet loaded
  const pos: UserPositionState = position || {
    user_address: '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
    collateral_asset: 'Tokenized Gold (XAU)',
    collateral_amount: 10.0,
    collateral_value: 40500.0,
    effective_oracle_price: snapshot.decision?.final_price ?? snapshot.consensus?.consensus_price ?? snapshot.multipli_observation?.price ?? 4050.0,
    debt_amount: 28000.0,
    current_ltv: 0.691,
    effective_ltv: 0.80,
    max_borrow_capacity: 32400.0,
    borrowing_headroom: 4400.0,
    health_factor: 1.16,
    protocol_state: 'NORMAL',
    position_status: 'HEALTHY',
  };

  const [collateralInput, setCollateralInput] = useState<string>(pos.collateral_amount.toString());
  const [debtInput, setDebtInput] = useState<string>(pos.debt_amount.toString());
  const [isUpdating, setIsUpdating] = useState<boolean>(false);

  // Sync inputs when position updates from external resets
  useEffect(() => {
    if (position) {
      setCollateralInput(position.collateral_amount.toString());
      setDebtInput(position.debt_amount.toString());
    }
  }, [position?.collateral_amount, position?.debt_amount]);

  const handleDepositSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseFloat(collateralInput);
    if (!isNaN(val) && val >= 0) {
      setIsUpdating(true);
      try {
        await onUpdatePosition(val, undefined, false);
      } finally {
        setIsUpdating(false);
      }
    }
  };

  const handleBorrowSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseFloat(debtInput);
    if (!isNaN(val) && val >= 0) {
      setIsUpdating(true);
      try {
        await onUpdatePosition(undefined, val, false);
      } finally {
        setIsUpdating(false);
      }
    }
  };

  const handleMaxBorrow = async () => {
    setIsUpdating(true);
    try {
      await onUpdatePosition(undefined, undefined, true);
    } finally {
      setIsUpdating(false);
    }
  };

  const getStatusBadge = () => {
    switch (pos.position_status) {
      case 'HEALTHY':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            HEALTHY (HF {pos.health_factor >= 99 ? '∞' : `${pos.health_factor.toFixed(2)}x`})
          </span>
        );
      case 'RESTRICTED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-300 animate-pulse">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            RESTRICTED LTV (50%)
          </span>
        );
      case 'OVER_LIMIT':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-300">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            OVER BORROW LIMIT
          </span>
        );
      case 'HALTED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-300">
            <Lock className="w-3.5 h-3.5 text-purple-600" />
            PROTOCOL HALTED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-300">
            {pos.position_status}
          </span>
        );
    }
  };

  const healthPct = Math.min(100, Math.max(0, (pos.health_factor / 1.5) * 100));
  const ltvUsagePct = pos.effective_ltv > 0 ? (pos.current_ltv / pos.effective_ltv) * 100 : 100;

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-borderHairline pb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-amber-100 border border-amber-200 flex items-center justify-center text-amber-800">
            <Coins className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                RWAUSD Collateral Vault
              </h3>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                PROTOTYPE SIMULATION
              </span>
            </div>
            <div className="text-[11px] font-mono text-slate-500">
              Vault: {pos.user_address.slice(0, 6)}...{pos.user_address.slice(-4)} • Collateral: {pos.collateral_asset}
            </div>
          </div>
        </div>
        <div>
          {getStatusBadge()}
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        {/* Metric 1: Collateral Valuation */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 uppercase font-mono flex items-center justify-between">
            <span>Collateral Value</span>
            <span className="text-slate-400 font-sans">@{pos.effective_oracle_price.toFixed(2)}/oz</span>
          </div>
          <div className="font-mono font-bold text-sm text-slate-900 mt-1">
            ${pos.collateral_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {pos.collateral_amount.toFixed(2)} oz deposited
          </div>
        </div>

        {/* Metric 2: Max Borrow Capacity */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 uppercase font-mono flex items-center justify-between">
            <span>Max Borrow Cap</span>
            <span className={`font-bold ${pos.effective_ltv >= 0.8 ? 'text-emerald-700' : 'text-amber-700'}`}>
              {(pos.effective_ltv * 100).toFixed(0)}% LTV
            </span>
          </div>
          <div className="font-mono font-bold text-sm text-slate-900 mt-1">
            ${pos.max_borrow_capacity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {pos.protocol_state} Policy
          </div>
        </div>

        {/* Metric 3: Current Debt */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 uppercase font-mono flex items-center justify-between">
            <span>Current Debt</span>
            <span className="font-mono text-slate-600">{(pos.current_ltv * 100).toFixed(1)}% LTV</span>
          </div>
          <div className="font-mono font-bold text-sm text-blue-900 mt-1">
            ${pos.debt_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            RWAUSD Minted
          </div>
        </div>

        {/* Metric 4: Health / Headroom */}
        <div className="p-2.5 bg-surfaceSubtle rounded border border-borderHairline">
          <div className="text-[10px] text-slate-500 uppercase font-mono flex items-center justify-between">
            <span>Headroom / Health</span>
            <span className={`font-bold ${pos.borrowing_headroom >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
              {pos.health_factor >= 99 ? '∞' : `${pos.health_factor.toFixed(2)}x`}
            </span>
          </div>
          <div className={`font-mono font-bold text-sm mt-1 ${pos.borrowing_headroom >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
            {pos.borrowing_headroom >= 0 ? `+$${pos.borrowing_headroom.toFixed(2)}` : `-$${Math.abs(pos.borrowing_headroom).toFixed(2)}`}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {pos.borrowing_headroom >= 0 ? 'Available to borrow' : 'Over collateral limit'}
          </div>
        </div>
      </div>

      {/* LTV & Health Bars */}
      <div className="bg-slate-50 p-3 rounded border border-slate-200/80 space-y-2">
        <div className="flex items-center justify-between text-[11px] font-mono">
          <span className="text-slate-600 flex items-center gap-1">
            <Percent className="w-3.5 h-3.5 text-slate-400" />
            LTV Utilization ({((pos.current_ltv) * 100).toFixed(1)}% of {(pos.effective_ltv * 100).toFixed(0)}% max)
          </span>
          <span className={`font-bold ${ltvUsagePct > 100 ? 'text-rose-700' : ltvUsagePct > 85 ? 'text-amber-700' : 'text-emerald-700'}`}>
            {ltvUsagePct.toFixed(1)}% of cap
          </span>
        </div>
        <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-300 ${
              ltvUsagePct > 100 ? 'bg-rose-500' : ltvUsagePct > 85 ? 'bg-amber-500' : 'bg-emerald-500'
            }`}
            style={{ width: `${Math.min(100, ltvUsagePct)}%` }}
          />
        </div>
      </div>

      {/* Interactive Controls (Deposit & Borrow) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        {/* Deposit Control */}
        <form onSubmit={handleDepositSubmit} className="p-3 bg-surfaceSubtle rounded border border-borderHairline space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
              <ArrowDownRight className="w-3.5 h-3.5 text-emerald-600" />
              Deposit Tokenized Gold (oz)
            </label>
            <span className="text-[10px] font-mono text-slate-500">Current: {pos.collateral_amount.toFixed(2)} oz</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              step="0.1"
              min="0"
              value={collateralInput}
              onChange={(e) => setCollateralInput(e.target.value)}
              className="flex-1 px-2.5 py-1.5 text-xs font-mono bg-white border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. 10.0"
              disabled={isUpdating}
            />
            <button
              type="submit"
              disabled={isUpdating}
              className="px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white rounded transition-colors disabled:opacity-50"
            >
              Update Collateral
            </button>
          </div>
        </form>

        {/* Borrow Control */}
        <form onSubmit={handleBorrowSubmit} className="p-3 bg-surfaceSubtle rounded border border-borderHairline space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
              <ArrowUpRight className="w-3.5 h-3.5 text-blue-600" />
              Borrow RWAUSD Debt ($)
            </label>
            <span className="text-[10px] font-mono text-slate-500">Cap: ${pos.max_borrow_capacity.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              step="1"
              min="0"
              value={debtInput}
              onChange={(e) => setDebtInput(e.target.value)}
              className="flex-1 px-2.5 py-1.5 text-xs font-mono bg-white border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. 700.0"
              disabled={isUpdating || pos.protocol_state === 'HALTED'}
            />
            <button
              type="button"
              onClick={handleMaxBorrow}
              disabled={isUpdating || pos.protocol_state === 'HALTED'}
              className="px-2 py-1.5 text-xs font-mono font-bold bg-slate-200 hover:bg-slate-300 text-slate-700 rounded transition-colors disabled:opacity-50"
              title="Borrow maximum capacity"
            >
              MAX
            </button>
            <button
              type="submit"
              disabled={isUpdating || pos.protocol_state === 'HALTED'}
              className="px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
            >
              Update Debt
            </button>
          </div>
        </form>
      </div>

      {/* Informational Footer explaining AEGIS connection */}
      <div className="text-[11px] text-slate-500 bg-slate-50/70 p-2.5 rounded border border-slate-200/60 flex items-start gap-2">
        <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
        <span>
          <strong>Why this matters:</strong> During market stress or stale oracle updates, AEGIS dynamically caps maximum borrowing capacity (e.g. restricting LTV from 80% to 50%) and substitutes resilient P_DEC consensus, preserving protocol solvency before bad debt can form.
        </span>
      </div>
    </div>
  );
};
