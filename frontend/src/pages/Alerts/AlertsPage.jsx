import React, { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Clock, Zap } from "lucide-react";
import { motion } from "framer-motion";
import axios from "axios";
import { GlassPanel } from "../../components/GlassPanel";
import { LoadingSkeleton } from "../../components/LoadingSkeleton";
import { DashboardLayout } from "../../layouts/DashboardLayout";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [refreshing, setRefreshing] = useState(false);

  const defaultConfig = {
    color: "#9ca3af",
    bg: "bg-gray-500/10",
    border: "border-gray-500/20",
    icon: AlertCircle,
  };

  useEffect(() => {
    fetchAlerts();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [filter]);

  async function fetchAlerts() {
    try {
      setLoading(true);
      const params = {};
      if (filter !== "all" && filter !== "unacknowledged") {
        params.severity = filter;
      }

      const response = await axios.get(`${API_BASE}/alerts`, { params });
      setAlerts(response.data.alerts || []);
    } catch (error) {
      console.error("Failed to fetch alerts:", error);
    } finally {
      setLoading(false);
    }
  }

  async function acknowledgeAlert(alertId) {
    try {
      await axios.post(`${API_BASE}/alerts/${alertId}/acknowledge`);
      setRefreshing(true);
      await fetchAlerts();
      setRefreshing(false);
    } catch (error) {
      console.error("Failed to acknowledge alert:", error);
    }
  }

  async function resolveAlert(alertId) {
    try {
      await axios.post(`${API_BASE}/alerts/${alertId}/resolve`);
      setRefreshing(true);
      await fetchAlerts();
      setRefreshing(false);
    } catch (error) {
      console.error("Failed to resolve alert:", error);
    }
  }

  const filteredAlerts = alerts.filter((alert) => {
    if (filter === "unacknowledged") return !alert.acknowledged_at;
    if (filter === "all") return true;
    return alert.severity === filter;
  });

  const activeAlerts = filteredAlerts.filter((a) => !a.resolved_at);
  const resolvedAlerts = filteredAlerts.filter((a) => a.resolved_at);

  const severityConfig = {
    critical: {
      color: "#ef4444",
      bg: "bg-red-500/10",
      border: "border-red-500/20",
      icon: AlertCircle,
    },
    warning: {
      color: "#f59e0b",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
      icon: AlertCircle,
    },
    info: {
      color: "#3b82f6",
      bg: "bg-blue-500/10",
      border: "border-blue-500/20",
      icon: Clock,
    },
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Alerts</h1>
        <p className="text-gray-400">
          Monitor quality drift, cost spikes, and new opportunities
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <GlassPanel>
          <div className="text-4xl font-bold text-red-400">{activeAlerts.length}</div>
          <div className="text-sm text-gray-400 mt-2">Active Alerts</div>
        </GlassPanel>
        <GlassPanel>
          <div className="text-4xl font-bold text-red-500">
            {activeAlerts.filter((a) => a.severity === "critical").length}
          </div>
          <div className="text-sm text-gray-400 mt-2">Critical</div>
        </GlassPanel>
        <GlassPanel>
          <div className="text-4xl font-bold text-amber-500">
            {activeAlerts.filter((a) => a.severity === "warning").length}
          </div>
          <div className="text-sm text-gray-400 mt-2">Warnings</div>
        </GlassPanel>
        <GlassPanel>
          <div className="text-4xl font-bold text-blue-400">
            {resolvedAlerts.length}
          </div>
          <div className="text-sm text-gray-400 mt-2">Resolved</div>
        </GlassPanel>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-white/5">
        {["all", "critical", "warning", "info", "unacknowledged"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-3 border-b-2 transition-colors ${
              filter === f
                ? "border-sky-500 text-sky-500"
                : "border-transparent text-gray-400 hover:text-gray-300"
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Active Alerts */}
      <div className="space-y-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i}>
              <LoadingSkeleton />
            </div>
          ))
        ) : activeAlerts.length === 0 ? (
          <GlassPanel>
            <div className="text-center py-12">
              <CheckCircle className="mx-auto w-16 h-16 text-green-500/30 mb-4" />
              <p className="text-gray-400">No active alerts. Everything looks great!</p>
            </div>
          </GlassPanel>
        ) : (
          activeAlerts.map((alert, idx) => (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
            >
              <AlertCard
                alert={alert}
                config={severityConfig[alert.severity] || defaultConfig}
                onAcknowledge={() => acknowledgeAlert(alert.id)}
                onResolve={() => resolveAlert(alert.id)}
              />
            </motion.div>
          ))
        )}
      </div>

      {/* Resolved Alerts */}
      {resolvedAlerts.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-400 mt-8">RESOLVED ({resolvedAlerts.length})</h3>
          {resolvedAlerts.map((alert) => (
            <motion.div key={alert.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <AlertCard
                alert={alert}
                config={severityConfig[alert.severity] || defaultConfig}
                resolved
              />
            </motion.div>
          ))}
        </div>
      )}
      </div>
    </DashboardLayout>
  );
}

function AlertCard({ alert, config, onAcknowledge, onResolve, resolved }) {
  const Icon = config.icon;
  const created = alert.created_at ? new Date(alert.created_at) : new Date();
  const timeAgo = formatTimeAgo(created);

  return (
    <GlassPanel className={`${config.bg} border ${config.border}`}>
      <div className="flex gap-4">
        <div className="flex-shrink-0 mt-1">
          <Icon className="w-5 h-5" style={{ color: config.color }} />
        </div>

        <div className="flex-grow">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-grow">
              <h3 className="font-semibold text-white">{alert.title}</h3>
              <p className="text-sm text-gray-400 mt-1">{alert.description}</p>

              {/* Metadata */}
              <div className="flex flex-wrap gap-4 mt-3 text-xs text-gray-500">
                <div>
                  <span className="text-gray-600">Type:</span>{" "}
                  <span className="text-gray-400">{alert.alert_type}</span>
                </div>
                {alert.task_type && (
                  <div>
                    <span className="text-gray-600">Task:</span>{" "}
                    <span className="text-gray-400">{alert.task_type}</span>
                  </div>
                )}
                {alert.model && (
                  <div>
                    <span className="text-gray-600">Model:</span>{" "}
                    <span className="text-gray-400">{alert.model}</span>
                  </div>
                )}
                {alert.metric_name && (
                  <div>
                    <span className="text-gray-600">Metric:</span>{" "}
                    <span className="text-gray-400">{alert.metric_name}</span>
                  </div>
                )}
                <div>
                  <span className="text-gray-600">Created:</span>{" "}
                  <span className="text-gray-400">{timeAgo}</span>
                </div>
              </div>
            </div>

            {/* Status Badge */}
            <div className="flex-shrink-0 text-right">
              <div
                className="px-3 py-1 rounded-full text-xs font-semibold text-white"
                style={{ backgroundColor: config.color + "20", color: config.color }}
              >
                {alert.severity.toUpperCase()}
              </div>

              {/* Actions */}
              {!resolved && (
                <div className="flex gap-2 mt-3">
                  {!alert.acknowledged_at && (
                    <button
                      onClick={onAcknowledge}
                      className="px-3 py-1 text-xs bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded transition-colors"
                    >
                      Acknowledge
                    </button>
                  )}
                  <button
                    onClick={onResolve}
                    className="px-3 py-1 text-xs bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded transition-colors"
                  >
                    Resolve
                  </button>
                </div>
              )}

              {resolved && (
                <div className="mt-3 text-xs text-green-400 flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" />
                  Resolved
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </GlassPanel>
  );
}

function formatTimeAgo(date) {
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
