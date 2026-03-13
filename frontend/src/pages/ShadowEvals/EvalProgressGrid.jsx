/**
 * EvalProgressGrid - Grid of eval progress cards, one per (task_type, original_model).
 * Shows progress bars, candidate badges, and status indicators.
 */

import { motion } from "framer-motion";
import {
  FileText,
  Code,
  Tags,
  CheckCircle,
  Database,
  Languages,
  Zap,
  Clock,
  ArrowRight,
} from "lucide-react";
import { GlassPanel } from "../../components/GlassPanel";
import { evalCards } from "./mockData";

const TASK_ICON_MAP = {
  Summarization: FileText,
  "Code Generation": Code,
  Classification: Tags,
  "QA / Validation": CheckCircle,
  Extraction: Database,
  Translation: Languages,
};

const STATUS_CONFIG = {
  collecting: {
    label: "Collecting Data",
    bg: "bg-zinc-500/15",
    text: "text-zinc-400",
    border: "border-zinc-500/30",
    icon: Clock,
  },
  analysis_ready: {
    label: "Analysis Ready",
    bg: "bg-sky-500/15",
    text: "text-sky-400",
    border: "border-sky-500/30",
    icon: Zap,
  },
  swap_available: {
    label: "Swap Available",
    bg: "bg-green-500/15",
    text: "text-green-400",
    border: "border-green-500/30",
    icon: ArrowRight,
  },
};

const N_THRESHOLD = 20;

function EvalCard({ card, onClick }) {
  const Icon = TASK_ICON_MAP[card.taskType] || FileText;
  const status = STATUS_CONFIG[card.status];
  const StatusIcon = status.icon;
  const progress = (card.runsCompleted / card.runsTarget) * 100;
  const thresholdPct = (N_THRESHOLD / card.runsTarget) * 100;
  const isClickable = card.status !== "collecting";

  return (
    <motion.div
      whileHover={isClickable ? { scale: 1.02, y: -2 } : {}}
      whileTap={isClickable ? { scale: 0.98 } : {}}
      onClick={isClickable ? () => onClick(card.id) : undefined}
      className={`relative rounded-lg backdrop-blur-md bg-white/3 border border-white/6
                  overflow-hidden transition-all ${
                    isClickable
                      ? "cursor-pointer hover:border-white/12 hover:bg-white/5"
                      : "opacity-75"
                  }`}
    >
      <div className="p-5">
        {/* Header: task type + status */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-white/5 border border-white/10">
              <Icon size={18} className="text-sky-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">{card.taskType}</p>
              <p className="text-xs text-zinc-500">{card.originalModel} &middot; {card.provider}</p>
            </div>
          </div>
          <div
            className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium
                        ${status.bg} ${status.text} border ${status.border}`}
          >
            <StatusIcon size={12} />
            {status.label}
          </div>
        </div>

        {/* Monthly cost */}
        <div className="mb-4">
          <p className="text-xs text-zinc-500">Current Monthly Cost</p>
          <p className="text-lg font-bold text-red-400">${card.monthlyCost.toLocaleString()}/mo</p>
        </div>

        {/* Progress bar */}
        <div className="mb-3">
          <div className="flex justify-between text-xs text-zinc-400 mb-1.5">
            <span>{card.runsCompleted}/{card.runsTarget} evaluations</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="relative h-2 bg-white/5 rounded-full overflow-hidden">
            {/* N>=20 threshold marker */}
            <div
              className="absolute top-0 bottom-0 w-px bg-amber-500/60 z-10"
              style={{ left: `${thresholdPct}%` }}
            />
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className={`h-full rounded-full ${
                card.runsCompleted >= N_THRESHOLD
                  ? "bg-gradient-to-r from-sky-500 to-green-500"
                  : "bg-sky-500/60"
              }`}
            />
          </div>
          {card.runsCompleted < N_THRESHOLD && (
            <p className="text-xs text-amber-400/70 mt-1">
              Need {N_THRESHOLD - card.runsCompleted} more runs for analysis (N&ge;20)
            </p>
          )}
        </div>

        {/* Candidate models */}
        <div>
          <p className="text-xs text-zinc-500 mb-2">Candidate Models</p>
          <div className="flex flex-wrap gap-1.5">
            {card.candidates.map((c) => (
              <span
                key={c.model}
                className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs
                           ${
                             c.model === card.bestCandidate
                               ? "bg-green-500/15 text-green-400 border border-green-500/30 font-medium"
                               : "bg-white/5 text-zinc-400 border border-white/10"
                           }`}
              >
                {c.model}
                {c.model === card.bestCandidate && (
                  <span className="ml-1 text-green-400">★</span>
                )}
              </span>
            ))}
          </div>
        </div>

        {/* Best candidate confidence */}
        {card.bestCandidate && card.bestCandidateConfidence && (
          <div className="mt-3 pt-3 border-t border-white/6 flex items-center justify-between">
            <span className="text-xs text-zinc-400">Best swap confidence</span>
            <span
              className={`text-sm font-bold ${
                card.bestCandidateConfidence >= 90
                  ? "text-green-400"
                  : card.bestCandidateConfidence >= 75
                  ? "text-amber-400"
                  : "text-zinc-400"
              }`}
            >
              {card.bestCandidateConfidence}%
            </span>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export function EvalProgressGrid({ onSelectEval }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {evalCards.map((card, idx) => (
        <motion.div
          key={card.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.08, duration: 0.4 }}
        >
          <EvalCard card={card} onClick={onSelectEval} />
        </motion.div>
      ))}
    </div>
  );
}
