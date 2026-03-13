/**
 * Recharts custom theme for dark glassmorphic Staxx dashboard.
 * Colors are consistent with the design system.
 */

export const chartTheme = {
  colors: {
    background: "#09090b",
    surface: "rgba(255,255,255,0.03)",
    primary: "#0ea5e9",      // sky-500
    success: "#22c55e",       // green-500
    warning: "#f59e0b",       // amber-500
    danger: "#ef4444",        // red-500
    textPrimary: "#fafafa",
    textSecondary: "#a1a1aa",
    textMuted: "#52525b",
  },

  // Recharts ResponsiveContainer defaults
  margin: { top: 24, right: 24, left: 0, bottom: 24 },

  // Grid styling
  grid: {
    stroke: "rgba(255,255,255,0.05)",
    strokeDasharray: "4",
  },

  // Axis styling
  axis: {
    stroke: "rgba(255,255,255,0.05)",
    fill: "#a1a1aa",
    fontSize: 12,
  },

  // Tooltip styling
  tooltip: {
    contentStyle: {
      backgroundColor: "rgba(9,9,11,0.95)",
      border: "1px solid rgba(255,255,255,0.1)",
      borderRadius: "8px",
      padding: "12px",
      backdropFilter: "blur(20px)",
    },
    labelStyle: {
      color: "#fafafa",
      fontSize: 12,
      fontWeight: 500,
    },
    itemStyle: {
      color: "#fafafa",
      fontSize: 11,
    },
  },

  // Legend styling
  legend: {
    textStyle: {
      color: "#a1a1aa",
      fontSize: 12,
    },
  },
};

/**
 * Gradient definitions for chart fills.
 * Used in SVG defs within chart components.
 */
export const chartGradients = {
  primaryGradient: (id = "primaryGradient") => ({
    id,
    colors: ["rgba(14, 165, 233, 0.4)", "rgba(14, 165, 233, 0)"],
  }),
  successGradient: (id = "successGradient") => ({
    id,
    colors: ["rgba(34, 197, 94, 0.4)", "rgba(34, 197, 94, 0)"],
  }),
  warningGradient: (id = "warningGradient") => ({
    id,
    colors: ["rgba(245, 158, 11, 0.4)", "rgba(245, 158, 11, 0)"],
  }),
  dangerGradient: (id = "dangerGradient") => ({
    id,
    colors: ["rgba(239, 68, 68, 0.4)", "rgba(239, 68, 68, 0)"],
  }),
};
