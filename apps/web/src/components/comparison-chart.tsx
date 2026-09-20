import React, { useState } from 'react';
import { TimeSeriesPoint, SimulationSnapshot, OracleObservation } from '@/lib/types';
import { TrendingUp, BarChart3, Layers, GitMerge } from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
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
  snapshot: SimulationSnapshot;
  timeSeries?: TimeSeriesPoint[];
}

export const ComparisonChart: React.FC<ComparisonChartProps> = ({
  snapshot,
  timeSeries = [],
}) => {
  const [viewMode, setViewMode] = useState<'STREAM' | 'DISPERSION'>('STREAM');

  const sources = snapshot.oracle_sources || [];
  const multipli = snapshot.multipli_observation;
  const consensus = snapshot.consensus;
  const market = snapshot.market_observation;

  // Dispersion bar data
  const dispersionData = [
    ...(multipli && multipli.price !== null && multipli.price > 0
      ? [
          {
            name: 'Multipli OSM',
            price: multipli.price,
            type: 'Target OSM (Delayed)',
            color: '#7C3AED',
          },
        ]
      : []),
    ...sources.map((s) => ({
      name: s.name,
      price: s.price,
      lower: s.price && s.confidence ? s.price - s.confidence : null,
      upper: s.price && s.confidence ? s.price + s.confidence : null,
      type: s.cluster_id === 'OUTLIER' ? 'Excluded Outlier' : 'Consensus Feed',
      color: s.cluster_id === 'OUTLIER' ? '#EF4444' : '#3B82F6',
    })),
    ...(consensus.consensus_price !== null && consensus.consensus_price > 0
      ? [
          {
            name: 'Consensus Median',
            price: consensus.consensus_price,
            type: 'Cluster Median',
            color: '#1D4ED8',
          },
        ]
      : []),
    ...(market && market.price !== null && market.price > 0
      ? [
          {
            name: 'Spot Market',
            price: market.price,
            type: 'Real-Time CLOB',
            color: '#D97706',
          },
        ]
      : []),
  ];

  // Calculate domain min/max
  const streamPrices: number[] = [];
  timeSeries.forEach((pt) => {
    if (pt.p_multipli != null) streamPrices.push(pt.p_multipli);
    if (pt.p_consensus != null) streamPrices.push(pt.p_consensus);
    if (pt.p_market != null) streamPrices.push(pt.p_market);
    if (pt.p_osm != null) streamPrices.push(pt.p_osm);
    if (pt.p_dec != null) streamPrices.push(pt.p_dec);
  });
  if (multipli?.price) streamPrices.push(multipli.price);
  if (consensus?.consensus_price) streamPrices.push(consensus.consensus_price);
  if (market?.price) streamPrices.push(market.price);

  const minPrice = streamPrices.length ? Math.floor(Math.min(...streamPrices) * 0.98) : 3800;
  const maxPrice = streamPrices.length ? Math.ceil(Math.max(...streamPrices) * 1.02) : 4500;

  return (
    <div className="bg-surface border border-borderHairline rounded shadow-card p-4 space-y-3">
      {/* Chart Header & View Mode Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-borderHairline pb-2.5">
        <div className="flex items-center space-x-2">
          {viewMode === 'STREAM' ? (
            <TrendingUp className="w-4 h-4 text-blue-600" />
          ) : (
            <BarChart3 className="w-4 h-4 text-slate-600" />
          )}
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
            {viewMode === 'STREAM'
              ? 'Multi-Oracle Time-Series Trajectory & Agreement Band'
              : 'Cross-Oracle Valuation Dispersion & Alignment'}
          </h3>
        </div>

        <div className="flex items-center space-x-3 text-[11px]">
          {/* Legend */}
          <div className="hidden sm:flex items-center gap-2.5 font-mono text-slate-600">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-purple-600 inline-block" />
              Multipli OSM
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-blue-600 inline-block" />
              Consensus Median
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-amber-600 inline-block" />
              Spot Reference
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
              Feed Dispersion
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
              margin={{ top: 10, right: 10, left: -10, bottom: 5 }}
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
                    const multipliVal = pt.p_multipli ?? pt.p_osm;
                    const consensusVal = pt.p_consensus ?? pt.p_dec;
                    const marketVal = pt.p_market;
                    return (
                      <div className="bg-surface border border-borderHairline p-2.5 rounded shadow-lg text-xs font-mono">
                        <div className="font-semibold text-slate-900 mb-1 border-b pb-1 font-sans">
                          Minute {pt.minute} ({label})
                        </div>
                        {multipliVal != null && (
                          <div className="text-purple-700">
                            Multipli OSM: <span className="font-bold">${multipliVal.toFixed(2)}</span>
                          </div>
                        )}
                        {consensusVal != null && (
                          <div className="text-blue-700">
                            Consensus Median: <span className="font-bold">${consensusVal.toFixed(2)}</span>
                          </div>
                        )}
                        {marketVal != null && (
                          <div className="text-amber-700">
                            Spot Reference: <span className="font-bold">${marketVal.toFixed(2)}</span>
                          </div>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              
              {/* Shaded Agreement Band */}
              <Area
                type="monotone"
                dataKey="cluster_max"
                stroke="none"
                fill="#3B82F6"
                fillOpacity={0.12}
                name="Cluster Agreement Band"
              />
              
              {/* Delayed Multipli OSM Line */}
              <Line
                type="stepAfter"
                dataKey={(d) => d.p_multipli ?? d.p_osm}
                stroke="#7C3AED"
                strokeWidth={2.5}
                dot={false}
                name="Multipli OSM (Delayed Buffer)"
              />
              
              {/* Cross-Oracle Consensus Line */}
              <Line
                type="monotone"
                dataKey={(d) => d.p_consensus ?? d.p_dec}
                stroke="#2563EB"
                strokeWidth={2.5}
                dot={{ r: 2, fill: '#2563EB' }}
                name="Consensus Median"
              />

              {/* Spot Market Line */}
              <Line
                type="monotone"
                dataKey="p_market"
                stroke="#D97706"
                strokeWidth={2}
                strokeDasharray="4 2"
                dot={{ r: 2, fill: '#D97706' }}
                name="Spot Reference"
              />
            </ComposedChart>
          ) : (
            <ComposedChart
              data={dispersionData}
              margin={{ top: 10, right: 10, left: -10, bottom: 20 }}
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
                        <div className="text-[10px] text-slate-400 mt-1 uppercase font-mono">
                          Role: {pt.type}
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {consensus.consensus_price !== null && (
                <ReferenceLine
                  y={consensus.consensus_price}
                  stroke="#2563EB"
                  strokeDasharray="3 3"
                  label={{
                    value: `Consensus: $${consensus.consensus_price.toFixed(2)}`,
                    position: 'insideTopRight',
                    fill: '#2563EB',
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
