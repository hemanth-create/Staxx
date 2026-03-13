/**
 * MetricCard - Glassmorphic metric display with animated counting,
 * trend arrow, and sparkline chart.
 */

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown } from "lucide-react";
import { GlassPanel } from "./GlassPanel";
import { SparkLine } from "./SparkLine";
import { useCountUp, useCountUpCurrency } from "../hooks/useCountUp";
import { mockSparklineData, calculateTrendPercent } from "../utils/mockData";

export function MetricCard({
  label,
  value,
  previousValue,
  currency = false,
  trend = "up",
  sparklineColor = "#0ea5e9",
}) {
  const trendPercent = calculateTrendPercent(value, previousValue);
  const isTrendingUp = trend === "up" || trendPercent > 0;

  // Determine trend color based on metric type
  let trendColor = "text-gray-400";
  if (isTrendingUp) {
    // For savings metrics, up is green; for costs, up is red
    trendColor =
      label.includes("Savings") || label.includes("savings")
        ? "text-green-500"
        : "text-red-500";
  } else {
    trendColor =
      label.includes("Savings") || label.includes("savings")
        ? "text-red-500"
        : "text-green-500";
  }

  // Always call both hooks, select after (Rules of Hooks)
  const countUpValue = useCountUp(value, 1);
  const countCurrencyValue = useCountUpCurrency(value, 1);
  const displayValue = currency ? countCurrencyValue : countUpValue;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <GlassPanel innerClassName="flex flex-col justify-between h-full">
        {/* Header: Label and Trend */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-400">{label}</h3>
          <div className={`flex items-center gap-1 ${trendColor}`}>
            {isTrendingUp ? (
              <TrendingUp size={16} />
            ) : (
              <TrendingDown size={16} />
            )}
            <span className="text-xs font-semibold">
              {Math.abs(trendPercent)}%
            </span>
          </div>
        </div>

        {/* Main Value (Animated) */}
        <motion.div className="mb-4">
          <motion.p
            className="text-3xl md:text-4xl font-bold text-white font-mono tracking-tight"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            {displayValue}
          </motion.p>
        </motion.div>

        {/* Sparkline Chart */}
        <div className="h-10 mt-2">
          <SparkLine
            data={mockSparklineData}
            color={sparklineColor}
            height={40}
          />
        </div>
      </GlassPanel>
    </motion.div>
  );
}
