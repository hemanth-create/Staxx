"""
Staxx Intelligence — FastAPI Cost Router

All four required endpoints plus a bonus /pricing catalog endpoint.

Endpoints:
    GET /api/v1/costs/breakdown    — Cost breakdown by model and task type
    GET /api/v1/costs/timeline     — Time-series cost data for charts
    GET /api/v1/costs/top-spenders — Top 5 most expensive task/model combos
    GET /api/v1/costs/summary      — Total spend, request count, trends
    GET /api/v1/costs/pricing      — Current pricing catalog (debugging/admin)
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cost_engine.api.schemas import (
    CostBreakdownResponse,
    CostSummaryResponse,
    CostTimelineResponse,
    ModelTaskCostBreakdown,
    PricingCatalogResponse,
    PricingEntry,
    TimelineBucket,
    TopSpenderEntry,
    TopSpendersResponse,
)
from cost_engine.db.models import get_session
from cost_engine.db.queries import (
    query_cost_breakdown,
    query_cost_summary,
    query_cost_timeline,
    query_top_spenders,
)
from cost_engine.pricing_catalog import get_catalog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/costs", tags=["costs"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


async def _get_db() -> AsyncSession:
    """Thin wrapper that yields an async session from cost_engine's pool."""
    async for session in get_session():
        yield session


# ---------------------------------------------------------------------------
# GET /api/v1/costs/breakdown
# ---------------------------------------------------------------------------


@router.get("/breakdown", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    org_id: UUID = Query(..., description="Organisation UUID"),
    period: str = Query("7d", description="Lookback period, e.g. 7d, 30d, 90d"),
    session: AsyncSession = Depends(_get_db),
) -> CostBreakdownResponse:
    """
    Cost breakdown by model and task type for the specified period.
    """
    rows = await query_cost_breakdown(session, org_id, period)

    breakdown = [
        ModelTaskCostBreakdown(
            model=r["model"],
            task_type=r["task_type"],
            call_count=int(r["call_count"]),
            total_cost=float(r["total_cost"]),
            total_input_tokens=int(r["total_input_tokens"] or 0),
            total_output_tokens=int(r["total_output_tokens"] or 0),
            avg_latency_ms=float(r["avg_latency_ms"]) if r.get("avg_latency_ms") else None,
        )
        for r in rows
    ]

    total_cost = sum(b.total_cost for b in breakdown)
    total_requests = sum(b.call_count for b in breakdown)

    return CostBreakdownResponse(
        org_id=str(org_id),
        period=period,
        breakdown=breakdown,
        total_cost_usd=round(total_cost, 6),
        total_requests=total_requests,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/costs/timeline
# ---------------------------------------------------------------------------


@router.get("/timeline", response_model=CostTimelineResponse)
async def get_cost_timeline(
    org_id: UUID = Query(..., description="Organisation UUID"),
    granularity: str = Query("hourly", description="Bucket size: hourly, daily, weekly"),
    period: str = Query("30d", description="Lookback period, e.g. 7d, 30d"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    session: AsyncSession = Depends(_get_db),
) -> CostTimelineResponse:
    """
    Time-series cost data bucketed by the requested granularity.
    Used by the dashboard charts (Recharts).
    """
    if granularity not in ("hourly", "daily", "weekly"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid granularity '{granularity}'. Must be one of: hourly, daily, weekly",
        )

    rows = await query_cost_timeline(
        session,
        org_id,
        granularity=granularity,
        period=period,
        model_filter=model,
        task_type_filter=task_type,
    )

    data = [
        TimelineBucket(
            bucket=str(r["bucket"]),
            model=r["model"],
            task_type=r["task_type"],
            call_count=int(r["call_count"]),
            total_cost=float(r["total_cost"]),
            total_input_tokens=int(r["total_input_tokens"] or 0),
            total_output_tokens=int(r["total_output_tokens"] or 0),
            avg_latency_ms=float(r["avg_latency_ms"]) if r.get("avg_latency_ms") else None,
        )
        for r in rows
    ]

    return CostTimelineResponse(
        org_id=str(org_id),
        period=period,
        granularity=granularity,
        data=data,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/costs/top-spenders
# ---------------------------------------------------------------------------


@router.get("/top-spenders", response_model=TopSpendersResponse)
async def get_top_spenders(
    org_id: UUID = Query(..., description="Organisation UUID"),
    period: str = Query("30d", description="Lookback period"),
    limit: int = Query(5, ge=1, le=20, description="Number of results"),
    session: AsyncSession = Depends(_get_db),
) -> TopSpendersResponse:
    """
    Top N most expensive model + task_type combinations.
    """
    rows = await query_top_spenders(session, org_id, period, limit)

    top = [
        TopSpenderEntry(
            model=r["model"],
            task_type=r["task_type"],
            call_count=int(r["call_count"]),
            total_cost=float(r["total_cost"]),
            avg_cost_per_call=float(r["avg_cost_per_call"]),
            total_input_tokens=int(r["total_input_tokens"] or 0),
            total_output_tokens=int(r["total_output_tokens"] or 0),
            avg_latency_ms=float(r["avg_latency_ms"]) if r.get("avg_latency_ms") else None,
        )
        for r in rows
    ]

    return TopSpendersResponse(
        org_id=str(org_id),
        period=period,
        limit=limit,
        top_spenders=top,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/costs/summary
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    org_id: UUID = Query(..., description="Organisation UUID"),
    session: AsyncSession = Depends(_get_db),
) -> CostSummaryResponse:
    """
    High-level summary: total spend this month, request count,
    average cost per request, and month-over-month trend.
    """
    data = await query_cost_summary(session, org_id)

    return CostSummaryResponse(
        org_id=str(org_id),
        total_spend_usd=data["total_spend_usd"],
        request_count=data["request_count"],
        avg_cost_per_request_usd=data["avg_cost_per_request_usd"],
        total_input_tokens=data["total_input_tokens"],
        total_output_tokens=data["total_output_tokens"],
        current_month_start=data["current_month_start"],
        month_over_month_trend_pct=data["month_over_month_trend_pct"],
        previous_month_spend_usd=data["previous_month_spend_usd"],
    )


# ---------------------------------------------------------------------------
# GET /api/v1/costs/pricing  (bonus — useful for debugging & admin UI)
# ---------------------------------------------------------------------------


@router.get("/pricing", response_model=PricingCatalogResponse)
async def get_pricing_catalog() -> PricingCatalogResponse:
    """
    Return the current in-memory pricing catalog.
    Useful for the admin panel and verifying pricing reloads.
    """
    catalog = get_catalog()
    fallback = catalog.get_fallback()

    models = [
        PricingEntry(
            canonical_name=p.canonical_name,
            provider=p.provider,
            input_per_1m_tokens=p.input_per_1m_tokens,
            output_per_1m_tokens=p.output_per_1m_tokens,
        )
        for p in catalog.list_models()
    ]

    return PricingCatalogResponse(
        models=models,
        fallback_input_per_1m_tokens=fallback.input_per_1m_tokens,
        fallback_output_per_1m_tokens=fallback.output_per_1m_tokens,
    )
