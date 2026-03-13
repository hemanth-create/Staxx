/**
 * SpendTreemap - Recharts Treemap showing spend distribution by task_type -> model.
 * Hover shows spend, % of total, request count. Click drills down to task detail.
 */

import { useState, useCallback } from "react";
import { Treemap, ResponsiveContainer, Tooltip } from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { GlassPanel } from "../../components/GlassPanel";
import { treemapData, totalSpend, TASK_COLORS } from "./mockData";

// Custom treemap cell content renderer
function CustomTreemapContent({ x, y, width, height, name, value, color, depth }) {
  if (width < 30 || height < 20) return null;

  const fontSize = width > 100 && height > 40 ? 13 : 11;
  const showValue = width > 60 && height > 35;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={4}
        ry={4}
        style={{
          fill: color || "#0ea5e9",
          fillOpacity: depth === 1 ? 0.85 : 0.6,
          stroke: "rgba(255,255,255,0.1)",
          strokeWidth: 1,
          cursor: "pointer",
        }}
      />
      {width > 40 && height > 25 && (
        <text
          x={x + width / 2}
          y={y + height / 2 - (showValue ? 6 : 0)}
          textAnchor="middle"
          dominantBaseline="middle"
          style={{
            fill: "#fafafa",
            fontSize,
            fontWeight: 500,
            pointerEvents: "none",
          }}
        >
          {name.length > width / 8 ? name.slice(0, Math.floor(width / 8)) + "..." : name}
        </text>
      )}
      {showValue && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 12}
          textAnchor="middle"
          dominantBaseline="middle"
          style={{
            fill: "rgba(255,255,255,0.7)",
            fontSize: 10,
            pointerEvents: "none",
          }}
        >
          ${value?.toLocaleString()}
        </text>
      )}
    </g>
  );
}

function TreemapTooltipContent({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  const pctOfTotal = ((data.size / totalSpend) * 100).toFixed(1);

  return (
    <div className="bg-zinc-950/95 border border-white/10 rounded-lg p-3 backdrop-blur-xl shadow-xl">
      <p className="text-sm font-semibold text-white mb-1">{data.name}</p>
      {data.provider && (
        <p className="text-xs text-zinc-400 mb-2">{data.provider}</p>
      )}
      <div className="space-y-1">
        <p className="text-xs text-zinc-300">
          Spend: <span className="text-white font-medium">${data.size?.toLocaleString()}</span>
        </p>
        <p className="text-xs text-zinc-300">
          % of total: <span className="text-white font-medium">{pctOfTotal}%</span>
        </p>
        {data.requests && (
          <p className="text-xs text-zinc-300">
            Requests: <span className="text-white font-medium">{data.requests?.toLocaleString()}</span>
          </p>
        )}
      </div>
    </div>
  );
}

export function SpendTreemap() {
  const [drillTask, setDrillTask] = useState(null);

  // Flatten treemap data for Recharts format
  const flatData = drillTask
    ? drillTask.children.map((child) => ({
        name: child.name,
        size: child.size,
        requests: child.requests,
        provider: child.provider,
        color: drillTask.color,
      }))
    : treemapData.map((task) => ({
        name: task.name,
        size: task.children.reduce((s, c) => s + c.size, 0),
        color: task.color,
        children: task.children,
      }));

  const handleClick = useCallback(
    (node) => {
      if (drillTask) return; // Already drilled in
      const task = treemapData.find((t) => t.name === node.name);
      if (task) setDrillTask(task);
    },
    [drillTask]
  );

  return (
    <GlassPanel>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Spend Treemap</h2>
          <p className="text-sm text-zinc-400">
            {drillTask
              ? `${drillTask.name} — model breakdown`
              : "Spend distribution by task type. Click to drill down."}
          </p>
        </div>
        <AnimatePresence>
          {drillTask && (
            <motion.button
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              onClick={() => setDrillTask(null)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-zinc-300
                         bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
            >
              <ArrowLeft size={14} />
              Back
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* Color legend */}
      {!drillTask && (
        <div className="flex flex-wrap gap-3 mb-4">
          {treemapData.map((task) => (
            <div key={task.name} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: task.color }}
              />
              <span className="text-xs text-zinc-400">{task.name}</span>
            </div>
          ))}
        </div>
      )}

      <ResponsiveContainer width="100%" height={360}>
        <Treemap
          data={flatData}
          dataKey="size"
          nameKey="name"
          stroke="rgba(255,255,255,0.08)"
          animationDuration={400}
          onClick={handleClick}
          content={({ x, y, width, height, name, value, depth, index }) => {
            const item = flatData[index] || {};
            return (
              <CustomTreemapContent
                x={x}
                y={y}
                width={width}
                height={height}
                name={name}
                value={value}
                color={item.color || TASK_COLORS.Summarization}
                depth={depth}
              />
            );
          }}
        >
          <Tooltip content={<TreemapTooltipContent />} />
        </Treemap>
      </ResponsiveContainer>
    </GlassPanel>
  );
}
