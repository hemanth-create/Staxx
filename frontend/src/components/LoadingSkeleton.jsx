/**
 * LoadingSkeleton - Animated loading placeholder matching glassmorphic design.
 */

import { motion } from "framer-motion";
import { GlassPanel } from "./GlassPanel";

export function LoadingSkeleton({
  height = "h-12",
  width = "w-full",
  className = "",
}) {
  return (
    <motion.div
      className={`${height} ${width} ${className}`}
      animate={{ opacity: [0.5, 0.8, 0.5] }}
      transition={{ duration: 1.5, repeat: Infinity }}
    >
      <div className="h-full bg-white/5 rounded-lg backdrop-blur-sm" />
    </motion.div>
  );
}

export function MetricCardSkeleton() {
  return (
    <GlassPanel className="flex flex-col justify-between h-full">
      <LoadingSkeleton height="h-4" width="w-24" className="mb-4" />
      <LoadingSkeleton height="h-10" width="w-32" className="mb-4" />
      <LoadingSkeleton height="h-10" width="w-full" />
    </GlassPanel>
  );
}

export function ChartSkeleton({ height = "h-80" }) {
  return (
    <GlassPanel className={height}>
      <div className="flex flex-col justify-between h-full">
        <LoadingSkeleton height="h-6" width="w-40" className="mb-4" />
        <LoadingSkeleton height="h-full" width="w-full" />
      </div>
    </GlassPanel>
  );
}
