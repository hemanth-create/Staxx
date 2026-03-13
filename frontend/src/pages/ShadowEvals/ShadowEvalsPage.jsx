/**
 * ShadowEvalsPage - Main page for Shadow Evaluation Lab.
 * Shows stats bar, eval progress grid, and detail view on card click.
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FlaskConical, BarChart3, Cpu } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { GlassPanel } from "../../components/GlassPanel";
import { ChartSkeleton } from "../../components/LoadingSkeleton";
import { useCountUp } from "../../hooks/useCountUp";
import { EvalProgressGrid } from "./EvalProgressGrid";
import { EvalDetailView } from "./EvalDetailView";
import { evalStats } from "./mockData";

function EvalStatCard({ icon: Icon, label, value, color, borderColor, bgColor }) {
  const displayValue = useCountUp(value, 1.2);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <GlassPanel className={`border-l-4 ${borderColor}`}>
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-xl ${bgColor} border border-white/10 flex-shrink-0`}>
            <Icon size={32} className={color} />
          </div>
          <div>
            <p className="text-4xl font-bold text-white font-mono tracking-tight">
              {displayValue}
            </p>
            <p className="text-sm text-zinc-400 mt-1">{label}</p>
          </div>
        </div>
      </GlassPanel>
    </motion.div>
  );
}

function ShadowEvalsPage() {
  const [loading, setLoading] = useState(true);
  const [selectedEvalId, setSelectedEvalId] = useState(null);

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
            <div className="h-5 w-96 bg-white/5 rounded-lg animate-pulse" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => <ChartSkeleton key={i} height="h-28" />)}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <ChartSkeleton key={i} height="h-64" />
            ))}
          </div>
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
          <h1 className="text-4xl font-bold text-white mb-2">Shadow Evaluation Lab</h1>
          <p className="text-gray-400">
            Real production prompts. Cheaper models. Zero risk.
          </p>
        </motion.div>

        {/* Stats Bar */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <EvalStatCard
            icon={FlaskConical}
            label="evaluations completed"
            value={evalStats.totalEvaluations}
            color="text-sky-400"
            borderColor="border-sky-500"
            bgColor="bg-sky-500/10"
          />
          <EvalStatCard
            icon={BarChart3}
            label="task types analyzed"
            value={evalStats.taskTypesAnalyzed}
            color="text-green-400"
            borderColor="border-green-500"
            bgColor="bg-green-500/10"
          />
          <EvalStatCard
            icon={Cpu}
            label="models tested"
            value={evalStats.modelsTested}
            color="text-amber-400"
            borderColor="border-amber-500"
            bgColor="bg-amber-500/10"
          />
        </div>

        {/* Content: Grid or Detail View */}
        <AnimatePresence mode="wait">
          {selectedEvalId ? (
            <motion.div
              key="detail"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <EvalDetailView
                evalId={selectedEvalId}
                onBack={() => setSelectedEvalId(null)}
              />
            </motion.div>
          ) : (
            <motion.div
              key="grid"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <EvalProgressGrid onSelectEval={setSelectedEvalId} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </DashboardLayout>
  );
}

export default ShadowEvalsPage;
