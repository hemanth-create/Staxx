"""
Staxx Intelligence — Recommendations API Router

Endpoints:
  GET  /api/v1/recommendations            — Active swap cards grouped by task type
  GET  /api/v1/roi/projection             — 12-month ROI projection
  GET  /api/v1/roi/waterfall              — Waterfall chart data
  POST /api/v1/recommendations/{id}/approve  — Mark a swap as approved
  POST /api/v1/recommendations/{id}/dismiss  — Dismiss a recommendation
  GET  /api/v1/alerts                     — Active drift/opportunity alerts
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from recommendations.api.schemas import (
    ActionResponse,
    AlertsResponse,
    ApproveRequest,
    DismissRequest,
    ROIProjectionOut,
    RecommendationsResponse,
    SwapCardOut,
    WaterfallOut,
)
from recommendations.db.queries import (
    dismiss_swap_card,
    approve_swap_card,
    fetch_active_alerts,
    fetch_approved_cards,
    fetch_scoring_results_for_org,
    persist_swap_cards,
    fetch_card_by_id,
    fetch_org_monthly_cost,
)
from recommendations.generator import RecommendationGenerator, RiskTolerance
from recommendations.roi_engine import ROIEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
roi_router = APIRouter(prefix="/roi", tags=["roi"])
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


# ---------------------------------------------------------------------------
# GET /recommendations
# ---------------------------------------------------------------------------


@router.get("", response_model=RecommendationsResponse)
async def get_recommendations(
    org_id: str = Query(..., description="Organisation UUID"),
    risk_tolerance: RiskTolerance = Query(
        "moderate",
        description="conservative | moderate | aggressive",
    ),
    refresh: bool = Query(
        False,
        description="If true, re-score from latest scoring results instead of cache.",
    ),
    db: AsyncSession = Depends(get_db),
) -> RecommendationsResponse:
    """
    Return all active swap recommendation cards for the given org,
    grouped by task_type.

    Uses cached DB records by default. Pass `?refresh=true` to re-generate
    from the latest scoring results (slower but always fresh).
    """
    if refresh:
        scoring_results = await fetch_scoring_results_for_org(db, org_id)
        if not scoring_results:
            return RecommendationsResponse(
                org_id=org_id,
                risk_tolerance=risk_tolerance,
                total_cards=0,
                total_monthly_savings_usd=0.0,
                cards_by_task={},
            )

        gen = RecommendationGenerator(risk_tolerance=risk_tolerance)
        grouped = gen.process(scoring_results)
        flat_cards = [c for cards in grouped.values() for c in cards]
        await persist_swap_cards(db, flat_cards)
    else:
        grouped_raw = await fetch_approved_cards(
            db, org_id, risk_tolerance=risk_tolerance
        )
        grouped = grouped_raw  # already keyed by task_type

    total_savings = sum(
        c.monthly_savings_usd for cards in grouped.values() for c in cards
    )
    total_cards = sum(len(v) for v in grouped.values())

    # Convert domain objects → API response objects
    cards_by_task: dict[str, list[SwapCardOut]] = {}
    for task_type, cards in grouped.items():
        cards_by_task[task_type] = [
            SwapCardOut(**c.model_dump()) for c in cards
        ]

    return RecommendationsResponse(
        org_id=org_id,
        risk_tolerance=risk_tolerance,
        total_cards=total_cards,
        total_monthly_savings_usd=round(total_savings, 2),
        cards_by_task=cards_by_task,
    )


# ---------------------------------------------------------------------------
# POST /recommendations/{id}/approve
# ---------------------------------------------------------------------------


@router.post(
    "/{recommendation_id}/approve",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_recommendation(
    recommendation_id: str,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    """
    Mark a swap recommendation as approved.

    This records the approval timestamp and sets status = 'approved'.
    The drift monitor uses this to begin continuous monitoring.
    """
    card = await fetch_card_by_id(db, recommendation_id)
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id!r} not found.",
        )

    updated = await approve_swap_card(
        db,
        recommendation_id=recommendation_id,
        approved_by=body.approved_by,
        notes=body.notes,
    )
    return ActionResponse(
        id=recommendation_id,
        status="approved",
        updated_at=updated,
    )


# ---------------------------------------------------------------------------
# POST /recommendations/{id}/dismiss
# ---------------------------------------------------------------------------


@router.post(
    "/{recommendation_id}/dismiss",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
)
async def dismiss_recommendation(
    recommendation_id: str,
    body: DismissRequest,
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    """
    Dismiss a swap recommendation.

    Dismissed cards are hidden from the default recommendations list
    and not included in ROI projections.
    """
    card = await fetch_card_by_id(db, recommendation_id)
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id!r} not found.",
        )

    updated = await dismiss_swap_card(
        db,
        recommendation_id=recommendation_id,
        dismissed_by=body.dismissed_by,
        reason=body.reason,
    )
    return ActionResponse(
        id=recommendation_id,
        status="dismissed",
        updated_at=updated,
    )


# ---------------------------------------------------------------------------
# GET /roi/projection
# ---------------------------------------------------------------------------


@roi_router.get("/projection", response_model=ROIProjectionOut)
async def get_roi_projection(
    org_id: str = Query(..., description="Organisation UUID"),
    risk_tolerance: RiskTolerance = Query("moderate"),
    staxx_subscription_usd: float = Query(
        299.0,
        description="Monthly Staxx subscription cost for break-even calculation.",
        ge=0,
    ),
    db: AsyncSession = Depends(get_db),
) -> ROIProjectionOut:
    """
    Return a 12-month ROI projection for all active (non-dismissed) swap
    recommendations, scoped to the given risk tolerance.
    """
    grouped_raw = await fetch_approved_cards(db, org_id, risk_tolerance=risk_tolerance)
    flat_cards = [c for cards in grouped_raw.values() for c in cards]

    original_monthly_cost = await fetch_org_monthly_cost(db, org_id)

    engine = ROIEngine(staxx_subscription_usd=staxx_subscription_usd)
    projection = engine.project(
        org_id=org_id,
        approved_cards=flat_cards,
        original_monthly_cost=original_monthly_cost,
    )

    return ROIProjectionOut(
        org_id=projection.org_id,
        original_monthly_cost_usd=projection.original_monthly_cost_usd,
        total_monthly_savings_usd=projection.total_monthly_savings_usd,
        annual_savings_usd=projection.annual_savings_usd,
        cost_reduction_pct=projection.cost_reduction_pct,
        projected_monthly_cost_usd=projection.projected_monthly_cost_usd,
        staxx_subscription_usd=projection.staxx_subscription_usd,
        break_even_months=projection.break_even_months,
        monthly_projections=[
            p.model_dump() for p in projection.monthly_projections
        ],
        included_card_ids=projection.included_card_ids,
    )


# ---------------------------------------------------------------------------
# GET /roi/waterfall
# ---------------------------------------------------------------------------


@roi_router.get("/waterfall", response_model=WaterfallOut)
async def get_roi_waterfall(
    org_id: str = Query(..., description="Organisation UUID"),
    risk_tolerance: RiskTolerance = Query("moderate"),
    db: AsyncSession = Depends(get_db),
) -> WaterfallOut:
    """
    Return waterfall chart data showing:
    Original spend → per-task savings → projected remaining spend.
    """
    grouped_raw = await fetch_approved_cards(db, org_id, risk_tolerance=risk_tolerance)
    flat_cards = [c for cards in grouped_raw.values() for c in cards]

    original_monthly_cost = await fetch_org_monthly_cost(db, org_id)

    engine = ROIEngine()
    projection = engine.project(
        org_id=org_id,
        approved_cards=flat_cards,
        original_monthly_cost=original_monthly_cost,
    )
    waterfall = projection.waterfall

    return WaterfallOut(
        org_id=org_id,
        segments=[s.model_dump() for s in waterfall.segments],
        total_original_usd=waterfall.total_original_usd,
        total_savings_usd=waterfall.total_savings_usd,
        projected_spend_usd=waterfall.projected_spend_usd,
    )


# ---------------------------------------------------------------------------
# GET /alerts
# ---------------------------------------------------------------------------


@alerts_router.get("", response_model=AlertsResponse)
async def get_alerts(
    org_id: str = Query(..., description="Organisation UUID"),
    alert_type: str | None = Query(
        None,
        description="Filter by type: quality_drift | cost_drift | volume_drift | new_opportunity",
    ),
    severity: str | None = Query(
        None,
        description="Filter by severity: info | warning | critical",
    ),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> AlertsResponse:
    """
    Return active drift and opportunity alerts for the given org.
    """
    alerts = await fetch_active_alerts(
        db,
        org_id=org_id,
        alert_type=alert_type,
        severity=severity,
        limit=limit,
    )

    from recommendations.api.schemas import AlertOut

    alert_outs = [
        AlertOut(
            id=str(a["id"]),
            org_id=str(a["org_id"]),
            swap_id=str(a["swap_id"]) if a.get("swap_id") else None,
            alert_type=a["alert_type"],
            severity=a["severity"],
            message=a["message"],
            metadata=a.get("metadata") or {},
            created_at=a["created_at"],
            status=a["status"],
        )
        for a in alerts
    ]

    return AlertsResponse(
        org_id=org_id,
        total_active=len(alert_outs),
        alerts=alert_outs,
    )
