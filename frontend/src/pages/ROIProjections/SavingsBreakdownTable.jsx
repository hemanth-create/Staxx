/**
 * SavingsBreakdownTable - Per-task-type savings breakdown.
 * Shows current model, recommended, savings, confidence, and status.
 */

import { motion } from "framer-motion";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import { GlassPanel } from "../../components/GlassPanel";
import { taskBreakdown } from "./mockData";

function SavingsBreakdownTable() {
  // Calculate total non-dismissed savings
  const totalSavings = taskBreakdown
    .filter((task) => task.status !== "dismissed")
    .reduce((sum, task) => sum + task.monthlySavings, 0);

  const getStatusBadge = (status) => {
    switch (status) {
      case "approved":
        return {
          icon: CheckCircle2,
          label: "Approved",
          color: "text-green-400",
          bgColor: "bg-green-500/10",
        };
      case "pending":
        return {
          icon: Clock,
          label: "Pending Review",
          color: "text-amber-400",
          bgColor: "bg-amber-500/10",
        };
      case "dismissed":
        return {
          icon: XCircle,
          label: "Dismissed",
          color: "text-zinc-500",
          bgColor: "bg-zinc-500/10",
        };
      default:
        return {
          icon: Clock,
          label: "Pending",
          color: "text-zinc-400",
          bgColor: "bg-zinc-500/10",
        };
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 90) return "text-green-400";
    if (confidence >= 75) return "text-amber-400";
    return "text-orange-400";
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.05, delayChildren: 0.1 },
    },
  };

  const rowVariants = {
    hidden: { opacity: 0, x: -8 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.3 } },
  };

  return (
    <GlassPanel>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Savings Breakdown</h3>
        <p className="text-sm text-zinc-400 mt-1">
          Monthly savings potential per task type
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/5">
              <th className="text-left py-3 px-4 font-semibold text-zinc-400">
                Task Type
              </th>
              <th className="text-left py-3 px-4 font-semibold text-zinc-400">
                Current Model
              </th>
              <th className="text-left py-3 px-4 font-semibold text-zinc-400">
                Recommended
              </th>
              <th className="text-right py-3 px-4 font-semibold text-zinc-400">
                Monthly Savings
              </th>
              <th className="text-center py-3 px-4 font-semibold text-zinc-400">
                Confidence
              </th>
              <th className="text-center py-3 px-4 font-semibold text-zinc-400">
                Status
              </th>
            </tr>
          </thead>

          <motion.tbody variants={containerVariants} initial="hidden" animate="visible">
            {taskBreakdown.map((task) => {
              const statusInfo = getStatusBadge(task.status);
              const StatusIcon = statusInfo.icon;
              const confidenceColor = getConfidenceColor(task.confidence);

              return (
                <motion.tr
                  key={task.id}
                  variants={rowVariants}
                  className="border-b border-white/5 hover:bg-white/3 transition-colors duration-200"
                >
                  <td className="py-4 px-4 text-white font-medium">{task.taskType}</td>
                  <td className="py-4 px-4 text-zinc-300">{task.currentModel}</td>
                  <td className="py-4 px-4 text-zinc-300">{task.recommended}</td>
                  <td className="py-4 px-4 text-right">
                    <span className="font-semibold text-green-400">
                      ${task.monthlySavings.toLocaleString()}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-center">
                    <span className={`font-semibold ${confidenceColor}`}>
                      {task.confidence}%
                    </span>
                  </td>
                  <td className="py-4 px-4 text-center">
                    <div
                      className={`inline-flex items-center gap-2 px-2.5 py-1.5 rounded-md ${statusInfo.bgColor}`}
                    >
                      <StatusIcon size={14} className={statusInfo.color} />
                      <span className={`text-xs font-semibold ${statusInfo.color}`}>
                        {statusInfo.label}
                      </span>
                    </div>
                  </td>
                </motion.tr>
              );
            })}

            {/* Footer: Total Row */}
            <motion.tr variants={rowVariants} className="border-t-2 border-white/10">
              <td colSpan="3" className="py-4 px-4 font-bold text-white">
                Total
              </td>
              <td className="py-4 px-4 text-right">
                <span className="font-bold text-green-400 text-base">
                  ${totalSavings.toLocaleString()}
                </span>
              </td>
              <td colSpan="2" />
            </motion.tr>
          </motion.tbody>
        </table>
      </div>

      {/* Footer Info */}
      <div className="mt-4 pt-4 border-t border-white/5 text-xs text-zinc-400">
        <p>
          Showing {taskBreakdown.filter((t) => t.status !== "dismissed").length} of{" "}
          {taskBreakdown.length} recommendations (excluding dismissed items)
        </p>
      </div>
    </GlassPanel>
  );
}

export default SavingsBreakdownTable;
