/**
 * DashboardHome - Main dashboard overview page.
 * Shows metrics, spend chart, task breakdown, and recommendations.
 */

import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ShoppingCart, TrendingUp } from "lucide-react";

import { DashboardLayout } from "../layouts/DashboardLayout";
import { MetricCard } from "../components/MetricCard";
import { GlassPanel } from "../components/GlassPanel";
import {
  mockMetrics,
  mockSpendOverTimeData,
  mockTopSpendByTask,
  mockRecommendations,
} from "../utils/mockData";

// Gradient definitions for charts
function ChartDefs() {
  return (
    <defs>
      <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
        <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
      </linearGradient>
      <linearGradient id="taskGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
        <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
      </linearGradient>
    </defs>
  );
}

function DashboardHome() {
  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Page Title */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-4xl font-bold text-white mb-2">
            Cost Intelligence Overview
          </h1>
          <p className="text-gray-400">
            Real-time insights into your LLM API spending and optimization
            opportunities.
          </p>
        </motion.div>

        {/* Key Metrics Row */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          <MetricCard
            label={mockMetrics.totalSpend.label}
            value={mockMetrics.totalSpend.value}
            previousValue={mockMetrics.totalSpend.previousValue}
            currency={true}
            trend="up"
            sparklineColor="#0ea5e9"
          />
          <MetricCard
            label={mockMetrics.potentialSavings.label}
            value={mockMetrics.potentialSavings.value}
            previousValue={mockMetrics.potentialSavings.previousValue}
            currency={true}
            trend="up"
            sparklineColor="#22c55e"
          />
          <MetricCard
            label={mockMetrics.activeModels.label}
            value={mockMetrics.activeModels.value}
            previousValue={mockMetrics.activeModels.previousValue}
            currency={false}
            trend="up"
            sparklineColor="#f59e0b"
          />
          <MetricCard
            label={mockMetrics.apiCalls.label}
            value={mockMetrics.apiCalls.value}
            previousValue={mockMetrics.apiCalls.previousValue}
            currency={false}
            trend="up"
            sparklineColor="#8b5cf6"
          />
        </motion.div>

        {/* Spend Over Time Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <GlassPanel>
            <h2 className="text-lg font-semibold text-white mb-4">
              Spend Over Time
            </h2>
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={mockSpendOverTimeData}>
                <ChartDefs />
                <CartesianGrid
                  strokeDasharray="4"
                  stroke="rgba(255,255,255,0.05)"
                />
                <XAxis
                  dataKey="date"
                  stroke="rgba(255,255,255,0.3)"
                  style={{ fontSize: 12 }}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.3)"
                  style={{ fontSize: 12 }}
                  label={{ value: "$", angle: -90, position: "insideLeft" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(9,9,11,0.95)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    padding: "12px",
                  }}
                  formatter={(value) => `$${value.toLocaleString()}`}
                  labelStyle={{ color: "#fafafa" }}
                />
                <Legend
                  wrapperStyle={{ paddingTop: "20px" }}
                  textStyle={{ color: "#a1a1aa" }}
                />
                <Area
                  type="monotone"
                  dataKey="spend"
                  stroke="#0ea5e9"
                  strokeWidth={2}
                  fill="url(#spendGradient)"
                  name="Actual Spend"
                  isAnimationActive={true}
                  animationDuration={1200}
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="projected"
                  stroke="#a1a1aa"
                  strokeWidth={1}
                  strokeDasharray="4"
                  fill="none"
                  name="Projected"
                  isAnimationActive={true}
                  animationDuration={1200}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </GlassPanel>
        </motion.div>

        {/* Bottom Row: Task Breakdown + Recommendations */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {/* Top Spend by Task */}
          <GlassPanel>
            <h2 className="text-lg font-semibold text-white mb-4">
              Spend by Task Type
            </h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={mockTopSpendByTask}
                margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
              >
                <ChartDefs />
                <CartesianGrid
                  strokeDasharray="4"
                  stroke="rgba(255,255,255,0.05)"
                  vertical={false}
                />
                <XAxis
                  dataKey="task"
                  stroke="rgba(255,255,255,0.3)"
                  style={{ fontSize: 11 }}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.3)"
                  style={{ fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(9,9,11,0.95)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    padding: "12px",
                  }}
                  formatter={(value) => `$${value.toLocaleString()}`}
                  labelStyle={{ color: "#fafafa" }}
                />
                <Bar
                  dataKey="spend"
                  fill="#22c55e"
                  isAnimationActive={true}
                  animationDuration={1000}
                  radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </GlassPanel>

          {/* Recommendations List */}
          <GlassPanel>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp size={20} className="text-green-500" />
              Active Swap Recommendations
            </h2>
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {mockRecommendations.map((rec, idx) => (
                <motion.div
                  key={rec.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * (idx + 1), duration: 0.4 }}
                  className="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/8 transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {rec.from} → {rec.to}
                      </p>
                      <p className="text-xs text-gray-500">{rec.taskType}</p>
                    </div>
                    <div
                      className="px-2 py-1 rounded-full text-xs font-bold bg-green-500/20
                      text-green-400 border border-green-500/50"
                    >
                      {rec.confidence}% confidence
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">
                      Potential savings
                    </span>
                    <span className="text-base font-bold text-green-400">
                      ${rec.monthlySavings.toLocaleString()}/mo
                    </span>
                  </div>
                  <div className="mt-2 pt-2 border-t border-white/10">
                    <p className="text-xs text-gray-500">
                      Volume: {rec.taskVolume.toLocaleString()} calls/month
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassPanel>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}

export default DashboardHome;
