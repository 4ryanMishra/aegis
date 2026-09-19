import React from 'react';
import { ValidatorObservation } from '@/lib/types';
import { Layers, Database, ExternalLink } from 'lucide-react';

interface ValidatorMatrixProps {
  validators: ValidatorObservation[];
  onInspectValidator: (val: ValidatorObservation) => void;
}

export const ValidatorMatrix: React.FC<ValidatorMatrixProps> = ({
  validators,
  onInspectValidator,
}) => {
  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card overflow-hidden">
      <div className="px-4 py-3 border-b border-borderHairline flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-slate-500" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Independent Validator Evidence Matrix
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-500">
          {validators.length} / 4 Observations Collected
        </span>
      </div>

      {validators.length === 0 ? (
        <div className="p-8 text-center text-xs text-secondaryText">
          Awaiting validator evidence submissions as verification window advances...
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-surfaceSubtle border-b border-borderHairline text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 px-3">Validator Node</th>
                <th className="py-2.5 px-3">Strategy / Methodology</th>
                <th className="py-2.5 px-3 text-right">Estimate</th>
                <th className="py-2.5 px-3 text-center">Uncertainty Bounds</th>
                <th className="py-2.5 px-3">Sources</th>
                <th className="py-2.5 px-3 text-center">Status</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderHairline">
              {validators.map((v) => (
                <tr 
                  key={v.validator_id}
                  className="hover:bg-slate-50/80 transition cursor-pointer"
                  onClick={() => onInspectValidator(v)}
                >
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                    {v.validator_id}
                  </td>
                  <td className="py-2.5 px-3 text-slate-700">
                    <div className="font-medium truncate max-w-[200px]" title={v.strategy_name}>
                      {v.strategy_name}
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      v{v.method_version}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900 tnum">
                    ${v.estimated_price.toFixed(2)}
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono text-slate-500 text-[11px] tnum">
                    [${v.uncertainty_lower.toFixed(2)} &ndash; ${v.uncertainty_upper.toFixed(2)}]
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">
                    <div className="flex items-center gap-1 text-[11px]">
                      <Database className="w-3 h-3 text-slate-400" />
                      <span>{v.source_ids.length} feeds</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                      {v.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        onInspectValidator(v);
                      }}
                      className="text-slate-400 hover:text-slate-800 transition"
                      title="Inspect Provenance"
                    >
                      <ExternalLink className="w-3.5 h-3.5 inline" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
