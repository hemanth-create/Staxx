/**
 * SavingsWaterfall - Waterfall chart showing current spend -> savings -> projected total.
 * Bars animate in sequentially on mount.
 */

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { GlassPanel } from "../../components/GlassPanel";
import { buildWaterfallData, swapRecommendations, swapSummary } from "./mockData";

function WaterfallTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="bg-zinc-950/95 border border-white/10 rounded-lg p-3 backdrop-blur-xl shadow-xl max-w-xs">
      <p className="text-sm font-semibold text-white mb-1">{data.name}</p>
      {data.isTotal ? (
        <p className="text-sm text-zinc-300">
          Total: <span className="text-white font-bold">${data.value.toLocaleString()}/mo</span>
        </p>
      ) : (
        <p className="text-sm text-green-400 font-medium">
          Savings: ${Math.abs(data.value).toLocaleString()}/mo
        </p>
      )}
      {data.runningTotal !== undefined && (
        <p className="text-xs text-zinc-500 mt-1">
          Running total: ${data.runningTotal.toLocaleString()}/mo
        </p>
      )}
    </div>
  );
}

export function SavingsWaterfall() {
  const waterfallData = useMemo(() => buildWaterfallData(swapRecommendations), []);

  // Transform for stacked bar (invisible base + visible portion)
  const chartData = useMemo(() => {
    let running = swapSummary.currentMonthlySpend;

    return waterfallData.map((item, idx) => {
      if (idx === 0) {
        // First bar: current spend
        return { ...item, base: 0, visible: item.value, displayName: "Current\nSpend" };
      }
      if (idx === waterfallData.length - 1) {
        // Last bar: projected total
        return { ...item, base: 0, visible: item.value, displayName: "Projected\nSpend" };
      }
      // Middle bars: savings (negative)
      const savingsAmt = Math.abs(item.value);
      running -= savingsAmt;
      return {
        ...item,
        base: running,
        visible: savingsAmt,
        displayName: item.shortName || item.name,
      };
    });
  }, [waterfallData]);

  return (
    <GlassPanel>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Savings Waterfall</h2>
          <p className="text-sm text-zinc-400">
            Impact of each recommended swap on total monthly spend
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-zinc-500">Total savings potential</p>
          <p className="text-xl font-bold text-green-400">
            ${swapSummary.totalProjectedSavings.toLocaleString()}/mo
          </p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={360}>
        <BarChart data={chartData} margin={{ top: 20, right: 20, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="4" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="displayName"
            stroke="rgba(255,255,255,0.05)"
            tick={{ fill: "#a1a1aa", fontSize: 10 }}
            tickLine={false}
            interval={0}
            height={50}
          />
          <YAxis
            stroke="rgba(255,255,255,0.05)"
            tick={{ fill: "#a1a1aa", fontSize: 11 }}
            tickLine={false}
            tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
          />
          <Tooltip content={<WaterfallTooltip />} />

          {/* Invisible base bar */}
          <Bar
            dataKey="base"
            stackId="stack"
            fill="transparent"
            isAnimationActive={false}
          />

          {/* Visible portion */}
          <Bar
            dataKey="visible"
            stackId="stack"
            radius={[4, 4, 0, 0]}
            animationDuration={800}
            animationBegin={200}
          >
            {chartData.map((entry, idx) => {
              let fill;
              if (idx === 0) fill = "#ef4444"; // Current: red
              else if (idx === chartData.length - 1) fill = "#0ea5e9"; // Projected: blue
              else fill = "#22c55e"; // Savings: green
              return <Cell key={entry.name} fill={fill} fillOpacity={0.8} />;
            })}
          </Bar>

          {/* Reference line at projected spend */}
          <ReferenceLine
            y={chartData[chartData.length - 1]?.visible || 0}
            stroke="#0ea5e9"
            strokeDasharray="4"
            strokeOpacity={0.4}
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex justify-center gap-6 mt-2">
        {[
          { color: "#ef4444", label: "Current Spend" },
          { color: "#22c55e", label: "Savings per Swap" },
          { color: "#0ea5e9", label: "Projected Spend" },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: item.color }} />
            <span className="text-xs text-zinc-400">{item.label}</span>
          </div>
        ))}
      </div>
    </GlassPanel>
  );
}
