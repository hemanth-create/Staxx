/**
 * Mock data for development and testing.
 * Replace with real API calls from platform backend.
 */

export const mockMetrics = {
  totalSpend: {
    value: 12400,
    previousValue: 11200,
    trend: "up",
    currency: true,
    label: "Total Spend (MTD)",
  },
  potentialSavings: {
    value: 9800,
    previousValue: 5200,
    trend: "up",
    currency: true,
    label: "Potential Savings",
  },
  activeModels: {
    value: 8,
    previousValue: 6,
    trend: "up",
    currency: false,
    label: "Active Models",
  },
  apiCalls: {
    value: 847500,
    previousValue: 756200,
    trend: "up",
    currency: false,
    label: "API Calls (MTD)",
  },
};

export const mockSpendOverTimeData = [
  { date: "Jan 1", spend: 350, projected: 380 },
  { date: "Jan 4", spend: 420, projected: 450 },
  { date: "Jan 7", spend: 380, projected: 410 },
  { date: "Jan 10", spend: 510, projected: 520 },
  { date: "Jan 13", spend: 480, projected: 495 },
  { date: "Jan 16", spend: 620, projected: 610 },
  { date: "Jan 19", spend: 580, projected: 590 },
  { date: "Jan 22", spend: 710, projected: 720 },
  { date: "Jan 25", spend: 690, projected: 695 },
  { date: "Jan 28", spend: 820, projected: 840 },
  { date: "Jan 31", spend: 760, projected: 780 },
];

export const mockTopSpendByTask = [
  { task: "Summarization", spend: 4200, percentage: 34 },
  { task: "Code Generation", spend: 3100, percentage: 25 },
  { task: "Classification", spend: 2400, percentage: 19 },
  { task: "QA / Validation", spend: 1800, percentage: 15 },
  { task: "Extraction", spend: 900, percentage: 7 },
];

export const mockRecommendations = [
  {
    id: 1,
    from: "Claude Opus",
    to: "Claude Haiku",
    taskType: "Summarization",
    monthlySavings: 4200,
    confidence: 94,
    taskVolume: 847,
  },
  {
    id: 2,
    from: "GPT-4o",
    to: "GPT-4 Turbo",
    taskType: "Classification",
    monthlySavings: 1800,
    confidence: 87,
    taskVolume: 5320,
  },
  {
    id: 3,
    from: "Claude Opus",
    to: "Claude Sonnet",
    taskType: "Code Generation",
    monthlySavings: 2300,
    confidence: 91,
    taskVolume: 1240,
  },
];

export const mockSparklineData = [
  { value: 65 },
  { value: 78 },
  { value: 72 },
  { value: 85 },
  { value: 92 },
  { value: 88 },
  { value: 95 },
];

/**
 * Utility to calculate trend percentage.
 */
export function calculateTrendPercent(current, previous) {
  if (!previous || previous === 0) return 0;
  return Math.round(((current - previous) / previous) * 100);
}
