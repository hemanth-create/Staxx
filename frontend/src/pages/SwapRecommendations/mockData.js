/**
 * Swap Recommendations mock data.
 * Realistic swap cards with metrics, confidence scores, and waterfall data.
 */

export const swapSummary = {
  totalProjectedSavings: 9420,
  totalEvaluations: 2847,
  taskTypesAnalyzed: 6,
  currentMonthlySpend: 12400,
};

export const swapRecommendations = [
  {
    id: "swap-1",
    taskType: "Summarization",
    currentModel: "GPT-4o",
    currentProvider: "OpenAI",
    currentMonthlyCost: 2100,
    recommendedModel: "Claude Haiku",
    recommendedProvider: "Anthropic",
    projectedMonthlyCost: 160,
    savings: 1940,
    confidence: 94,
    evalCount: 47,
    status: "pending", // pending, approved, dismissed
    metrics: {
      latency: { current: 1240, recommended: 310, unit: "ms", better: "lower" },
      quality: { current: 99.4, recommended: 99.2, unit: "%", better: "higher" },
      errorRate: { current: 0.4, recommended: 0.3, unit: "%", better: "lower" },
    },
  },
  {
    id: "swap-2",
    taskType: "Classification",
    currentModel: "GPT-4o",
    currentProvider: "OpenAI",
    currentMonthlyCost: 1200,
    recommendedModel: "Claude Haiku",
    recommendedProvider: "Anthropic",
    projectedMonthlyCost: 90,
    savings: 1110,
    confidence: 97,
    evalCount: 50,
    status: "pending",
    metrics: {
      latency: { current: 890, recommended: 210, unit: "ms", better: "lower" },
      quality: { current: 98.8, recommended: 99.1, unit: "%", better: "higher" },
      errorRate: { current: 0.6, recommended: 0.2, unit: "%", better: "lower" },
    },
  },
  {
    id: "swap-3",
    taskType: "Summarization",
    currentModel: "Claude Opus",
    currentProvider: "Anthropic",
    currentMonthlyCost: 1400,
    recommendedModel: "Claude Haiku",
    recommendedProvider: "Anthropic",
    projectedMonthlyCost: 108,
    savings: 1292,
    confidence: 91,
    evalCount: 42,
    status: "pending",
    metrics: {
      latency: { current: 2800, recommended: 280, unit: "ms", better: "lower" },
      quality: { current: 99.1, recommended: 97.8, unit: "%", better: "higher" },
      errorRate: { current: 0.2, recommended: 0.3, unit: "%", better: "lower" },
    },
  },
  {
    id: "swap-4",
    taskType: "Code Generation",
    currentModel: "Claude Opus",
    currentProvider: "Anthropic",
    currentMonthlyCost: 900,
    recommendedModel: "Claude Sonnet",
    recommendedProvider: "Anthropic",
    projectedMonthlyCost: 310,
    savings: 590,
    confidence: 82,
    evalCount: 35,
    status: "pending",
    metrics: {
      latency: { current: 3200, recommended: 1100, unit: "ms", better: "lower" },
      quality: { current: 96.2, recommended: 94.8, unit: "%", better: "higher" },
      errorRate: { current: 1.1, recommended: 1.4, unit: "%", better: "lower" },
    },
  },
  {
    id: "swap-5",
    taskType: "Code Generation",
    currentModel: "GPT-4o",
    currentProvider: "OpenAI",
    currentMonthlyCost: 1800,
    recommendedModel: "Claude Sonnet",
    recommendedProvider: "Anthropic",
    projectedMonthlyCost: 620,
    savings: 1180,
    confidence: 78,
    evalCount: 38,
    status: "pending",
    metrics: {
      latency: { current: 1800, recommended: 980, unit: "ms", better: "lower" },
      quality: { current: 97.1, recommended: 95.6, unit: "%", better: "higher" },
      errorRate: { current: 0.8, recommended: 1.2, unit: "%", better: "lower" },
    },
  },
  {
    id: "swap-6",
    taskType: "QA / Validation",
    currentModel: "GPT-4 Turbo",
    currentProvider: "OpenAI",
    currentMonthlyCost: 960,
    recommendedModel: "Gemini Flash",
    recommendedProvider: "Google",
    projectedMonthlyCost: 180,
    savings: 780,
    confidence: 75,
    evalCount: 28,
    status: "pending",
    metrics: {
      latency: { current: 1100, recommended: 240, unit: "ms", better: "lower" },
      quality: { current: 98.4, recommended: 97.1, unit: "%", better: "higher" },
      errorRate: { current: 0.3, recommended: 0.5, unit: "%", better: "lower" },
    },
  },
];

// Waterfall chart data derived from recommendations
export function buildWaterfallData(recs) {
  const currentTotal = swapSummary.currentMonthlySpend;
  let running = currentTotal;

  const data = [
    {
      name: "Current Spend",
      value: currentTotal,
      fill: "#ef4444",
      isTotal: true,
    },
  ];

  const sorted = [...recs]
    .filter((r) => r.status !== "dismissed")
    .sort((a, b) => b.savings - a.savings);

  sorted.forEach((rec) => {
    running -= rec.savings;
    data.push({
      name: `${rec.taskType}\n(${rec.currentModel} → ${rec.recommendedModel})`,
      shortName: rec.taskType,
      value: -rec.savings,
      runningTotal: running,
      fill: "#22c55e",
      isTotal: false,
    });
  });

  data.push({
    name: "Projected Spend",
    value: running,
    fill: "#0ea5e9",
    isTotal: true,
  });

  return data;
}
