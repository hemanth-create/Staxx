"""
Staxx Intelligence — API Response Schemas (Pydantic v2)

Strict response models for every cost API endpoint.
These ensure consistent JSON contracts for the dashboard frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------


class ModelTaskCostBreakdown(BaseModel):
    """Single row in the cost breakdown response."""

    model: str
    task_type: str
    call_count: int
    total_cost: float = Field(..., description="Total cost in USD")
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: Optional[float] = None


class TimelineBucket(BaseModel):
    """Single time bucket in the cost timeline response."""

    bucket: str = Field(..., description="ISO-8601 timestamp of the bucket start")
    model: str
    task_type: str
    call_count: int
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: Optional[float] = None


class TopSpenderEntry(BaseModel):
    """Single entry in the top-spenders response."""

    model: str
    task_type: str
    call_count: int
    total_cost: float
    avg_cost_per_call: float
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: Optional[float] = None


# ---------------------------------------------------------------------------
# Endpoint response envelopes
# ---------------------------------------------------------------------------


class CostBreakdownResponse(BaseModel):
    """Response for GET /api/v1/costs/breakdown"""

    org_id: str
    period: str
    breakdown: list[ModelTaskCostBreakdown]
    total_cost_usd: float = Field(..., description="Sum of all breakdown rows")
    total_requests: int


class CostTimelineResponse(BaseModel):
    """Response for GET /api/v1/costs/timeline"""

    org_id: str
    period: str
    granularity: str
    data: list[TimelineBucket]


class TopSpendersResponse(BaseModel):
    """Response for GET /api/v1/costs/top-spenders"""

    org_id: str
    period: str
    limit: int
    top_spenders: list[TopSpenderEntry]


class CostSummaryResponse(BaseModel):
    """Response for GET /api/v1/costs/summary"""

    org_id: str
    total_spend_usd: float
    request_count: int
    avg_cost_per_request_usd: float
    total_input_tokens: int
    total_output_tokens: int
    current_month_start: str
    month_over_month_trend_pct: float = Field(
        ..., description="Percentage change from previous month (positive = increase)"
    )
    previous_month_spend_usd: float


# ---------------------------------------------------------------------------
# Pricing catalog models (for the optional /pricing endpoint)
# ---------------------------------------------------------------------------


class PricingEntry(BaseModel):
    """Single model pricing entry."""

    canonical_name: str
    provider: str
    input_per_1m_tokens: float
    output_per_1m_tokens: float


class PricingCatalogResponse(BaseModel):
    """Response listing all available model pricings."""

    models: list[PricingEntry]
    fallback_input_per_1m_tokens: float
    fallback_output_per_1m_tokens: float
