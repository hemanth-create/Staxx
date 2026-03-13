/**
 * ROIProjectionsPage - The "Is Staxx worth it?" page.
 * Answers customers' question with clear numbers and beautiful visualizations.
 */

import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { DollarSign, TrendingUp, Zap } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { GlassPanel } from "../../components/GlassPanel";
import { ChartSkeleton, MetricCardSkeleton } from "../../components/LoadingSkeleton";
import { useCountUpCurrency } from "../../hooks/useCountUp";
import SavingsProjectionChart from "./SavingsProjectionChart";
import SavingsBreakdownTable from "./SavingsBreakdownTable";
import WhatIfSimulator from "./WhatIfSimulator";
import ExecutiveSummaryCard from "./ExecutiveSummaryCard";
import { roiSummary, buildProjectionData } from "./mockData";

function ROIProjectionsPage() {
  const [loading, setLoading] = useState(true);
  const [implementationRate, setImplementationRate] = useState(75);

  // Build projection data based on current implementation rate
  const projectionData = useMemo(
    () => buildProjectionData(implementationRate / 100),
    [implementationRate]
  );

  // Extract key metrics from month 12 of projection
  const month12 = projectionData[11];
  const adjustedMonthlySavings = Math.round(month12.cumulativeSavings / 12);
  const adjustedAnnualSavings = month12.cumulativeSavings;
  const adjustedROIMultiple = (adjustedMonthlySavings / roiSummary.staxxSubscription).toFixed(1);

  // Animated count-up values
  const animatedMonthlySavings = useCountUpCurrency(
    loading ? 0 : adjustedMonthlySavings
  );
  const animatedAnnualSavings = useCountUpCurrency(loading ? 0 : adjustedAnnualSavings);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-8">
          {/* Hero skeleton */}
          <div>
            <div className="h-10 w-96 bg-white/5 rounded-lg animate-pulse mb-4" />
            <div className="grid grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <MetricCardSkeleton key={i} />
              ))}
            </div>
          </div>
          {/* Content skeletons */}
          {[1, 2, 3, 4].map((i) => (
            <ChartSkeleton key={i} height="h-80" />
          ))}
        </div>
      </DashboardLayout>
    );
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.2 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
  };

  return (
    <DashboardLayout>
      <motion.div
        className="space-y-8"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Hero Section */}
        <motion.div variants={itemVariants}>
          <h1 className="text-4xl font-bold text-white mb-2">Return on Investment</h1>
          <p className="text-lg text-zinc-400">
            Is Staxx Intelligence worth it? Let's prove it with your numbers.
          </p>
        </motion.div>

        {/* Metric Cards Grid */}
        <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Monthly Savings Card */}
          <GlassPanel>
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-green-500/20 border border-green-500/30">
                    <DollarSign size={20} className="text-green-400" />
                  </div>
                  <h3 className="text-sm font-medium text-zinc-400">Monthly Savings</h3>
                </div>
                <motion.p
                  key={adjustedMonthlySavings}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-3xl md:text-4xl font-bold text-green-400 font-mono"
                >
                  {animatedMonthlySavings}
                </motion.p>
              </div>
              <div className="mt-4 pt-4 border-t border-white/5">
                <p className="text-xs text-zinc-500">
                  At {implementationRate}% implementation
                </p>
              </div>
            </div>
          </GlassPanel>

          {/* Annual Projection Card */}
          <GlassPanel>
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-sky-500/20 border border-sky-500/30">
                    <TrendingUp size={20} className="text-sky-400" />
                  </div>
                  <h3 className="text-sm font-medium text-zinc-400">Annual Projection</h3>
                </div>
                <motion.p
                  key={adjustedAnnualSavings}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-3xl md:text-4xl font-bold text-sky-400 font-mono"
                >
                  {animatedAnnualSavings}
                </motion.p>
              </div>
              <div className="mt-4 pt-4 border-t border-white/5">
                <p className="text-xs text-zinc-500">
                  ±{Math.round(adjustedAnnualSavings * 0.08).toLocaleString()} CI
                </p>
              </div>
            </div>
          </GlassPanel>

          {/* ROI Multiple Card */}
          <GlassPanel>
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-purple-500/20 border border-purple-500/30">
                    <Zap size={20} className="text-purple-400" />
                  </div>
                  <h3 className="text-sm font-medium text-zinc-400">ROI Multiple</h3>
                </div>
                <div className="flex items-end gap-1">
                  <motion.p
                    key={adjustedROIMultiple}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-4xl font-bold text-purple-400 font-mono"
                  >
                    {adjustedROIMultiple}
                  </motion.p>
                  <span className="text-2xl text-purple-400/60 mb-1.5">×</span>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-white/5">
                <p className="text-xs text-zinc-500">
                  Savings to subscription ratio
                </p>
              </div>
            </div>
          </GlassPanel>
        </motion.div>

        {/* Savings Projection Chart */}
        <motion.div variants={itemVariants}>
          <SavingsProjectionChart data={projectionData} />
        </motion.div>

        {/* Savings Breakdown Table */}
        <motion.div variants={itemVariants}>
          <SavingsBreakdownTable />
        </motion.div>

        {/* What-If Simulator */}
        <motion.div variants={itemVariants}>
          <WhatIfSimulator onRateChange={setImplementationRate} />
        </motion.div>

        {/* Executive Summary Card */}
        <motion.div variants={itemVariants}>
          <ExecutiveSummaryCard />
        </motion.div>
      </motion.div>
    </DashboardLayout>
  );
}

export default ROIProjectionsPage;
