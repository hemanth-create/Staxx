"""Alert management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from backend.app.db import get_db
from backend.platform.auth.dependencies import CurrentOrg
from .schemas import (
    AlertResponse,
    AlertListResponse,
    AcknowledgeAlertRequest,
    ResolveAlertRequest,
    AlertThresholdResponse,
    AlertThresholdUpdate,
)
from ..db.queries import AlertQueries, AlertThresholdQueries
from ..db.models import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse, name="list_alerts")
async def list_alerts(
    status: Optional[str] = Query(None, regex="^(active|resolved|all)$"),
    severity: Optional[str] = Query(None, regex="^(critical|warning|info)$"),
    alert_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_org: str = Depends(CurrentOrg),
    db: Session = Depends(get_db),
):
    """
    List alerts with optional filtering.

    Query parameters:
    - status: "active", "resolved", or "all" (default: all)
    - severity: "critical", "warning", or "info"
    - alert_type: "quality_drift", "cost_anomaly", or "opportunity"
    - limit: Number of results (1-100, default 50)
    - offset: Pagination offset (default 0)
    """
    alerts, total = AlertQueries.get_alerts(
        db, current_org, status=status, severity=severity, alert_type=alert_type,
        limit=limit, offset=offset
    )

    return AlertListResponse(
        alerts=[AlertResponse.from_orm(a) for a in alerts],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{alert_id}", response_model=AlertResponse, name="get_alert")
async def get_alert(
    alert_id: str,
    current_org: str = Depends(CurrentOrg),
    db: Session = Depends(get_db),
):
    """Get a specific alert by ID."""
    alert = AlertQueries.get_alert(db, alert_id)

    if not alert or alert.org_id != current_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    return AlertResponse.from_orm(alert)


@router.post("/{alert_id}/acknowledge", name="acknowledge_alert")
async def acknowledge_alert(
    alert_id: str,
    body: AcknowledgeAlertRequest,
    current_org: str = Depends(CurrentOrg),
    current_user: str = Depends(lambda: None),  # Optional user context
    db: Session = Depends(get_db),
):
    """Mark an alert as acknowledged."""
    alert = AlertQueries.get_alert(db, alert_id)

    if not alert or alert.org_id != current_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    success = AlertQueries.acknowledge_alert(db, alert_id, current_user)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to acknowledge alert")

    return {"status": "acknowledged"}


@router.post("/{alert_id}/resolve", name="resolve_alert")
async def resolve_alert(
    alert_id: str,
    body: ResolveAlertRequest,
    current_org: str = Depends(CurrentOrg),
    current_user: str = Depends(lambda: None),  # Optional user context
    db: Session = Depends(get_db),
):
    """Resolve an alert."""
    alert = AlertQueries.get_alert(db, alert_id)

    if not alert or alert.org_id != current_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    success = AlertQueries.resolve_alert(db, alert_id, current_user)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to resolve alert")

    return {"status": "resolved"}


@router.get("/settings/threshold", response_model=AlertThresholdResponse, name="get_alert_settings")
async def get_alert_settings(
    current_org: str = Depends(CurrentOrg),
    db: Session = Depends(get_db),
):
    """Get alert threshold configuration for the organization."""
    threshold = AlertThresholdQueries.get_threshold(db, current_org)

    if not threshold:
        threshold = AlertThresholdQueries.create_threshold(db, current_org)

    return AlertThresholdResponse.from_orm(threshold)


@router.put("/settings/threshold", response_model=AlertThresholdResponse, name="update_alert_settings")
async def update_alert_settings(
    updates: AlertThresholdUpdate,
    current_org: str = Depends(CurrentOrg),
    db: Session = Depends(get_db),
):
    """Update alert threshold configuration."""
    threshold = AlertThresholdQueries.get_threshold(db, current_org)

    if not threshold:
        threshold = AlertThresholdQueries.create_threshold(db, current_org)

    # Filter out None values
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}

    threshold = AlertThresholdQueries.update_threshold(db, current_org, **update_dict)

    if not threshold:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update settings")

    return AlertThresholdResponse.from_orm(threshold)
