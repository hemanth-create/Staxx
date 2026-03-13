/**
 * ProviderBreakdown - Donut chart showing spend by provider.
 * Center text displays total spend. Legend with provider colors.
 */

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { motion } from "framer-motion";
import { GlassPanel } from "../../components/GlassPanel";
import { providerBreakdownData, totalSpend } from "./mockData";

function ProviderTooltipContent({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0];
  const pct = ((data.value / totalSpend) * 100).toFixed(1);

  return (
    <div className="bg-zinc-950/95 border border-white/10 rounded-lg p-3 backdrop-blur-xl shadow-xl">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: data.payload.color }} />
        <span className="text-sm font-semibold text-white">{data.name}</span>
      </div>
      <p className="text-xs text-zinc-300">
        Spend: <span className="text-white font-medium">${data.value.toLocaleString()}</span>
      </p>
      <p className="text-xs text-zinc-300">
        Share: <span className="text-white font-medium">{pct}%</span>
      </p>
    </div>
  );
}

function CenterLabel({ viewBox }) {
  if (!viewBox) return null;
  const { cx = 150, cy = 150 } = viewBox;
  const x = typeof cx === "string" ? 150 : cx;
  const y = typeof cy === "string" ? 150 : cy;

  return (
    <g>
      <text
        x={x}
        y={y - 10}
        textAnchor="middle"
        dominantBaseline="middle"
        className="fill-zinc-400"
        style={{ fontSize: 12 }}
      >
        Total Spend
      </text>
      <text
        x={x}
        y={y + 14}
        textAnchor="middle"
        dominantBaseline="middle"
        className="fill-white"
        style={{ fontSize: 22, fontWeight: 700 }}
      >
        ${totalSpend.toLocaleString()}
      </text>
    </g>
  );
}

function CustomLegend({ payload }) {
  return (
    <div className="flex flex-wrap justify-center gap-4 mt-4">
      {payload.map((entry) => {
        const item = providerBreakdownData.find((d) => d.name === entry.value);
        const pct = item ? ((item.value / totalSpend) * 100).toFixed(1) : "0";
        return (
          <motion.div
            key={entry.value}
            whileHover={{ scale: 1.05 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/3 border border-white/6"
          >
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-xs text-zinc-300">{entry.value}</span>
            <span className="text-xs font-medium text-white">{pct}%</span>
          </motion.div>
        );
      })}
    </div>
  );
}

export function ProviderBreakdown() {
  return (
    <GlassPanel>
      <h2 className="text-lg font-semibold text-white mb-1">Provider Breakdown</h2>
      <p className="text-sm text-zinc-400 mb-4">Spend distribution across LLM providers</p>

      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={providerBreakdownData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={75}
            outerRadius={110}
            paddingAngle={3}
            strokeWidth={0}
            animationDuration={800}
            animationBegin={200}
          >
            {providerBreakdownData.map((entry) => (
              <Cell
                key={entry.name}
                fill={entry.color}
                style={{ filter: "drop-shadow(0 0 6px rgba(0,0,0,0.3))" }}
              />
            ))}
            <CenterLabel viewBox={{ cx: 150, cy: 150 }} />
          </Pie>
          <Tooltip content={<ProviderTooltipContent />} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Provider detail cards */}
      <div className="grid grid-cols-2 gap-3 mt-4">
        {providerBreakdownData.map((provider) => (
          <motion.div
            key={provider.name}
            whileHover={{ scale: 1.02 }}
            className="rounded-lg bg-white/3 border border-white/6 p-3"
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: provider.color }} />
              <span className="text-sm font-medium text-white">{provider.name}</span>
            </div>
            <p className="text-lg font-bold text-white">${provider.value.toLocaleString()}</p>
            <p className="text-xs text-zinc-500">
              {((provider.value / totalSpend) * 100).toFixed(1)}% of total
            </p>
          </motion.div>
        ))}
      </div>
    </GlassPanel>
  );
}
