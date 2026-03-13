/**
 * ConfidenceBadge - Color-coded confidence indicator for swap recommendations.
 * Green "STRONG YES" (>=90), Yellow "YES" (>=75), Orange "MAYBE" (<75)
 */

import { motion } from "framer-motion";
import { ShieldCheck, Shield, ShieldAlert } from "lucide-react";

const CONFIDENCE_TIERS = {
  strong: {
    label: "STRONG YES",
    bg: "bg-green-500/15",
    text: "text-green-400",
    border: "border-green-500/30",
    glow: "shadow-green-500/20",
    icon: ShieldCheck,
  },
  yes: {
    label: "YES",
    bg: "bg-amber-500/15",
    text: "text-amber-400",
    border: "border-amber-500/30",
    glow: "shadow-amber-500/20",
    icon: Shield,
  },
  maybe: {
    label: "MAYBE",
    bg: "bg-orange-500/15",
    text: "text-orange-400",
    border: "border-orange-500/30",
    glow: "shadow-orange-500/20",
    icon: ShieldAlert,
  },
};

function getTier(confidence) {
  if (confidence >= 90) return CONFIDENCE_TIERS.strong;
  if (confidence >= 75) return CONFIDENCE_TIERS.yes;
  return CONFIDENCE_TIERS.maybe;
}

export function ConfidenceBadge({ confidence, size = "default" }) {
  const tier = getTier(confidence);
  const Icon = tier.icon;

  const sizeClasses = size === "large"
    ? "px-4 py-2 text-sm gap-2"
    : "px-2.5 py-1 text-xs gap-1.5";

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={{ scale: 1.05 }}
      className={`inline-flex items-center rounded-full font-bold
                  ${tier.bg} ${tier.text} border ${tier.border} shadow-lg ${tier.glow}
                  ${sizeClasses}`}
    >
      <Icon size={size === "large" ? 16 : 13} />
      <span>{tier.label}</span>
      <span className="opacity-75">({confidence}%)</span>
    </motion.div>
  );
}
