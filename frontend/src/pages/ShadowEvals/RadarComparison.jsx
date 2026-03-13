/**
 * RadarComparison - Side-by-side radar chart comparing original vs candidate model.
 * Metrics: cost efficiency, latency, quality, error rate, consistency.
 */

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { GlassPanel } from "../../components/GlassPanel";

function RadarTooltipContent({ active, payload }) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-zinc-950/95 border border-white/10 rounded-lg p-3 backdrop-blur-xl shadow-xl">
      <p className="text-xs font-semibold text-white mb-1.5">{payload[0]?.payload?.metric}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-xs text-zinc-400">{entry.name}:</span>
          <span className="text-xs font-medium text-white">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

export function RadarComparison({ radarMetrics, originalModel, candidateModel }) {
  const data = [
    {
      metric: "Cost Efficiency",
      original: Math.round(radarMetrics.original.cost),
      candidate: Math.round(radarMetrics.candidate.cost),
    },
    {
      metric: "Latency",
      original: Math.round(radarMetrics.original.latency),
      candidate: Math.round(radarMetrics.candidate.latency),
    },
    {
      metric: "Quality",
      original: Math.round(radarMetrics.original.quality),
      candidate: Math.round(radarMetrics.candidate.quality),
    },
    {
      metric: "Error Rate",
      original: Math.round(radarMetrics.original.errorRate),
      candidate: Math.round(radarMetrics.candidate.errorRate),
    },
    {
      metric: "Consistency",
      original: Math.round(radarMetrics.original.consistency),
      candidate: Math.round(radarMetrics.candidate.consistency),
    },
  ];

  return (
    <GlassPanel>
      <h3 className="text-sm font-semibold text-white mb-1">Performance Comparison</h3>
      <p className="text-xs text-zinc-500 mb-4">Higher is better across all axes</p>

      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid stroke="rgba(255,255,255,0.08)" />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: "#a1a1aa", fontSize: 11 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: "#52525b", fontSize: 10 }}
            axisLine={false}
          />
          <Tooltip content={<RadarTooltipContent />} />
          <Radar
            name={originalModel}
            dataKey="original"
            stroke="#ef4444"
            fill="#ef4444"
            fillOpacity={0.15}
            strokeWidth={2}
            animationDuration={800}
          />
          <Radar
            name={candidateModel}
            dataKey="candidate"
            stroke="#22c55e"
            fill="#22c55e"
            fillOpacity={0.15}
            strokeWidth={2}
            animationDuration={800}
            animationBegin={200}
          />
          <Legend
            formatter={(value) => (
              <span className="text-xs text-zinc-400">{value}</span>
            )}
          />
        </RadarChart>
      </ResponsiveContainer>
    </GlassPanel>
  );
}
