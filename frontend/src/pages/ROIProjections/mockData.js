/**
 * ROI Projections mock data.
 * Realistic data for a company (Acme Corp) spending $25k/mo on LLM APIs.
 */

export const roiSummary = {
  company: "Acme Corp",
  dateRange: "January 2025",
  currentMonthlySpend: 25000,
  monthlySavings: 14420,
  annualProjection: 173040,
  annualCILower: 159278,  // -8%
  annualCIUpper: 186802,  // +8%
  roiMultiple: 28.9,
  staxxSubscription: 499,
  breakEvenMonth: 1,
};

export const taskBreakdown = [
  {
    id: "task-1",
    taskType: "Summarization",
    currentModel: "GPT-4o",
    recommended: "Claude Haiku",
    monthlySavings: 4800,
    confidence: 94,
    status: "approved",
  },
  {
    id: "task-2",
    taskType: "Classification",
    currentModel: "GPT-4o",
    recommended: "Claude Haiku",
    monthlySavings: 3200,
    confidence: 97,
    status: "approved",
  },
  {
    id: "task-3",
    taskType: "Code Generation",
    currentModel: "Claude Opus",
    recommended: "Claude Sonnet",
    monthlySavings: 2100,
    confidence: 82,
    status: "pending",
  },
  {
    id: "task-4",
    taskType: "Data Extraction",
    currentModel: "GPT-4 Turbo",
    recommended: "Gemini Flash",
    monthlySavings: 1900,
    confidence: 88,
    status: "pending",
  },
  {
    id: "task-5",
    taskType: "QA / Validation",
    currentModel: "GPT-4o",
    recommended: "Claude Haiku",
    monthlySavings: 1420,
    confidence: 76,
    status: "pending",
  },
  {
    id: "task-6",
    taskType: "Translation",
    currentModel: "Claude Opus",
    recommended: "Gemini Flash",
    monthlySavings: 1000,
    confidence: 71,
    status: "dismissed",
  },
];

/**
 * Build 12-month projection data based on implementation rate (0-1).
 * Assumes gradual adoption over the year, with confidence intervals.
 */
export function buildProjectionData(implementationRate = 1.0) {
  const staxxCost = roiSummary.staxxSubscription;

  // Calculate total potential savings at 100% implementation
  const totalMonthlySavings = roiSummary.monthlySavings;

  // Assume adoption curve: slow start (month 1: 40%), accelerating through year
  const adoptionCurve = [0.40, 0.50, 0.60, 0.68, 0.75, 0.81, 0.86, 0.90, 0.93, 0.95, 0.97, 1.0];

  const data = [];
  let cumulativeSavings = 0;
  let cumulativeStaxxCost = 0;

  for (let month = 1; month <= 12; month++) {
    const adoptionFactor = adoptionCurve[month - 1];
    const monthSavings = totalMonthlySavings * adoptionFactor * implementationRate;
    const ciLower = monthSavings * 0.92; // -8% CI
    const ciUpper = monthSavings * 1.08; // +8% CI

    cumulativeSavings += monthSavings;
    cumulativeStaxxCost += staxxCost;

    data.push({
      month,
      label: `M${month}`,
      expectedSavings: Math.round(monthSavings),
      cumulativeSavings: Math.round(cumulativeSavings),
      ciLower: Math.round(ciLower),
      ciUpper: Math.round(ciUpper),
      staxxCost: Math.round(cumulativeStaxxCost),
    });
  }

  return data;
}

/**
 * Top 3 recommendations by savings (for Executive Summary Card).
 */
export function getTopRecommendations(count = 3) {
  return taskBreakdown
    .filter((task) => task.status !== "dismissed")
    .sort((a, b) => b.monthlySavings - a.monthlySavings)
    .slice(0, count);
}
