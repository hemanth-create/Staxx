/**
 * Shadow Evaluations mock data.
 * Realistic eval runs across task types with candidate model comparisons.
 */

export const evalStats = {
  totalEvaluations: 2847,
  taskTypesAnalyzed: 6,
  modelsTested: 9,
};

export const TASK_ICONS = {
  Summarization: "FileText",
  "Code Generation": "Code",
  Classification: "Tags",
  "QA / Validation": "CheckCircle",
  Extraction: "Database",
  Translation: "Languages",
};

export const evalCards = [
  {
    id: "eval-1",
    taskType: "Summarization",
    originalModel: "GPT-4o",
    provider: "OpenAI",
    monthlyCost: 2100,
    runsCompleted: 47,
    runsTarget: 50,
    status: "swap_available",
    candidates: [
      { model: "Claude Haiku", provider: "Anthropic" },
      { model: "Gemini Flash", provider: "Google" },
      { model: "GPT-4o-mini", provider: "OpenAI" },
    ],
    bestCandidate: "Claude Haiku",
    bestCandidateConfidence: 94,
  },
  {
    id: "eval-2",
    taskType: "Classification",
    originalModel: "GPT-4o",
    provider: "OpenAI",
    monthlyCost: 1200,
    runsCompleted: 50,
    runsTarget: 50,
    status: "swap_available",
    candidates: [
      { model: "Claude Haiku", provider: "Anthropic" },
      { model: "Titan Lite", provider: "AWS Bedrock" },
    ],
    bestCandidate: "Claude Haiku",
    bestCandidateConfidence: 97,
  },
  {
    id: "eval-3",
    taskType: "Code Generation",
    originalModel: "Claude Opus",
    provider: "Anthropic",
    monthlyCost: 900,
    runsCompleted: 35,
    runsTarget: 50,
    status: "analysis_ready",
    candidates: [
      { model: "Claude Sonnet", provider: "Anthropic" },
      { model: "GPT-4o", provider: "OpenAI" },
    ],
    bestCandidate: "Claude Sonnet",
    bestCandidateConfidence: 82,
  },
  {
    id: "eval-4",
    taskType: "QA / Validation",
    originalModel: "GPT-4 Turbo",
    provider: "OpenAI",
    monthlyCost: 960,
    runsCompleted: 28,
    runsTarget: 50,
    status: "analysis_ready",
    candidates: [
      { model: "Gemini Flash", provider: "Google" },
      { model: "Claude Sonnet", provider: "Anthropic" },
    ],
    bestCandidate: "Gemini Flash",
    bestCandidateConfidence: 75,
  },
  {
    id: "eval-5",
    taskType: "Extraction",
    originalModel: "GPT-4o",
    provider: "OpenAI",
    monthlyCost: 480,
    runsCompleted: 14,
    runsTarget: 50,
    status: "collecting",
    candidates: [
      { model: "Claude Haiku", provider: "Anthropic" },
      { model: "GPT-4o-mini", provider: "OpenAI" },
    ],
    bestCandidate: null,
    bestCandidateConfidence: null,
  },
  {
    id: "eval-6",
    taskType: "Translation",
    originalModel: "GPT-4 Turbo",
    provider: "OpenAI",
    monthlyCost: 420,
    runsCompleted: 8,
    runsTarget: 50,
    status: "collecting",
    candidates: [
      { model: "Gemini Pro", provider: "Google" },
      { model: "Claude Haiku", provider: "Anthropic" },
    ],
    bestCandidate: null,
    bestCandidateConfidence: null,
  },
  {
    id: "eval-7",
    taskType: "Summarization",
    originalModel: "Claude Opus",
    provider: "Anthropic",
    monthlyCost: 1400,
    runsCompleted: 42,
    runsTarget: 50,
    status: "swap_available",
    candidates: [
      { model: "Claude Haiku", provider: "Anthropic" },
      { model: "Gemini Flash", provider: "Google" },
    ],
    bestCandidate: "Claude Haiku",
    bestCandidateConfidence: 91,
  },
  {
    id: "eval-8",
    taskType: "Code Generation",
    originalModel: "GPT-4o",
    provider: "OpenAI",
    monthlyCost: 1800,
    runsCompleted: 38,
    runsTarget: 50,
    status: "analysis_ready",
    candidates: [
      { model: "Claude Sonnet", provider: "Anthropic" },
      { model: "GPT-4o-mini", provider: "OpenAI" },
    ],
    bestCandidate: "Claude Sonnet",
    bestCandidateConfidence: 78,
  },
];

