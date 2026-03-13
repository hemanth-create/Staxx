/**
 * Mock data for Alerts page development and testing.
 */

export const mockAlerts = [
  {
    id: "alert-001",
    alert_type: "cost_anomaly",
    severity: "critical",
    title: "Cost Spike: GPT-4 Usage Surge",
    description:
      "GPT-4 spending increased to $1,245 (3.2σ above baseline of $380). Volume spike detected.",
    model: "gpt-4",
    task_type: "code_generation",
    metric_name: "daily_cost",
    created_at: new Date(Date.now() - 5 * 60000).toISOString(), // 5 min ago
    acknowledged_at: null,
    resolved_at: null,
  },
  {
    id: "alert-002",
    alert_type: "quality_drift",
    severity: "warning",
    title: "Quality Drift: Error Rate Spike",
    description:
      "Error rate increased to 8.2% on Claude 3.5 Sonnet (baseline: 2.1%). JSON validity dropped 4.3%.",
    model: "claude-3-5-sonnet",
    task_type: "summarization",
    metric_name: "error_rate",
    created_at: new Date(Date.now() - 45 * 60000).toISOString(), // 45 min ago
    acknowledged_at: new Date(Date.now() - 30 * 60000).toISOString(), // acknowledged 30 min ago
    resolved_at: null,
  },
  {
    id: "alert-003",
    alert_type: "opportunity",
    severity: "info",
    title: "New Model Available: Claude Opus 4.6",
    description:
      "Anthropic released Claude Opus 4.6 on Mar 1, 2026. Early benchmarks show 12% better performance. Consider running shadow evaluations.",
    model: "claude-opus-4-6",
    created_at: new Date(Date.now() - 8 * 3600000).toISOString(), // 8 hours ago
    acknowledged_at: null,
    resolved_at: null,
  },
  {
    id: "alert-004",
    alert_type: "cost_anomaly",
    severity: "warning",
    title: "Unusual Request Volume",
    description:
      "Request volume spiked to 15,430 requests/hour (2.1σ above 8,200 baseline). Cost per request stable.",
    metric_name: "request_volume",
    task_type: "classification",
    created_at: new Date(Date.now() - 12 * 3600000).toISOString(), // 12 hours ago
    acknowledged_at: null,
    resolved_at: new Date(Date.now() - 10 * 3600000).toISOString(), // resolved 10 hours ago
  },
  {
    id: "alert-005",
    alert_type: "opportunity",
    severity: "info",
    title: "Price Drop: GPT-4 Turbo Input Tokens",
    description:
      "OpenAI reduced GPT-4 Turbo input token price by 45% (from $0.01 to $0.0055 per 1K). Estimated monthly savings: $8,200.",
    model: "gpt-4-turbo",
    created_at: new Date(Date.now() - 24 * 3600000).toISOString(), // 1 day ago
    acknowledged_at: null,
    resolved_at: null,
  },
  {
    id: "alert-006",
    alert_type: "quality_drift",
    severity: "info",
    title: "Output Consistency Degraded",
    description:
      "Coefficient of variation increased from 0.18 to 0.31 on PII extraction task. Output is becoming less consistent.",
    model: "gpt-4-turbo",
    task_type: "pii_extraction",
    metric_name: "output_consistency",
    created_at: new Date(Date.now() - 2 * 24 * 3600000).toISOString(), // 2 days ago
    acknowledged_at: null,
    resolved_at: new Date(Date.now() - 20 * 3600000).toISOString(),
  },
  {
    id: "alert-007",
    alert_type: "cost_anomaly",
    severity: "critical",
    title: "Cost Spike: Bedrock Claude Runaway",
    description:
      "AWS Bedrock Claude spending jumped to $3,800 in 2 hours (estimated daily cost $45,600). Investigate immediately.",
    model: "bedrock-claude",
    created_at: new Date(Date.now() - 90 * 60000).toISOString(), // 90 min ago
    acknowledged_at: new Date(Date.now() - 85 * 60000).toISOString(),
    resolved_at: new Date(Date.now() - 60 * 60000).toISOString(),
  },
  {
    id: "alert-008",
    alert_type: "opportunity",
    severity: "info",
    title: "Competitive Advantage: Llama 3.1 vs GPT-4",
    description:
      "Meta's Llama 3.1 offers 15% cost savings with equivalent performance on your code_generation tasks. Consider shadow eval.",
    model: "llama-3.1",
    task_type: "code_generation",
    created_at: new Date(Date.now() - 3 * 24 * 3600000).toISOString(), // 3 days ago
    acknowledged_at: null,
    resolved_at: null,
  },
];

export const evalStats = {
  activeAlerts: 4,
  criticalAlerts: 2,
  warningAlerts: 3,
  resolvedAlerts: 3,
  qualityDriftCount: 2,
  costAnomalyCount: 3,
  opportunityCount: 3,
};
