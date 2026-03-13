"""Alert API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from backend.app.core.db import get_async_session
from platform.auth.dependencies import CurrentOrg
from alerts.api.schemas import (
    AlertResponse,
    AlertListResponse,
    AlertThresholdResponse,
    AlertThresholdUpdate,
    AlertAcknowledge,
    AlertResolve,
)
from alerts.db import queries as alert_queries

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    db=Depends(get_async_session),
    current_org: CurrentOrg = Depends(),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List active alerts for organization."""
    alerts = await alert_queries.get_active_alerts(
        db, current_org.id, alert_type=alert_type, severity=severity, limit=limit
    )

    return AlertListResponse(
        alerts=[AlertResponse.from_orm(a) for a in alerts],
        total=len(alerts),
        limit=limit,
        offset=offset,
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    db=Depends(get_async_session),
    current_org: CurrentOrg = Depends(),
):
    """Acknowledge an alert."""
    alert = await alert_queries.acknowledge_alert(db, alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.org_id != current_org.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.commit()
    return AlertResponse.from_orm(alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    db=Depends(get_async_session),
    current_org: CurrentOrg = Depends(),
):
    """Resolve an alert."""
    alert = await alert_queries.resolve_alert(db, alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.org_id != current_org.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.commit()
    return AlertResponse.from_orm(alert)


@router.get("/settings", response_model=AlertThresholdResponse)
async def get_alert_settings(
    db=Depends(get_async_session),
    current_org: CurrentOrg = Depends(),
):
    """Get alert thresholds for organization."""
    threshold = await alert_queries.get_or_create_threshold(db, current_org.id)
    return AlertThresholdResponse.from_orm(threshold)


@router.put("/settings", response_model=AlertThresholdResponse)
async def update_alert_settings(
    payload: AlertThresholdUpdate,
    db=Depends(get_async_session),
    current_org: CurrentOrg = Depends(),
):
    """Update alert thresholds for organization."""
    threshold = await alert_queries.update_threshold(
        db, current_org.id, **payload.dict(exclude_unset=True)
    )
    await db.commit()
    return AlertThresholdResponse.from_orm(threshold)


@router.get("/recent", response_model=AlertListResponse)
async def get_recent_alerts(
    db=Depends(get_async_session),
    current_org: CurrentOrg = Depends(),
    hours: int = Query(24, ge=1, le=720),
):
    """Get alerts from the last N hours."""
    alerts = await alert_queries.get_recent_alerts(db, current_org.id, hours=hours)

    return AlertListResponse(
        alerts=[AlertResponse.from_orm(a) for a in alerts],
        total=len(alerts),
        limit=len(alerts),
        offset=0,
    )
