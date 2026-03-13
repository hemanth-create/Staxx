/**
 * OutputViewer - Toggle between original and candidate model outputs
 * for individual sample prompts.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { GlassPanel } from "../../components/GlassPanel";

export function OutputViewer({ sampleOutputs, originalModel, candidateModel }) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [activeTab, setActiveTab] = useState("original");

  const sample = sampleOutputs[currentIdx];
  if (!sample) return null;

  const hasPrev = currentIdx > 0;
  const hasNext = currentIdx < sampleOutputs.length - 1;

  return (
    <GlassPanel>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white">Sample Outputs</h3>
          <p className="text-xs text-zinc-500">
            Compare actual responses side by side ({currentIdx + 1}/{sampleOutputs.length})
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setCurrentIdx((i) => i - 1)}
            disabled={!hasPrev}
            className="p-1.5 rounded-md bg-white/5 border border-white/10 text-zinc-400
                       hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            onClick={() => setCurrentIdx((i) => i + 1)}
            disabled={!hasNext}
            className="p-1.5 rounded-md bg-white/5 border border-white/10 text-zinc-400
                       hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Prompt preview */}
      <div className="rounded-lg bg-white/3 border border-white/6 p-3 mb-4">
        <p className="text-xs text-zinc-500 mb-1">Prompt</p>
        <p className="text-sm text-zinc-300 font-mono">{sample.promptPreview}</p>
      </div>

      {/* Toggle tabs */}
      <div className="flex gap-1 mb-4 p-1 rounded-lg bg-white/3">
        <button
          onClick={() => setActiveTab("original")}
          className={`flex-1 px-3 py-2 rounded-md text-xs font-medium transition-all ${
            activeTab === "original"
              ? "bg-red-500/20 text-red-400 border border-red-500/30"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          {originalModel} (Current)
        </button>
        <button
          onClick={() => setActiveTab("candidate")}
          className={`flex-1 px-3 py-2 rounded-md text-xs font-medium transition-all ${
            activeTab === "candidate"
              ? "bg-green-500/20 text-green-400 border border-green-500/30"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          {candidateModel} (Candidate)
        </button>
      </div>

      {/* Output display */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${currentIdx}-${activeTab}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          className="rounded-lg bg-zinc-900/50 border border-white/6 p-4"
        >
          <p className="text-sm text-zinc-200 leading-relaxed font-mono whitespace-pre-wrap">
            {activeTab === "original" ? sample.original : sample.candidate}
          </p>
        </motion.div>
      </AnimatePresence>
    </GlassPanel>
  );
}
