import React, { useState } from 'react';
import { ScenarioRecord, TimeSeriesPoint } from '@/lib/types';
import { LineChart as LineChartIcon, BarChart3, TrendingUp, Layers } from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  Line,
  Area,
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
  timeSeries?: TimeSeriesPoint[];
  uncertaintyHalfWidth?: number;
}

export const ComparisonChart: React.FC<ComparisonChartProps> = ({
  scenario,
  timeSeries = [],
  uncertaintyHalfWidth = 0.25,
}) => {
  const { p_osm, p_dec, p_market, validators } = scenario;
  const [viewMode, setViewMode] = useState<'STREAM' | 'DISPERSION'>('STREAM');

  // Dispersion bar data
  const dispersionData = [
    {
      name: 'P_OSM',
      price: p_osm.value,
      type: 'OSM Baseline',
      color: '#475569',
    },
    ...validators.map((v) => ({
      name: v.lane_id != null
        ? `LANE ${v.lane_id}`
        : String(v.validator_id || 'VALIDATOR'),
      price: v.estimated_price,
      lower: v.uncertainty_lower,
      upper: v.uncertainty_upper,
      type: 'Validator Lane',
      color: '#3B82F6',
    })),
    ...(p_dec.value !== null
      ? [
          {
            name: 'P_DEC',
            price: p_dec.value,
            type: 'Robust Median',
            color: '#1D4ED8',
          },
        ]
      : []),
    ...(p_market.value !== null
      ? [
          {
            name: 'P_MARKET',
            price: p_market.value,
            type: 'Market Stream',
            color: '#D97706',
          },
        ]
      : []),
  ];

  // Calculate domain min/max
  const streamPrices: number[] = [];
  timeSeries.forEach((pt) => {
    if (pt.p_osm != null) streamPrices.push(pt.p_osm);
    if (pt.p_dec != null) streamPrices.push(pt.p_dec);
    if (pt.p_market != null) streamPrices.push(pt.p_market);
  });
  if (p_osm.value) streamPrices.push(p_osm.value);
  if (p_dec.value) streamPrices.push(p_dec.value);
  if (p_market.value) streamPrices.push(p_market.value);

  const minPrice = streamPrices.length ? Math.floor(Math.min(...streamPrices) * 0.98) : 85;
  const maxPrice = streamPrices.length ? Math.ceil(Math.max(...streamPrices) * 1.02) : 105;

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4">
      
      {/* Chart Header & View Mode Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center space-x-2">
          {viewMode === 'STREAM' ? (
            <TrendingUp className="w-4 h-4 text-blue-600" />
          ) : (
            <BarChart3 className="w-4 h-4 text-slate-600" />
          )}
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
            {viewMode === 'STREAM'
              ? 'Real-Time Verification Window Trajectory & Confidence Band'
              : 'Valuation Dispersion & Cross-Lane Alignment'}
          </h3>
        </div>

        <div className="flex items-center space-x-3 text-[11px]">
          
          {/* Legend */}
          <div className="hidden sm:flex items-center gap-2.5 font-mono text-slate-600">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-slate-600 inline-block" />
              P_OSM
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-blue-600 inline-block" />
              P_DEC (&plusmn;{uncertaintyHalfWidth.toFixed(2)})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-amber-600 inline-block" />
              P_MARKET
            </span>
          </div>

          {/* Mode Toggle Buttons */}
          <div className="flex items-center bg-surfaceSubtle border border-borderHairline rounded p-0.5">
            <button
              onClick={() => setViewMode('STREAM')}
              className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${
                viewMode === 'STREAM'
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Live Stream
            </button>
            <button
              onClick={() => setViewMode('DISPERSION')}
              className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${
                viewMode === 'DISPERSION'
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Lane Dispersion
            </button>
          </div>

        </div>
      </div>

      {/* Chart Canvas */}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {viewMode === 'STREAM' && timeSeries.length > 0 ? (
            <ComposedChart
              data={timeSeries}
              margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
              <XAxis
                dataKey="time_label"
                stroke="#64748B"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: '#CBD5E1' }}
              />
              <YAxis
                domain={[minPrice, maxPrice]}
                stroke="#64748B"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: '#CBD5E1' }}
                tickFormatter={(v) => `$${v}`}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const pt = payload[0].payload as TimeSeriesPoint;
                    return (
                      <div className="bg-surface border border-borderHairline p-2.5 rounded shadow-lg text-xs font-mono">
                        <div className="font-semibold text-slate-900 mb-1 border-b pb-1 font-sans">
                          Minute {pt.minute} ({label})
                        </div>
                        {pt.p_osm != null && (
                          <div className="text-slate-600">
                            P_OSM: <span className="font-bold">${pt.p_osm.toFixed(2)}</span>
                          </div>
                        )}
                        <div className="text-blue-700">
                          P_DEC: <span className="font-bold">${pt.p_dec.toFixed(2)}</span>
                          <span className="text-[10px] text-blue-500 ml-1">
                            [&plusmn;${uncertaintyHalfWidth.toFixed(2)}]
                          </span>
                        </div>
                        <div className="text-amber-700">
                          P_MARKET: <span className="font-bold">${pt.p_market.toFixed(2)}</span>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              
              {/* Shaded P_DEC Uncertainty Area */}
              <Area
                type="monotone"
                dataKey="uncertainty_upper"
                stroke="none"
                fill="#3B82F6"
                fillOpacity={0.12}
                name="Uncertainty Band"
              />
              
              {/* Stale Baseline P_OSM Line */}
              <Line
                type="stepAfter"
                dataKey="p_osm"
                stroke="#475569"
                strokeWidth={2}
                dot={false}
                name="P_OSM (Baseline)"
              />
              
              {/* Live Decentralized P_DEC Line */}
              <Line
                type="monotone"
                dataKey="p_dec"
                stroke="#2563EB"
                strokeWidth={2.5}
                dot={{ r: 2, fill: '#2563EB' }}
                name="P_DEC (Median)"
              />

              {/* Attested Live P_MARKET Line */}
              <Line
                type="monotone"
                dataKey="p_market"
                stroke="#D97706"
                strokeWidth={2}
                strokeDasharray="4 2"
                dot={{ r: 2, fill: '#D97706' }}
                name="P_MARKET"
              />
            </ComposedChart>
          ) : (
            <ComposedChart
              data={dispersionData}
              margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
              <XAxis
                dataKey="name"
                stroke="#64748B"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: '#CBD5E1' }}
              />
              <YAxis
                domain={[minPrice, maxPrice]}
                stroke="#64748B"
                fontSize={10}
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
                          Price: <span className="font-bold">${pt.price ? pt.price.toFixed(2) : '--'}</span>
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
              <Bar dataKey="price" radius={[3, 3, 0, 0]} maxBarSize={44}>
                {dispersionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </ComposedChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
};
