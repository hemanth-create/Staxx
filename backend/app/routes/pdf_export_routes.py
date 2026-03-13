"""PDF export endpoints for reports."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from uuid import UUID

from backend.app.core.db import get_async_session
from platform.auth.dependencies import CurrentOrg
from app.utils.pdf_export import StaxxPDFReport

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/executive-summary/pdf")
async def export_executive_summary_pdf(
    db=Depends(get_async_session),
    current_org: CurrentOrg = Depends(),
):
    """Export executive summary as PDF."""
    try:
        # Fetch org data
        org = current_org  # Already have org from dependency

        # Fetch ROI projection data
        from recommendations.db.queries import (
            get_organization_roi_projection,
            get_active_recommendations,
        )

        roi_data = await get_organization_roi_projection(db, org.id)
        swaps = await get_active_recommendations(db, org.id)

        if not roi_data:
            raise HTTPException(status_code=404, detail="No projection data available")

        # Generate PDF
        report = StaxxPDFReport(
            title="Executive Summary",
            org_name=org.name,
        )

        # Convert swaps to format needed for PDF
        top_swaps = [
            {
                "task_type": swap.task_type,
                "current_model": swap.current_model,
                "recommended_model": swap.recommended_model,
                "monthly_savings": swap.monthly_savings_usd,
                "confidence": swap.confidence_pct / 100.0,
            }
            for swap in swaps[:5]
        ]

        pdf_buffer = report.generate_executive_summary(
            current_spend=roi_data.get("current_monthly_spend", 0),
            projected_savings=roi_data.get("monthly_savings", 0),
            confidence=roi_data.get("average_confidence", 0.75),
            top_swaps=top_swaps,
            roi_multiple=roi_data.get("roi_multiple", 0),
        )

        return FileResponse(
            pdf_buffer,
            media_type="application/pdf",
            filename=f"staxx-executive-summary-{org.id}.pdf",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-analysis/pdf")
async def export_cost_analysis_pdf(
    db=Depends(get_async_session),
    current_org: CurrentOrg = Depends(),
):
    """Export cost analysis as PDF."""
    try:
        org = current_org

        # Fetch cost data
        from cost_engine.db.queries import (
            get_cost_breakdown,
            get_daily_costs,
        )

        breakdown = await get_cost_breakdown(db, org.id, period="30d")
        daily_costs = await get_daily_costs(db, org.id, days=30)

        # Parse breakdown into model and task dictionaries
        cost_by_model = {}
        cost_by_task = {}

        if breakdown:
            for item in breakdown:
                model = item.get("model", "unknown")
                task = item.get("task_type", "unknown")
                cost = item.get("cost_usd", 0)

                cost_by_model[model] = cost_by_model.get(model, 0) + cost
                cost_by_task[task] = cost_by_task.get(task, 0) + cost

        # Generate PDF
        report = StaxxPDFReport(
            title="Cost Analysis",
            org_name=org.name,
        )

        pdf_buffer = report.generate_cost_analysis(
            daily_costs=daily_costs or [],
            cost_by_model=cost_by_model,
            cost_by_task=cost_by_task,
        )

        return FileResponse(
            pdf_buffer,
            media_type="application/pdf",
            filename=f"staxx-cost-analysis-{org.id}.pdf",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
