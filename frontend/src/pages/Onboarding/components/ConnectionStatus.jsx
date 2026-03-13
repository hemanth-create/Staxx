/**
 * ConnectionStatus - Animated connection health indicator.
 */

import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

export function ConnectionStatus({ status = "idle", label = null }) {
  const getStatusColor = () => {
    switch (status) {
      case "connected":
        return "text-green-400";
      case "checking":
        return "text-amber-400";
      case "failed":
        return "text-red-400";
      default:
        return "text-zinc-600";
    }
  };

  const getStatusBgColor = () => {
    switch (status) {
      case "connected":
        return "bg-green-500/20 border-green-500/30";
      case "checking":
        return "bg-amber-500/20 border-amber-500/30";
      case "failed":
        return "bg-red-500/20 border-red-500/30";
      default:
        return "bg-zinc-700/30 border-zinc-600/30";
    }
  };

  const renderIcon = () => {
    switch (status) {
      case "connected":
        return <CheckCircle2 size={20} className={getStatusColor()} />;
      case "checking":
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
          >
            <Loader2 size={20} className={getStatusColor()} />
          </motion.div>
        );
      case "failed":
        return <XCircle size={20} className={getStatusColor()} />;
      default:
        return (
          <div className="w-5 h-5 rounded-full border-2 border-zinc-600 border-t-zinc-400" />
        );
    }
  };

  return (
    <div className="flex items-center gap-3 p-4 rounded-lg border" style={{ borderColor: "inherit" }}>
      <motion.div
        className={`flex-shrink-0 p-2 rounded-full border ${getStatusBgColor()}`}
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {renderIcon()}
      </motion.div>

      {label && (
        <div>
          <p className="text-sm font-medium text-white">{label}</p>
          <p className={`text-xs ${getStatusColor()}`}>
            {status === "connected" && "Connected"}
            {status === "checking" && "Checking..."}
            {status === "failed" && "Connection failed"}
            {status === "idle" && "Ready to test"}
          </p>
        </div>
      )}
    </div>
  );
}
