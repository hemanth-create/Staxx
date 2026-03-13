/**
 * Cost Topology mock data.
 * Realistic data for a company spending ~$12,400/mo across 4 providers and 6 task types.
 */

// Task type color palette (consistent across all charts)
export const TASK_COLORS = {
  Summarization: "#0ea5e9",   // sky-500
  "Code Generation": "#8b5cf6", // violet-500
  Classification: "#22c55e",   // green-500
  "QA / Validation": "#f59e0b", // amber-500
  Extraction: "#ec4899",       // pink-500
  Translation: "#06b6d4",      // cyan-500
};

export const PROVIDER_COLORS = {
  OpenAI: "#10b981",
  Anthropic: "#d97706",
  Google: "#3b82f6",
  "AWS Bedrock": "#f97316",
};

// Section 1: Treemap data — task_type -> model hierarchy
export const treemapData = [
  {
    name: "Summarization",
    color: TASK_COLORS.Summarization,
    children: [
      { name: "GPT-4o", size: 2100, requests: 4230, provider: "OpenAI" },
      { name: "Claude Opus", size: 1400, requests: 1820, provider: "Anthropic" },
      { name: "Gemini Pro", size: 700, requests: 3100, provider: "Google" },
    ],
  },
  {
    name: "Code Generation",
    color: TASK_COLORS["Code Generation"],
    children: [
      { name: "GPT-4o", size: 1800, requests: 3600, provider: "OpenAI" },
      { name: "Claude Opus", size: 900, requests: 1100, provider: "Anthropic" },
      { name: "Claude Sonnet", size: 400, requests: 2800, provider: "Anthropic" },
    ],
  },
  {
    name: "Classification",
    color: TASK_COLORS.Classification,
    children: [
      { name: "GPT-4o", size: 1200, requests: 8400, provider: "OpenAI" },
      { name: "Claude Haiku", size: 180, requests: 12000, provider: "Anthropic" },
      { name: "Titan Lite", size: 120, requests: 9600, provider: "AWS Bedrock" },
    ],
  },
  {
    name: "QA / Validation",
    color: TASK_COLORS["QA / Validation"],
    children: [
      { name: "GPT-4 Turbo", size: 960, requests: 2400, provider: "OpenAI" },
      { name: "Claude Sonnet", size: 540, requests: 3600, provider: "Anthropic" },
      { name: "Gemini Flash", size: 300, requests: 6000, provider: "Google" },
    ],
  },
  {
    name: "Extraction",
    color: TASK_COLORS.Extraction,
    children: [
      { name: "GPT-4o", size: 480, requests: 1920, provider: "OpenAI" },
      { name: "Claude Sonnet", size: 260, requests: 1740, provider: "Anthropic" },
      { name: "Titan Express", size: 160, requests: 3200, provider: "AWS Bedrock" },
    ],
  },
  {
    name: "Translation",
    color: TASK_COLORS.Translation,
    children: [
      { name: "GPT-4 Turbo", size: 420, requests: 2100, provider: "OpenAI" },
      { name: "Gemini Pro", size: 280, requests: 2800, provider: "Google" },
      { name: "Claude Haiku", size: 100, requests: 5000, provider: "Anthropic" },
    ],
  },
];

// Total spend for reference
export const totalSpend = treemapData.reduce(
  (sum, task) => sum + task.children.reduce((s, m) => s + m.size, 0),
  0
);

