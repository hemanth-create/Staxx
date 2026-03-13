/**
 * ModelUtilizationTable - Glassmorphic sortable table with status badges.
 * Row click opens a side panel with detailed metrics.
 */

import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronUp, ChevronDown, X, ArrowRight } from "lucide-react";
import { GlassPanel } from "../../components/GlassPanel";
import { modelUtilizationData } from "./mockData";

const STATUS_CONFIG = {
  optimal: {
    label: "Optimal",
    bg: "bg-green-500/15",
    text: "text-green-400",
    border: "border-green-500/30",
  },
  review: {
    label: "Review",
    bg: "bg-amber-500/15",
    text: "text-amber-400",
    border: "border-amber-500/30",
  },
  overspend: {
    label: "Overspend Detected",
    bg: "bg-red-500/15",
    text: "text-red-400",
    border: "border-red-500/30",
  },
};

const DEFAULT_STATUS_CONFIG = STATUS_CONFIG.optimal;

const COLUMNS = [
  { key: "model", label: "Model", sortable: true },
  { key: "taskType", label: "Task Type", sortable: true },
  { key: "requests7d", label: "Requests (7d)", sortable: true, numeric: true },
  { key: "avgCostPerReq", label: "Avg Cost/Req", sortable: true, numeric: true },
  { key: "totalSpend7d", label: "Total Spend (7d)", sortable: true, numeric: true },
  { key: "avgLatencyP95", label: "Avg Latency (p95)", sortable: true, numeric: true },
  { key: "status", label: "Status", sortable: true },
];

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.optimal;
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                  ${cfg.bg} ${cfg.text} border ${cfg.border}`}
    >
      {cfg.label}
    </span>
  );
}

function SortIndicator({ column, sortKey, sortDir }) {
  const isActive = sortKey === column;
  return (
    <span className="inline-flex flex-col ml-1 -space-y-1">
      <motion.span animate={{ opacity: isActive && sortDir === "asc" ? 1 : 0.3 }}>
        <ChevronUp size={12} />
      </motion.span>
      <motion.span animate={{ opacity: isActive && sortDir === "desc" ? 1 : 0.3 }}>
        <ChevronDown size={12} />
      </motion.span>
    </span>
  );
}

function DetailPanel({ row, onClose }) {
  if (!row) return null;
  const status = STATUS_CONFIG[row.status] || DEFAULT_STATUS_CONFIG;

  return (
    <motion.div
      initial={{ x: "100%", opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: "100%", opacity: 0 }}
      transition={{ type: "spring", damping: 25, stiffness: 200 }}
      className="fixed top-0 right-0 h-full w-full max-w-md z-50
                 bg-zinc-950/98 border-l border-white/10 backdrop-blur-xl
                 overflow-y-auto shadow-2xl"
    >
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xl font-bold text-white">{row.model}</h3>
            <p className="text-sm text-zinc-400">{row.provider} &middot; {row.taskType}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-white/5 border border-white/10
                       hover:bg-white/10 transition-colors text-zinc-400 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        {/* Status */}
        <div>
          <StatusBadge status={row.status} />
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-2 gap-4">
          <MetricBlock label="Requests (7d)" value={row.requests7d.toLocaleString()} />
          <MetricBlock label="Avg Cost/Request" value={`$${row.avgCostPerReq.toFixed(4)}`} />
          <MetricBlock label="Total Spend (7d)" value={`$${row.totalSpend7d.toLocaleString()}`} />
          <MetricBlock label="Latency p95" value={`${row.avgLatencyP95}ms`} />
          <MetricBlock label="Cost/1k Requests" value={`$${(row.avgCostPerReq * 1000).toFixed(2)}`} />
          <MetricBlock label="Monthly Projection" value={`$${Math.round(row.totalSpend7d * 4.3).toLocaleString()}`} />
        </div>

        {/* Shadow eval suggestion */}
        {row.shadowSuggestion && (
          <div className="rounded-lg bg-white/5 border border-white/10 p-4">
            <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <ArrowRight size={14} className={status.text} />
              Shadow Eval Recommendation
            </h4>
            <p className="text-sm text-zinc-300 mb-2">{row.shadowSuggestion}</p>
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-400">Confidence:</span>
              <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${row.shadowConfidence}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                  className={`h-full rounded-full ${
                    row.shadowConfidence >= 90 ? "bg-green-500" : "bg-amber-500"
                  }`}
                />
              </div>
              <span className="text-xs font-medium text-white">{row.shadowConfidence}%</span>
            </div>
          </div>
        )}

        {/* Projected savings */}
        {row.status === "overspend" && (
          <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-4">
            <p className="text-sm text-green-400 font-medium">
              Estimated monthly savings if swapped:
            </p>
            <p className="text-2xl font-bold text-green-400 mt-1">
              ${Math.round(row.totalSpend7d * 4.3 * 0.72).toLocaleString()}/mo
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function MetricBlock({ label, value }) {
  return (
    <div className="rounded-lg bg-white/3 border border-white/6 p-3">
      <p className="text-xs text-zinc-500 mb-1">{label}</p>
      <p className="text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

export function ModelUtilizationTable() {
  const [sortKey, setSortKey] = useState("totalSpend7d");
  const [sortDir, setSortDir] = useState("desc");
  const [selectedRow, setSelectedRow] = useState(null);

  const handleSort = useCallback(
    (key) => {
      if (sortKey === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("desc");
      }
    },
    [sortKey]
  );

  const sortedData = useMemo(() => {
    const statusOrder = { overspend: 0, review: 1, optimal: 2 };
    return [...modelUtilizationData].sort((a, b) => {
      let aVal = a[sortKey];
      let bVal = b[sortKey];
      if (sortKey === "status") {
        aVal = statusOrder[aVal] ?? 3;
        bVal = statusOrder[bVal] ?? 3;
      }
      if (typeof aVal === "string") {
        return sortDir === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      return sortDir === "asc" ? aVal - bVal : bVal - aVal;
    });
  }, [sortKey, sortDir]);

  const formatCell = (key, value) => {
    switch (key) {
      case "requests7d":
        return value.toLocaleString();
      case "avgCostPerReq":
        return `$${value.toFixed(4)}`;
      case "totalSpend7d":
        return `$${value.toLocaleString()}`;
      case "avgLatencyP95":
        return `${value}ms`;
      case "status":
        return <StatusBadge status={value} />;
      default:
        return value;
    }
  };

  return (
    <>
      <GlassPanel noPadding>
        <div className="p-6 pb-2">
          <h2 className="text-lg font-semibold text-white">Model Utilization</h2>
          <p className="text-sm text-zinc-400 mt-1">
            Click any row for detailed metrics and shadow eval results.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/6">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => col.sortable && handleSort(col.key)}
                    className={`px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider
                               ${col.sortable ? "cursor-pointer hover:text-zinc-200 select-none" : ""}
                               ${col.numeric ? "text-right" : ""}`}
                  >
                    <span className="inline-flex items-center">
                      {col.label}
                      {col.sortable && (
                        <SortIndicator column={col.key} sortKey={sortKey} sortDir={sortDir} />
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedData.map((row, idx) => (
                <motion.tr
                  key={row.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.03, duration: 0.3 }}
                  onClick={() => setSelectedRow(row)}
                  className="border-b border-white/3 hover:bg-white/5 transition-colors cursor-pointer"
                >
                  {COLUMNS.map((col) => (
                    <td
                      key={col.key}
                      className={`px-6 py-4 text-sm ${
                        col.numeric ? "text-right" : ""
                      } ${col.key === "model" ? "font-medium text-white" : "text-zinc-300"}`}
                    >
                      {formatCell(col.key, row[col.key])}
                    </td>
                  ))}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>

      {/* Side panel overlay */}
      <AnimatePresence>
        {selectedRow && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedRow(null)}
              className="fixed inset-0 bg-black/50 z-40"
            />
            <DetailPanel row={selectedRow} onClose={() => setSelectedRow(null)} />
          </>
        )}
      </AnimatePresence>
    </>
  );
}
