/**
 * CostAnomalyTimeline - Line chart with gradient fill, anomaly markers,
 * and projected-savings overlay.
 */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceDot,
} from "recharts";
import { GlassPanel } from "../../components/GlassPanel";
import { costTimelineData } from "./mockData";

function AnomalyTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;

  const dataPoint = costTimelineData.find((d) => d.date === label);

  return (
    <div className="bg-zinc-950/95 border border-white/10 rounded-lg p-3 backdrop-blur-xl shadow-xl max-w-xs">
      <p className="text-sm font-semibold text-white mb-2">{label}</p>
      <div className="space-y-1.5">
        {payload.map((entry) => (
          <div key={entry.dataKey} className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: entry.stroke || entry.color }}
            />
            <span className="text-xs text-zinc-400">{entry.name}:</span>
            <span className="text-xs font-medium text-white">
              ${entry.value?.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
      {dataPoint?.isAnomaly && (
        <div className="mt-2 pt-2 border-t border-white/10">
          <p className="text-xs text-red-400 font-medium">Anomaly Detected</p>
          <p className="text-xs text-zinc-400 mt-0.5">{dataPoint.anomalyReason}</p>
        </div>
      )}
    </div>
  );
}

function AnomalyDot(props) {
  const { cx, cy, payload } = props;
  if (!payload?.isAnomaly) return null;

  return (
    <g>
      {/* Glow ring */}
      <circle cx={cx} cy={cy} r={10} fill="rgba(239, 68, 68, 0.2)" />
      {/* Main dot */}
      <circle cx={cx} cy={cy} r={5} fill="#ef4444" stroke="#fafafa" strokeWidth={1.5} />
    </g>
  );
}

export function CostAnomalyTimeline() {
  const anomalyPoints = costTimelineData.filter((d) => d.isAnomaly);

  return (
    <GlassPanel>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Cost Anomaly Timeline</h2>
          <p className="text-sm text-zinc-400">
            Daily spend with anomaly detection. Dotted line shows projected spend if swaps applied.
          </p>
        </div>
        {anomalyPoints.length > 0 && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/15 border border-red-500/30">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs font-medium text-red-400">
              {anomalyPoints.length} anomal{anomalyPoints.length === 1 ? "y" : "ies"}
            </span>
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={costTimelineData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="spendAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="projectedAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="4" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="date"
            stroke="rgba(255,255,255,0.05)"
            tick={{ fill: "#a1a1aa", fontSize: 11 }}
            tickLine={false}
            interval={4}
          />
          <YAxis
            stroke="rgba(255,255,255,0.05)"
            tick={{ fill: "#a1a1aa", fontSize: 11 }}
            tickLine={false}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip content={<AnomalyTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: "12px" }}
            formatter={(value) => (
              <span className="text-xs text-zinc-400">{value}</span>
            )}
          />

          {/* Projected savings area */}
          <Area
            type="monotone"
            dataKey="projectedWithSwaps"
            stroke="#22c55e"
            strokeWidth={1.5}
            strokeDasharray="6 3"
            fill="url(#projectedAreaGradient)"
            name="Projected (post-swap)"
            dot={false}
            animationDuration={1200}
          />

          {/* Actual spend area */}
          <Area
            type="monotone"
            dataKey="spend"
            stroke="#0ea5e9"
            strokeWidth={2}
            fill="url(#spendAreaGradient)"
            name="Actual Spend"
            dot={<AnomalyDot />}
            activeDot={{ r: 4, stroke: "#0ea5e9", fill: "#fafafa" }}
            animationDuration={1200}
          />

          {/* Anomaly reference dots with labels */}
          {anomalyPoints.map((point) => {
            const idx = costTimelineData.indexOf(point);
            return (
              <ReferenceDot
                key={idx}
                x={point.date}
                y={point.spend}
                r={0}
                label={{
                  value: "!",
                  position: "top",
                  fill: "#ef4444",
                  fontSize: 14,
                  fontWeight: "bold",
                  offset: 15,
                }}
              />
            );
          })}
        </AreaChart>
      </ResponsiveContainer>
    </GlassPanel>
  );
}
