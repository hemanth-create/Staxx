/**
 * SwapCard - Premium swap recommendation card. The core UI that sells the product.
 * Left: current setup (red), Center: animated arrow + savings (green), Right: recommended setup.
 * Bottom: metric comparison bars + action buttons.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Check, X, ExternalLink } from "lucide-react";
import { ConfidenceBadge } from "./ConfidenceBadge";

function MetricBar({ label, current, recommended, unit, better }) {
  const max = Math.max(current, recommended);
  const currentPct = (current / max) * 100;
  const recommendedPct = (recommended / max) * 100;

  // Determine which is better
  const currentWins =
    (better === "lower" && current < recommended) ||
    (better === "higher" && current > recommended);
  const recommendedWins = !currentWins;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="text-zinc-500">
          {current}{unit} → {recommended}{unit}
        </span>
      </div>
      <div className="flex gap-1 h-1.5">
        <div className="flex-1 bg-white/5 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${currentPct}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className={`h-full rounded-full ${currentWins ? "bg-green-500" : "bg-red-400/60"}`}
          />
        </div>
        <div className="flex-1 bg-white/5 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${recommendedPct}%` }}
            transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
            className={`h-full rounded-full ${recommendedWins ? "bg-green-500" : "bg-red-400/60"}`}
          />
        </div>
      </div>
    </div>
  );
}

export function SwapCard({ recommendation, onApprove, onDismiss, onViewDetails, index = 0 }) {
  const [cardStatus, setCardStatus] = useState(recommendation.status);
  const rec = recommendation;

  const handleApprove = () => {
    setCardStatus("approved");
    onApprove?.(rec.id);
  };

  const handleDismiss = () => {
    setCardStatus("dismissed");
    onDismiss?.(rec.id);
  };

  const isActioned = cardStatus === "approved" || cardStatus === "dismissed";

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5, type: "spring", damping: 20 }}
      layout
      className="relative group"
    >
      {/* Glow effect on hover */}
      <div className="absolute -inset-px rounded-xl bg-gradient-to-r from-sky-500/20 via-green-500/20 to-sky-500/20
                      opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-sm" />

      <div className={`relative rounded-xl backdrop-blur-md border overflow-hidden transition-all duration-300
                       ${isActioned
                         ? cardStatus === "approved"
                           ? "bg-green-500/5 border-green-500/20"
                           : "bg-white/2 border-white/4 opacity-60"
                         : "bg-white/3 border-white/8 hover:border-white/15"
                       }`}>

        {/* Main content: 3-column layout */}
        <div className="p-6">
          <div className="flex flex-col lg:flex-row items-stretch gap-4 lg:gap-0">

            {/* LEFT: Current setup */}
            <div className="flex-1 lg:pr-6">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Current</p>
              <p className="text-lg font-bold text-white">{rec.currentModel}</p>
              <p className="text-xs text-zinc-400 mb-3">{rec.currentProvider} &middot; {rec.taskType}</p>
              <p className="text-2xl font-bold text-red-400">
                ${rec.currentMonthlyCost.toLocaleString()}
                <span className="text-sm font-normal text-red-400/70">/mo</span>
              </p>
            </div>

            {/* CENTER: Arrow + savings */}
            <div className="flex lg:flex-col items-center justify-center lg:px-8 lg:border-x border-white/6 gap-3">
              <motion.div
                animate={{ x: [0, 8, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                className="p-3 rounded-full bg-green-500/15 border border-green-500/30"
              >
                <ArrowRight size={24} className="text-green-400" />
              </motion.div>
              <div className="text-center">
                <p className="text-xs text-zinc-500">Save</p>
                <motion.p
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: index * 0.1 + 0.3, type: "spring" }}
                  className="text-2xl font-bold text-green-400"
                >
                  ${rec.savings.toLocaleString()}
                </motion.p>
                <p className="text-xs text-green-400/70">/mo</p>
              </div>
            </div>

            {/* RIGHT: Recommended setup */}
            <div className="flex-1 lg:pl-6">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Recommended</p>
              <p className="text-lg font-bold text-white">{rec.recommendedModel}</p>
              <p className="text-xs text-zinc-400 mb-3">{rec.recommendedProvider} &middot; {rec.taskType}</p>
              <p className="text-2xl font-bold text-green-400">
                ${rec.projectedMonthlyCost.toLocaleString()}
                <span className="text-sm font-normal text-green-400/70">/mo</span>
              </p>
              <div className="mt-2">
                <ConfidenceBadge confidence={rec.confidence} />
              </div>
            </div>
          </div>
        </div>

        {/* Bottom section: Metrics + Actions */}
        <div className="border-t border-white/6 px-6 py-4">
          <div className="flex flex-col lg:flex-row lg:items-end gap-4">
            {/* Metrics comparison bars */}
            <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <MetricBar
                label="Latency (p95)"
                current={rec.metrics.latency.current}
                recommended={rec.metrics.latency.recommended}
                unit={rec.metrics.latency.unit}
                better={rec.metrics.latency.better}
              />
              <MetricBar
                label="Quality Score"
                current={rec.metrics.quality.current}
                recommended={rec.metrics.quality.recommended}
                unit={rec.metrics.quality.unit}
                better={rec.metrics.quality.better}
              />
              <MetricBar
                label="Error Rate"
                current={rec.metrics.errorRate.current}
                recommended={rec.metrics.errorRate.recommended}
                unit={rec.metrics.errorRate.unit}
                better={rec.metrics.errorRate.better}
              />
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 shrink-0">
              <AnimatePresence mode="wait">
                {cardStatus === "approved" ? (
                  <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-green-500/20 text-green-400 text-sm font-medium"
                  >
                    <Check size={16} />
                    Approved
                  </motion.div>
                ) : cardStatus === "dismissed" ? (
                  <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white/5 text-zinc-500 text-sm"
                  >
                    Dismissed
                  </motion.div>
                ) : (
                  <motion.div className="flex items-center gap-2" layout>
                    <button
                      onClick={handleApprove}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                                 bg-green-500 text-white hover:bg-green-600
                                 transition-colors shadow-lg shadow-green-500/25"
                    >
                      <Check size={14} />
                      Approve Swap
                    </button>
                    <button
                      onClick={handleDismiss}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm
                                 bg-white/5 text-zinc-400 border border-white/10
                                 hover:bg-white/10 hover:text-zinc-200 transition-colors"
                    >
                      <X size={14} />
                      Dismiss
                    </button>
                    <button
                      onClick={() => onViewDetails?.(rec.id)}
                      className="flex items-center gap-1 px-3 py-2 text-sm text-sky-400
                                 hover:text-sky-300 transition-colors"
                    >
                      <ExternalLink size={14} />
                      Details
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Eval count footer */}
          <p className="text-xs text-zinc-600 mt-3">
            Based on {rec.evalCount} shadow evaluations
          </p>
        </div>
      </div>
    </motion.div>
  );
}
