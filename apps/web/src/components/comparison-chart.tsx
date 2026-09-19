import React from 'react';
import { ScenarioRecord } from '@/lib/types';
import { BarChart3 } from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Cell,
  CartesianGrid,
} from 'recharts';

interface ComparisonChartProps {
  scenario: ScenarioRecord;
}

export const ComparisonChart: React.FC<ComparisonChartProps> = ({ scenario }) => {
  const { p_osm, p_dec, p_market, validators, window } = scenario;

  // Build chart points
  const data = [
    {
      name: 'P_OSM (Baseline)',
      price: p_osm.value,
      type: 'OSM',
      color: '#475569',
      isMarket: false,
    },
    ...validators.map((v) => ({
      name: v.validator_id,
      price: v.estimated_price,
      lower: v.uncertainty_lower,
      upper: v.uncertainty_upper,
      type: 'VALIDATOR',
      color: '#3B82F6',
      isMarket: false,
    })),
    ...(p_dec.value !== null
      ? [
          {
            name: 'P_DEC (Median)',
            price: p_dec.value,
            type: 'P_DEC',
            color: '#1D4ED8',
            isMarket: false,
          },
        ]
      : []),
    ...(p_market.value !== null
      ? [
          {
            name: 'P_MARKET (T1)',
            price: p_market.value,
            type: 'MARKET',
            color: '#D97706',
            isMarket: true,
          },
        ]
      : []),
  ];

  // Calculate domain min/max
  const allPrices = data.map((d) => d.price).filter((p) => p !== undefined && p !== null);
  const minPrice = allPrices.length ? Math.floor(Math.min(...allPrices) * 0.98) : 85;
  const maxPrice = allPrices.length ? Math.ceil(Math.max(...allPrices) * 1.02) : 105;

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <BarChart3 className="w-4 h-4 text-slate-500" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Valuation Dispersion & Market Alignment Chart
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-medium text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-slate-600 inline-block" />
            P_OSM
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-blue-600 inline-block" />
            Validators / P_DEC
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-amber-600 inline-block" />
            P_MARKET
          </span>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
            <XAxis
              dataKey="name"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#CBD5E1' }}
            />
            <YAxis
              domain={[minPrice, maxPrice]}
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#CBD5E1' }}
              tickFormatter={(v) => `$${v}`}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const pt = payload[0].payload;
                  return (
                    <div className="bg-surface border border-borderHairline p-2.5 rounded shadow-lg text-xs">
                      <div className="font-semibold text-slate-900 mb-1">{pt.name}</div>
                      <div className="font-mono text-slate-700">
                        Price: <span className="font-bold">${pt.price.toFixed(2)}</span>
                      </div>
                      {pt.lower && (
                        <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                          Range: [${pt.lower.toFixed(2)} &ndash; ${pt.upper.toFixed(2)}]
                        </div>
                      )}
                      <div className="text-[10px] text-slate-400 mt-1 uppercase font-mono">
                        Type: {pt.type}
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            {p_market.value !== null && (
              <ReferenceLine
                y={p_market.value}
                stroke="#D97706"
                strokeDasharray="3 3"
                label={{
                  value: `Market: $${p_market.value.toFixed(2)}`,
                  position: 'insideTopRight',
                  fill: '#D97706',
                  fontSize: 10,
                }}
              />
            )}
            <Bar dataKey="price" radius={[3, 3, 0, 0]} maxBarSize={48}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
