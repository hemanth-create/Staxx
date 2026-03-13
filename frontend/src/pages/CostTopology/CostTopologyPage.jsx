/**
 * CostTopologyPage - Main layout for the Cost Topology page.
 * "Where your LLM budget goes" — the customer's aha moment.
 */

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { ChartSkeleton } from "../../components/LoadingSkeleton";
import { SpendTreemap } from "./SpendTreemap";
import { ModelUtilizationTable } from "./ModelUtilizationTable";
import { CostAnomalyTimeline } from "./CostAnomalyTimeline";
import { ProviderBreakdown } from "./ProviderBreakdown";

const stagger = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

function CostTopologyPage() {
  const [loading, setLoading] = useState(true);

  // Simulate API fetch delay
  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-8">
          {/* Hero skeleton */}
          <div>
            <div className="h-10 w-64 bg-white/5 rounded-lg animate-pulse mb-2" />
            <div className="h-5 w-80 bg-white/5 rounded-lg animate-pulse" />
          </div>
          <ChartSkeleton height="h-96" />
          <ChartSkeleton height="h-80" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartSkeleton height="h-96" />
            <ChartSkeleton height="h-96" />
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="visible"
        className="space-y-8"
      >
        {/* Hero Section */}
        <motion.div variants={fadeUp}>
          <h1 className="text-4xl font-bold text-white mb-2">Spend Topology</h1>
          <p className="text-gray-400">
            Where your LLM budget goes — drill into task types, models, and providers.
          </p>
        </motion.div>

        {/* Section 1: Spend Treemap */}
        <motion.div variants={fadeUp}>
          <SpendTreemap />
        </motion.div>

        {/* Section 2: Model Utilization Table */}
        <motion.div variants={fadeUp}>
          <ModelUtilizationTable />
        </motion.div>

        {/* Section 3 & 4: Timeline + Provider Breakdown */}
        <motion.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CostAnomalyTimeline />
          <ProviderBreakdown />
        </motion.div>
      </motion.div>
    </DashboardLayout>
  );
}

export default CostTopologyPage;
