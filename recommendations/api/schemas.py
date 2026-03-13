"""
Staxx Intelligence — Recommendation API Request/Response Schemas

All FastAPI endpoint inputs and outputs are typed through these Pydantic models.
They are separate from the internal domain models in generator.py / roi_engine.py
to allow the API contract to evolve independently.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / Embedded
# ---------------------------------------------------------------------------


class MetricsSummaryOut(BaseModel):
    sample_size: int
    cost_savings_monthly_usd: float
    cost_savings_ci_lower: float
    cost_savings_ci_upper: float
    latency_p95_ms: float
    latency_delta_pct: float
    error_rate: float
    json_validity_rate: float | None
    output_consistency_cv: float
    topsis_score: float
    is_pareto_optimal: bool


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


class SwapCardOut(BaseModel):
    """Response model for a single swap recommendation card."""

    id: str
    org_id: str
    task_type: str
    current_model: str
    recommended_model: str
    swap_recommendation: str
    confidence_pct: int
    monthly_savings_usd: float
    annual_savings_usd: float
    monthly_savings_ci_lower: float
    monthly_savings_ci_upper: float
    original_monthly_cost_usd: float
    projected_monthly_cost_usd: float
    headline: str
    rationale: str
    metrics: MetricsSummaryOut
    generated_at: datetime
    status: str


class RecommendationsResponse(BaseModel):
    """Response for GET /recommendations."""

    org_id: str
    risk_tolerance: str
    total_cards: int
    total_monthly_savings_usd: float
    cards_by_task: dict[str, list[SwapCardOut]]


# ---------------------------------------------------------------------------
# ROI Projection
# ---------------------------------------------------------------------------


class MonthlyDataPointOut(BaseModel):
    month: str
    cumulative_savings_usd: float
    cumulative_savings_lower: float
    cumulative_savings_upper: float
    remaining_cost_usd: float


class ROIProjectionOut(BaseModel):
    """Response for GET /roi/projection."""

    org_id: str
    original_monthly_cost_usd: float
    total_monthly_savings_usd: float
    annual_savings_usd: float
    cost_reduction_pct: float
    projected_monthly_cost_usd: float
    staxx_subscription_usd: float
    break_even_months: float | None
    monthly_projections: list[MonthlyDataPointOut]
    included_card_ids: list[str]


# ---------------------------------------------------------------------------
# Waterfall
# ---------------------------------------------------------------------------


class WaterfallSegmentOut(BaseModel):
    label: str
    value: float
    category: str
    task_type: str | None = None


class WaterfallOut(BaseModel):
    """Response for GET /roi/waterfall."""

    org_id: str
    segments: list[WaterfallSegmentOut]
    total_original_usd: float
    total_savings_usd: float
    projected_spend_usd: float


# ---------------------------------------------------------------------------
# Approve / Dismiss
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    """Body for POST /recommendations/{id}/approve."""

    notes: str | None = Field(None, description="Optional approval notes.")
    approved_by: str | None = Field(None, description="User who approved.")


class DismissRequest(BaseModel):
    """Body for POST /recommendations/{id}/dismiss."""

    reason: str | None = Field(None, description="Why this recommendation was dismissed.")
    dismissed_by: str | None = Field(None, description="User who dismissed.")


class ActionResponse(BaseModel):
    """Generic response for approve / dismiss actions."""

    id: str
    status: str
    updated_at: datetime


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class AlertOut(BaseModel):
    """Response model for a single drift/opportunity alert."""

    id: str
    org_id: str
    swap_id: str | None
    alert_type: str = Field(
        description="quality_drift | cost_drift | volume_drift | new_opportunity"
    )
    severity: str = Field(description="info | warning | critical")
    message: str
    metadata: dict[str, Any]
    created_at: datetime
    status: str = Field(description="active | acknowledged | resolved")


class AlertsResponse(BaseModel):
    """Response for GET /alerts."""

    org_id: str
    total_active: int
    alerts: list[AlertOut]
