/**
 * ExecutiveSummaryCard - Shareable executive summary with export to PDF.
 * Premium glassmorphic card with gradient border.
 */

import { useRef } from "react";
import { Printer, TrendingUp } from "lucide-react";
import { GlassPanel } from "../../components/GlassPanel";
import { roiSummary, getTopRecommendations } from "./mockData";

function ExecutiveSummaryCard() {
  const cardRef = useRef(null);
  const topRecs = getTopRecommendations(3);

  const handleExportPDF = () => {
    window.print();
  };

  return (
    <>
      {/* Print styles */}
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          #exec-summary-card,
          #exec-summary-card * {
            visibility: visible;
          }
          #exec-summary-card {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            border: none;
            box-shadow: none;
            background: white;
            color: black;
          }
          #exec-summary-card .text-white {
            color: black;
          }
          #exec-summary-card .text-zinc-400,
          #exec-summary-card .text-zinc-300,
          #exec-summary-card .text-zinc-500 {
            color: #666;
          }
          #exec-summary-card .bg-white\/3,
          #exec-summary-card .bg-white\/5,
          #exec-summary-card .bg-white\/8,
          #exec-summary-card .bg-green-500\/10,
          #exec-summary-card .glass-panel {
            background: #f5f5f5;
            border: 1px solid #ddd;
          }
          #exec-summary-card .text-green-400,
          #exec-summary-card .text-green-500 {
            color: #16a34a;
          }
          #exec-summary-card .text-sky-400 {
            color: #0284c7;
          }
          #exec-summary-card .border {
            border-color: #ddd;
          }
        }
      `}</style>

      <GlassPanel className="relative overflow-hidden">
        {/* Gradient border effect */}
        <div className="absolute inset-0 bg-gradient-to-r from-green-500/40 via-sky-500/40 to-purple-500/40 rounded-lg pointer-events-none" />
        <div className="absolute inset-1 bg-gradient-to-b from-zinc-900/80 to-zinc-950 rounded-lg pointer-events-none" />

        {/* Content */}
        <div ref={cardRef} id="exec-summary-card" className="relative p-8 space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-white/10 pb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center">
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">Executive Summary</h2>
                <p className="text-xs text-zinc-400">{roiSummary.dateRange}</p>
              </div>
            </div>

            <button
              onClick={handleExportPDF}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500/20 border border-green-500/50 text-green-400 hover:bg-green-500/30 transition-colors print:hidden"
            >
              <Printer size={16} />
              <span className="text-sm font-medium">Export PDF</span>
            </button>
          </div>

          {/* Company & Date Section */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-1">
                Organization
              </p>
              <p className="text-xl font-bold text-white">{roiSummary.company}</p>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between items-center text-zinc-400">
                  <span>Current Monthly Spend</span>
                  <span className="font-semibold text-white">
                    ${(roiSummary.currentMonthlySpend / 1000).toFixed(0)}k
                  </span>
                </div>
                <div className="flex justify-between items-center text-zinc-400">
                  <span>Staxx Subscription</span>
                  <span className="font-semibold text-white">
                    ${roiSummary.staxxSubscription}/mo
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-500/10 to-green-600/5 border border-green-500/20 rounded-lg p-4">
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-1">
                Projected Annual Savings
              </p>
              <p className="text-3xl font-bold text-green-400">
                ${(roiSummary.annualProjection / 1000).toFixed(0)}k
              </p>
              <p className="text-xs text-zinc-400 mt-2">
                Based on {roiSummary.monthlySavings} monthly savings across{" "}
                {topRecs.length} recommendations
              </p>
            </div>
          </div>

          {/* ROI Multiple - Giant Display */}
          <div className="bg-gradient-to-br from-sky-500/10 to-blue-600/5 border border-sky-500/20 rounded-lg p-6 text-center">
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">
              Return on Investment
            </p>
            <div className="flex items-end justify-center gap-1">
              <span className="text-5xl font-bold text-sky-400">{roiSummary.roiMultiple}</span>
              <span className="text-2xl text-sky-400/60 mb-1">×</span>
            </div>
            <p className="text-sm text-zinc-400 mt-2">
              For every $1 spent on Staxx, save ${roiSummary.roiMultiple.toFixed(1)}
            </p>
          </div>

          {/* Top 3 Recommendations */}
          <div>
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-3">
              Top Model Swap Opportunities
            </p>
            <div className="space-y-2">
              {topRecs.map((rec, idx) => (
                <div
                  key={rec.id}
                  className="flex items-center justify-between bg-white/3 border border-white/5 rounded-lg p-3"
                >
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-white">{rec.taskType}</p>
                    <p className="text-xs text-zinc-400">
                      {rec.currentModel} → {rec.recommended}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-green-400">
                      ${rec.monthlySavings.toLocaleString()}
                    </p>
                    <p className="text-xs text-zinc-400">{rec.confidence}% confidence</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-white/5" />

          {/* Footer */}
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <p>
              Generated by <span className="font-semibold text-zinc-400">Staxx Intelligence</span>
            </p>
            <div className="flex items-center gap-1">
              <TrendingUp size={12} className="text-green-500" />
              <span>LLM Cost Optimizer</span>
            </div>
          </div>
        </div>
      </GlassPanel>
    </>
  );
}

export default ExecutiveSummaryCard;
