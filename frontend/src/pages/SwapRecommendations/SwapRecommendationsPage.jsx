/**
 * SwapRecommendationsPage - The money page.
 * Giant savings number, premium swap cards, and waterfall chart.
 */

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { DollarSign } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { ChartSkeleton } from "../../components/LoadingSkeleton";
import { SwapCard } from "./SwapCard";
import { SavingsWaterfall } from "./SavingsWaterfall";
import { swapSummary, swapRecommendations } from "./mockData";
import { useCountUpCurrency } from "../../hooks/useCountUp";

function SwapRecommendationsPage() {
  const [loading, setLoading] = useState(true);
  const animatedSavings = useCountUpCurrency(loading ? 0 : swapSummary.totalProjectedSavings);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-8">
          <div>
            <div className="h-10 w-72 bg-white/5 rounded-lg animate-pulse mb-2" />
            <div className="h-16 w-64 bg-white/5 rounded-lg animate-pulse mb-2" />
            <div className="h-5 w-96 bg-white/5 rounded-lg animate-pulse" />
          </div>
          {[1, 2, 3].map((i) => (
            <ChartSkeleton key={i} height="h-48" />
          ))}
          <ChartSkeleton height="h-96" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-4xl font-bold text-white mb-4">Recommended Swaps</h1>

          {/* Giant savings number */}
          <div className="flex items-center gap-4 mb-3">
            <div className="p-3 rounded-xl bg-green-500/15 border border-green-500/30">
              <DollarSign size={28} className="text-green-400" />
            </div>
            <div>
              <p className="text-sm text-zinc-400">Total Projected Savings</p>
              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.5 }}
                className="text-5xl font-bold text-green-400"
              >
                {animatedSavings}
                <span className="text-2xl font-normal text-green-400/60">/mo</span>
              </motion.p>
            </div>
          </div>

          <p className="text-gray-400">
            Based on {swapSummary.totalEvaluations.toLocaleString()} shadow evaluations
            across {swapSummary.taskTypesAnalyzed} task types
          </p>
        </motion.div>

        {/* Swap Cards */}
        <div className="space-y-6">
          {[...swapRecommendations]
            .sort((a, b) => b.savings - a.savings)
            .map((rec, idx) => (
              <SwapCard
                key={rec.id}
                recommendation={rec}
                index={idx}
                onApprove={(id) => console.log("Approved:", id)}
                onDismiss={(id) => console.log("Dismissed:", id)}
                onViewDetails={(id) => console.log("View details:", id)}
              />
            ))}
        </div>

        {/* Savings Waterfall */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.5 }}
        >
          <SavingsWaterfall />
        </motion.div>
      </div>
    </DashboardLayout>
  );
}

export default SwapRecommendationsPage;