// Section 2: Model utilization table
export const modelUtilizationData = [
  {
    id: 1,
    model: "GPT-4o",
    provider: "OpenAI",
    taskType: "Summarization",
    requests7d: 4230,
    avgCostPerReq: 0.0497,
    totalSpend7d: 2100,
    avgLatencyP95: 1240,
    status: "overspend",
    shadowSuggestion: "Claude Haiku at 97% quality parity",
    shadowConfidence: 94,
  },
  {
    id: 2,
    model: "GPT-4o",
    provider: "OpenAI",
    taskType: "Classification",
    requests7d: 8400,
    avgCostPerReq: 0.0143,
    totalSpend7d: 1200,
    avgLatencyP95: 890,
    status: "overspend",
    shadowSuggestion: "Claude Haiku at 99% quality parity",
    shadowConfidence: 97,
  },
  {
    id: 3,
    model: "Claude Opus",
    provider: "Anthropic",
    taskType: "Code Generation",
    requests7d: 1100,
    avgCostPerReq: 0.8182,
    totalSpend7d: 900,
    avgLatencyP95: 3200,
    status: "review",
    shadowSuggestion: "Claude Sonnet at 91% quality parity",
    shadowConfidence: 82,
  },
  {
    id: 4,
    model: "GPT-4o",
    provider: "OpenAI",
    taskType: "Code Generation",
    requests7d: 3600,
    avgCostPerReq: 0.05,
    totalSpend7d: 1800,
    avgLatencyP95: 1800,
    status: "review",
    shadowSuggestion: "Claude Sonnet at 89% quality parity",
    shadowConfidence: 78,
  },
  {
    id: 5,
    model: "Claude Sonnet",
    provider: "Anthropic",
    taskType: "QA / Validation",
    requests7d: 3600,
    avgCostPerReq: 0.015,
    totalSpend7d: 540,
    avgLatencyP95: 720,
    status: "optimal",
    shadowSuggestion: null,
    shadowConfidence: null,
  },
  {
    id: 6,
    model: "Claude Haiku",
    provider: "Anthropic",
    taskType: "Classification",
    requests7d: 12000,
    avgCostPerReq: 0.0015,
    totalSpend7d: 180,
    avgLatencyP95: 210,
    status: "optimal",
    shadowSuggestion: null,
    shadowConfidence: null,
  },
  {
    id: 7,
    model: "Gemini Pro",
    provider: "Google",
    taskType: "Summarization",
    requests7d: 3100,
    avgCostPerReq: 0.0226,
    totalSpend7d: 700,
    avgLatencyP95: 980,
    status: "optimal",
    shadowSuggestion: null,
    shadowConfidence: null,
  },
  {
    id: 8,
    model: "GPT-4 Turbo",
    provider: "OpenAI",
    taskType: "QA / Validation",
    requests7d: 2400,
    avgCostPerReq: 0.04,
    totalSpend7d: 960,
    avgLatencyP95: 1100,
    status: "review",
    shadowSuggestion: "Gemini Flash at 93% quality parity",
    shadowConfidence: 75,
  },
  {
    id: 9,
    model: "Titan Lite",
    provider: "AWS Bedrock",
    taskType: "Classification",
    requests7d: 9600,
    avgCostPerReq: 0.00125,
    totalSpend7d: 120,
    avgLatencyP95: 180,
    status: "optimal",
    shadowSuggestion: null,
    shadowConfidence: null,
  },
  {
    id: 10,
    model: "Claude Opus",
    provider: "Anthropic",
    taskType: "Summarization",
    requests7d: 1820,
    avgCostPerReq: 0.7692,
    totalSpend7d: 1400,
    avgLatencyP95: 2800,
    status: "overspend",
    shadowSuggestion: "Claude Haiku at 96% quality parity",
    shadowConfidence: 91,
  },
];

// Section 3: Cost anomaly timeline (30 days)
function generateTimeline() {
  const data = [];
  const baseDate = new Date(2025, 1, 1); // Feb 1 2025
  const baseSpend = 400;

  for (let i = 0; i < 30; i++) {
    const date = new Date(baseDate);
    date.setDate(date.getDate() + i);
    const label = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });

    // Organic daily variation
    const variation = Math.sin(i * 0.5) * 60 + Math.random() * 40;
    let spend = Math.round(baseSpend + variation + i * 3);

    let isAnomaly = false;
    let anomalyReason = null;

    // Inject anomalies on specific days
    if (i === 8) {
      spend = 780;
      isAnomaly = true;
      anomalyReason = "Spike: GPT-4o classification volume surged 3x due to batch job misconfiguration";
    }
    if (i === 19) {
      spend = 850;
      isAnomaly = true;
      anomalyReason = "Spike: New summarization pipeline deployed without model tier review";
    }
    if (i === 25) {
      spend = 720;
      isAnomaly = true;
      anomalyReason = "Spike: Retry storm on Claude Opus due to rate limit errors";
    }

    // Projected savings line (what spend would be if recommended swaps applied)
    const projectedWithSwaps = Math.round(spend * 0.38);

    data.push({
      date: label,
      spend,
      projectedWithSwaps,
      isAnomaly,
      anomalyReason,
    });
  }
  return data;
}

export const costTimelineData = generateTimeline();

// Section 4: Provider breakdown
export const providerBreakdownData = [
  { name: "OpenAI", value: 6960, color: PROVIDER_COLORS.OpenAI },
  { name: "Anthropic", value: 3780, color: PROVIDER_COLORS.Anthropic },
  { name: "Google", value: 1280, color: PROVIDER_COLORS.Google },
  { name: "AWS Bedrock", value: 380, color: PROVIDER_COLORS["AWS Bedrock"] },
];