// Detailed comparison data for EvalDetailView
export const evalDetailData = {
  "eval-1": {
    taskType: "Summarization",
    originalModel: "GPT-4o",
    bestCandidate: "Claude Haiku",
    sampleSize: 47,
    topsisScore: 0.87,
    radarMetrics: {
      original: {
        cost: 25, // inverted: lower is better, so higher score = more expensive
        latency: 60,
        quality: 95,
        errorRate: 97,
        consistency: 93,
      },
      candidate: {
        cost: 92,
        latency: 88,
        quality: 93,
        errorRate: 98,
        consistency: 91,
      },
    },
    metricsTable: [
      {
        metric: "Avg Cost / Request",
        original: "$0.0497",
        candidate: "$0.0038",
        delta: "-92.4%",
        ci: "±0.8%",
        winner: "candidate",
      },
      {
        metric: "Latency p95",
        original: "1,240ms",
        candidate: "310ms",
        delta: "-75.0%",
        ci: "±42ms",
        winner: "candidate",
      },
      {
        metric: "Schema Validity",
        original: "99.4%",
        candidate: "99.2%",
        delta: "-0.2%",
        ci: "±0.3%",
        winner: "tie",
      },
      {
        metric: "Error Rate",
        original: "0.4%",
        candidate: "0.3%",
        delta: "-0.1%",
        ci: "±0.2%",
        winner: "candidate",
      },
      {
        metric: "Output Length CV",
        original: "8.2%",
        candidate: "9.1%",
        delta: "+0.9%",
        ci: "±1.4%",
        winner: "tie",
      },
      {
        metric: "TOPSIS Score",
        original: "0.42",
        candidate: "0.87",
        delta: "+107%",
        ci: "±0.04",
        winner: "candidate",
      },
    ],
    sampleOutputs: [
      {
        id: 1,
        promptPreview: "Summarize the following quarterly earnings report from Acme Corp...",
        original:
          "Acme Corp reported Q3 revenue of $2.4B, up 12% YoY. Operating margin improved to 18.3%, driven by cost optimization in cloud infrastructure. The company raised full-year guidance to $9.8B, citing strong enterprise demand. Key risks include FX headwinds and ongoing regulatory scrutiny in the EU market.",
        candidate:
          "Acme Corp's Q3 results: Revenue $2.4B (+12% YoY), operating margin 18.3% (improved via cloud cost cuts). Full-year guidance raised to $9.8B on enterprise strength. Risks: FX headwinds, EU regulation.",
      },
      {
        id: 2,
        promptPreview: "Create a 2-sentence summary of this customer support ticket...",
        original:
          "The customer experienced intermittent login failures on the mobile app (iOS 17.2) starting March 1st, affecting their ability to access account settings. Engineering traced the root cause to an expired OAuth token refresh handler and deployed a hotfix on March 3rd.",
        candidate:
          "Customer reported intermittent mobile app login failures (iOS 17.2) since March 1st, blocking account settings access. Root cause was an expired OAuth token refresh handler; hotfix deployed March 3rd.",
      },
      {
        id: 3,
        promptPreview: "Summarize the key points from this product requirements document...",
        original:
          "The PRD outlines a new real-time collaboration feature for the document editor. Key requirements include: WebSocket-based presence indicators, conflict-free replicated data types (CRDTs) for concurrent editing, cursor position broadcasting with <100ms latency, and offline editing with automatic merge on reconnection. Target launch is Q2 2025.",
        candidate:
          "PRD describes a real-time collaboration feature for the doc editor. Requirements: WebSocket presence, CRDT-based concurrent editing, <100ms cursor broadcasting, offline editing with auto-merge. Launch target: Q2 2025.",
      },
    ],
    bootstrapCI: {
      lower: 0.83,
      upper: 0.91,
      mean: 0.87,
      samples: 1000,
    },
  },
};

