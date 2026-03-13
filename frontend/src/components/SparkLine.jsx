/**
 * SparkLine - Tiny inline sparkline chart for metric cards.
 * Shows trend at a glance using Recharts.
 */

import { useId } from "react";
import { AreaChart, Area, ResponsiveContainer, Tooltip } from "recharts";
import { chartTheme } from "../theme/chartTheme";

export function SparkLine({ data = [], color = "#0ea5e9", height = 40 }) {
  const gradientId = useId();

  if (!data || data.length === 0) {
    return <div className="h-10 bg-white/5 rounded" />;
  }

  return (
    <div style={{ width: "100%", height, minHeight: height }}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(9,9,11,0.95)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "6px",
              padding: "6px",
              fontSize: 11,
            }}
            cursor={false}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            isAnimationActive={true}
            animationDuration={1000}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
