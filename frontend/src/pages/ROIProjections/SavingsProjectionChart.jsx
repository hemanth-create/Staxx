/**
 * SavingsProjectionChart - 12-month cumulative savings visualization.
 * Shows expected savings with confidence interval band and Staxx subscription cost overlay.
 */

import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { GlassPanel } from "../../components/GlassPanel";

// Custom tooltip (defined outside component to prevent Recharts remount)
function CustomTooltip({ active, payload }) {
  if (active && payload?.length) {
    const point = payload[0].payload;
    return (
      <div className="bg-zinc-950/95 border border-white/10 rounded-lg p-3 backdrop-blur-xl shadow-xl">
        <p className="text-xs text-zinc-400 font-semibold mb-2">{point.label}</p>
        <div className="space-y-1 text-xs">
          <p className="text-green-400">
            Expected: ${(point.expectedSavings / 1000).toFixed(1)}k
          </p>
          <p className="text-green-400/60">
            CI: ${(point.ciLower / 1000).toFixed(1)}k – ${(point.ciUpper / 1000).toFixed(1)}k
          </p>
          <p className="text-white/40">Staxx Cost: ${(point.staxxCost / 1000).toFixed(1)}k</p>
          <p className="text-sky-400 font-semibold">
            Net: ${((point.cumulativeSavings - point.staxxCost) / 1000).toFixed(1)}k
          </p>
        </div>
      </div>
    );
  }
  return null;
}

function SavingsProjectionChart({ data = [] }) {
  if (!data.length) return null;

  // Find break-even month (first month where cumulativeSavings > staxxCost)
  const breakEvenMonth = data.find(
    (d) => d.cumulativeSavings > d.staxxCost
  )?.month || 1;

  // Format Y-axis label as $Xk
  const formatYAxis = (value) => `$${(value / 1000).toFixed(0)}k`;

  return (
    <GlassPanel>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">12-Month Savings Projection</h3>
        <p className="text-sm text-zinc-400 mt-1">
          Cumulative savings including Staxx Intelligence subscription costs
        </p>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart
          data={data}
          margin={{ top: 24, right: 24, left: 0, bottom: 24 }}
        >
          <defs>
            {/* Gradient for the main savings area */}
            <linearGradient id="savingsGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="0"
            stroke="rgba(255,255,255,0.05)"
            vertical={false}
          />
          <XAxis
            dataKey="label"
            stroke="rgba(255,255,255,0.3)"
            style={{ fontSize: 12, fill: "#a1a1aa" }}
          />
          <YAxis
            stroke="rgba(255,255,255,0.3)"
            tickFormatter={formatYAxis}
            style={{ fontSize: 12, fill: "#a1a1aa" }}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* CI Band - Lower bound (invisible, just establishes baseline) */}
          <Area
            dataKey="ciLower"
            fill="transparent"
            stroke="none"
            isAnimationActive={true}
            animationDuration={1200}
          />

          {/* CI Band - Upper bound fill (creates the visible band) */}
          <Area
            dataKey="ciUpper"
            fill="rgba(34, 197, 94, 0.12)"
            stroke="none"
            isAnimationActive={true}
            animationDuration={1200}
          />

          {/* Expected Savings - Main line and area */}
          <Area
            dataKey="cumulativeSavings"
            fill="url(#savingsGradient)"
            stroke="#22c55e"
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={true}
            animationDuration={1200}
          />

          {/* Staxx Subscription Cost - Dotted line */}
          <Line
            dataKey="staxxCost"
            stroke="rgba(255,255,255,0.4)"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            dot={false}
            isAnimationActive={true}
            animationDuration={1200}
            name="Staxx Cost"
          />

          {/* Break-even reference line */}
          <ReferenceLine
            x={`M${breakEvenMonth}`}
            stroke="rgba(34, 197, 94, 0.5)"
            strokeDasharray="3 3"
            label={{
              value: `Break-even: Month ${breakEvenMonth}`,
              position: "top",
              fill: "#22c55e",
              fontSize: 11,
              fontWeight: 600,
              offset: 10,
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-6 flex items-center gap-6 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-green-500" />
          <span className="text-zinc-400">Expected Savings</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-green-500/30" />
          <span className="text-zinc-400">Confidence Interval (±8%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 border-t border-dashed border-white/40" />
          <span className="text-zinc-400">Staxx Subscription Cost</span>
        </div>
      </div>
    </GlassPanel>
  );
}

export default SavingsProjectionChart;