// Generate detail data for all eval cards that have analysis
export function getEvalDetail(evalId) {
  if (evalDetailData[evalId]) return evalDetailData[evalId];

  // Generate synthetic detail for other cards
  const card = evalCards.find((c) => c.id === evalId);
  if (!card || card.status === "collecting") return null;

  const quality = 85 + Math.random() * 12;
  return {
    taskType: card.taskType,
    originalModel: card.originalModel,
    bestCandidate: card.bestCandidate,
    sampleSize: card.runsCompleted,
    topsisScore: (card.bestCandidateConfidence / 100) * 0.95,
    radarMetrics: {
      original: {
        cost: 20 + Math.random() * 20,
        latency: 50 + Math.random() * 30,
        quality,
        errorRate: 90 + Math.random() * 8,
        consistency: 85 + Math.random() * 10,
      },
      candidate: {
        cost: 75 + Math.random() * 20,
        latency: 75 + Math.random() * 20,
        quality: quality - 1 - Math.random() * 3,
        errorRate: 92 + Math.random() * 7,
        consistency: 83 + Math.random() * 12,
      },
    },
    metricsTable: [
      {
        metric: "Avg Cost / Request",
        original: `$${(0.03 + Math.random() * 0.05).toFixed(4)}`,
        candidate: `$${(0.002 + Math.random() * 0.008).toFixed(4)}`,
        delta: `-${(70 + Math.random() * 25).toFixed(1)}%`,
        ci: `±${(0.5 + Math.random() * 1.5).toFixed(1)}%`,
        winner: "candidate",
      },
      {
        metric: "Latency p95",
        original: `${Math.round(800 + Math.random() * 1500)}ms`,
        candidate: `${Math.round(150 + Math.random() * 400)}ms`,
        delta: `-${(50 + Math.random() * 35).toFixed(1)}%`,
        ci: `±${Math.round(20 + Math.random() * 60)}ms`,
        winner: "candidate",
      },
      {
        metric: "Schema Validity",
        original: `${(98 + Math.random() * 1.5).toFixed(1)}%`,
        candidate: `${(97.5 + Math.random() * 2).toFixed(1)}%`,
        delta: `${(-0.5 + Math.random()).toFixed(1)}%`,
        ci: "±0.4%",
        winner: "tie",
      },
      {
        metric: "Error Rate",
        original: `${(0.2 + Math.random() * 0.6).toFixed(1)}%`,
        candidate: `${(0.1 + Math.random() * 0.5).toFixed(1)}%`,
        delta: `${(-0.3 + Math.random() * 0.2).toFixed(1)}%`,
        ci: "±0.2%",
        winner: "candidate",
      },
    ],
    sampleOutputs: [
      {
        id: 1,
        promptPreview: `Sample ${card.taskType.toLowerCase()} prompt for ${card.originalModel}...`,
        original: `This is the original ${card.originalModel} output for a ${card.taskType.toLowerCase()} task. The response demonstrates the model's capabilities with detailed, comprehensive output that covers all aspects of the input prompt.`,
        candidate: `This is the ${card.bestCandidate} output for the same ${card.taskType.toLowerCase()} task. The response is more concise but captures the essential information accurately, demonstrating comparable quality at significantly lower cost.`,
      },
    ],
    bootstrapCI: {
      lower: (card.bestCandidateConfidence / 100) * 0.95 - 0.04,
      upper: (card.bestCandidateConfidence / 100) * 0.95 + 0.04,
      mean: (card.bestCandidateConfidence / 100) * 0.95,
      samples: 1000,
    },
  };
}
