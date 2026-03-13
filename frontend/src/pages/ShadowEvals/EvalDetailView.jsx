/**
 * EvalDetailView - Detailed comparison when clicking into an eval card.
 * Shows radar chart, metrics table with CIs, sample outputs, and statistical details.
 */

import { motion } from "framer-motion";
import { ArrowLeft, BarChart3, Trophy } from "lucide-react";
import { GlassPanel } from "../../components/GlassPanel";
import { RadarComparison } from "./RadarComparison";
import { OutputViewer } from "./OutputViewer";
import { getEvalDetail } from "./mockData";

function MetricsTable({ metricsTable }) {
  return (
    <GlassPanel noPadding>
      <div className="p-4 pb-2">
        <h3 className="text-sm font-semibold text-white">Metrics Comparison</h3>
        <p className="text-xs text-zinc-500 mt-0.5">With bootstrap confidence intervals</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/6">
              {["Metric", "Original", "Candidate", "Delta", "CI (95%)"].map((h) => (
                <th
                  key={h}
                  className="px-4 py-2.5 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metricsTable.map((row, idx) => (
              <motion.tr
                key={row.metric}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="border-b border-white/3"
              >
                <td className="px-4 py-3 text-sm text-white font-medium">{row.metric}</td>
                <td className="px-4 py-3 text-sm text-zinc-300 font-mono">{row.original}</td>
                <td className="px-4 py-3 text-sm text-zinc-300 font-mono">{row.candidate}</td>
                <td className="px-4 py-3">
                  <span
                    className={`text-sm font-mono font-medium ${
                      row.winner === "candidate"
                        ? "text-green-400"
                        : row.winner === "original"
                        ? "text-red-400"
                        : "text-zinc-400"
                    }`}
                  >
                    {row.delta}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-zinc-500 font-mono">{row.ci}</td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassPanel>
  );
}

function BootstrapCIVisualization({ bootstrapCI }) {
  const { lower, upper, mean, samples } = bootstrapCI;
  const range = upper - lower;
  const scale = (val) => ((val - lower + range * 0.2) / (range * 1.4)) * 100;

  return (
    <GlassPanel>
      <h3 className="text-sm font-semibold text-white mb-1">Bootstrap Confidence Interval</h3>
      <p className="text-xs text-zinc-500 mb-4">{samples.toLocaleString()} bootstrap samples</p>

      <div className="relative h-12 mb-3">
        {/* CI range bar */}
        <div className="absolute top-1/2 -translate-y-1/2 h-3 bg-white/5 rounded-full w-full" />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${scale(upper) - scale(lower)}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="absolute top-1/2 -translate-y-1/2 h-3 bg-sky-500/30 rounded-full border border-sky-500/50"
          style={{ left: `${scale(lower)}%` }}
        />
        {/* Mean marker */}
        <motion.div
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 }}
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-sky-500 border-2 border-white shadow-lg"
          style={{ left: `${scale(mean)}%`, marginLeft: "-8px" }}
        />
      </div>

      <div className="flex justify-between text-xs text-zinc-400">
        <span>Lower: {lower.toFixed(2)}</span>
        <span className="text-sky-400 font-medium">Mean: {mean.toFixed(2)}</span>
        <span>Upper: {upper.toFixed(2)}</span>
      </div>
    </GlassPanel>
  );
}

function TopsisBreakdown({ topsisScore }) {
  const getGrade = (score) => {
    if (score >= 0.85) return { label: "Excellent", color: "text-green-400", bg: "bg-green-500/15" };
    if (score >= 0.7) return { label: "Good", color: "text-sky-400", bg: "bg-sky-500/15" };
    if (score >= 0.5) return { label: "Moderate", color: "text-amber-400", bg: "bg-amber-500/15" };
    return { label: "Weak", color: "text-red-400", bg: "bg-red-500/15" };
  };

  const grade = getGrade(topsisScore);

  return (
    <GlassPanel>
      <div className="flex items-center gap-3 mb-3">
        <Trophy size={18} className={grade.color} />
        <h3 className="text-sm font-semibold text-white">TOPSIS Score</h3>
      </div>
      <div className="flex items-end gap-3">
        <motion.p
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className={`text-4xl font-bold ${grade.color}`}
        >
          {topsisScore.toFixed(2)}
        </motion.p>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${grade.bg} ${grade.color} mb-1`}>
          {grade.label}
        </span>
      </div>
      <div className="mt-3 h-2 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${topsisScore * 100}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
          className="h-full rounded-full bg-gradient-to-r from-sky-500 to-green-500"
        />
      </div>
      <p className="text-xs text-zinc-500 mt-2">
        TOPSIS multi-criteria ranking score (0–1). Higher = stronger candidate.
      </p>
    </GlassPanel>
  );
}

export function EvalDetailView({ evalId, onBack }) {
  const detail = getEvalDetail(evalId);

  if (!detail) {
    return (
      <div className="space-y-6">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={16} />
          Back to evaluations
        </button>
        <GlassPanel>
          <p className="text-zinc-400 text-center py-12">
            Insufficient data. Need at least 20 evaluation runs to generate analysis.
          </p>
        </GlassPanel>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Back button + header */}
      <div>
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors mb-4"
        >
          <ArrowLeft size={16} />
          Back to evaluations
        </button>
        <div className="flex items-center gap-3">
          <BarChart3 size={24} className="text-sky-500" />
          <div>
            <h2 className="text-xl font-bold text-white">
              {detail.originalModel} vs {detail.bestCandidate}
            </h2>
            <p className="text-sm text-zinc-400">
              {detail.taskType} &middot; {detail.sampleSize} evaluation runs
            </p>
          </div>
        </div>
      </div>

      {/* Radar + TOPSIS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RadarComparison
            radarMetrics={detail.radarMetrics}
            originalModel={detail.originalModel}
            candidateModel={detail.bestCandidate}
          />
        </div>
        <div className="space-y-6">
          <TopsisBreakdown topsisScore={detail.topsisScore} />
          <BootstrapCIVisualization bootstrapCI={detail.bootstrapCI} />
        </div>
      </div>

      {/* Metrics Table */}
      <MetricsTable metricsTable={detail.metricsTable} />

      {/* Sample Outputs */}
      <OutputViewer
        sampleOutputs={detail.sampleOutputs}
        originalModel={detail.originalModel}
        candidateModel={detail.bestCandidate}
      />
    </motion.div>
  );
}
