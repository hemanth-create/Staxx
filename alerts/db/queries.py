"""Alert database queries."""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from .models import Alert, AlertThreshold


async def create_alert(
    db: AsyncSession,
    org_id: UUID,
    alert_type: str,
    severity: str,
    title: str,
    description: str,
    task_type: Optional[str] = None,
    model: Optional[str] = None,
    metric_name: Optional[str] = None,
    current_value: Optional[float] = None,
    threshold_value: Optional[float] = None,
) -> Alert:
    """Create a new alert."""
    alert = Alert(
        org_id=org_id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        description=description,
        task_type=task_type,
        model=model,
        metric_name=metric_name,
        current_value=current_value,
        threshold_value=threshold_value,
    )
    db.add(alert)
    await db.flush()
    return alert


async def get_active_alerts(
    db: AsyncSession,
    org_id: UUID,
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> List[Alert]:
    """Get active (not resolved) alerts for an org."""
    query = select(Alert).where(
        and_(
            Alert.org_id == org_id,
            Alert.resolved_at.is_(None),
        )
    )

    if alert_type:
        query = query.where(Alert.alert_type == alert_type)

    if severity:
        query = query.where(Alert.severity == severity)

    query = query.order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def acknowledge_alert(db: AsyncSession, alert_id: UUID) -> Optional[Alert]:
    """Mark an alert as acknowledged."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if alert:
        alert.acknowledged_at = datetime.utcnow()
        await db.flush()

    return alert


async def resolve_alert(db: AsyncSession, alert_id: UUID) -> Optional[Alert]:
    """Mark an alert as resolved."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if alert:
        alert.resolved_at = datetime.utcnow()
        await db.flush()

    return alert


async def get_or_create_threshold(
    db: AsyncSession, org_id: UUID
) -> AlertThreshold:
    """Get or create alert threshold config for org."""
    result = await db.execute(
        select(AlertThreshold).where(AlertThreshold.org_id == org_id)
    )
    threshold = result.scalar_one_or_none()

    if not threshold:
        threshold = AlertThreshold(org_id=org_id)
        db.add(threshold)
        await db.flush()

    return threshold


async def update_threshold(
    db: AsyncSession,
    org_id: UUID,
    **updates,
) -> AlertThreshold:
    """Update alert thresholds for org."""
    threshold = await get_or_create_threshold(db, org_id)

    for key, value in updates.items():
        if hasattr(threshold, key) and value is not None:
            setattr(threshold, key, value)

    threshold.updated_at = datetime.utcnow()
    await db.flush()
    return threshold


async def get_recent_alerts(
    db: AsyncSession,
    org_id: UUID,
    hours: int = 24,
) -> List[Alert]:
    """Get alerts from the last N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(Alert)
        .where(
            and_(
                Alert.org_id == org_id,
                Alert.created_at >= cutoff,
            )
        )
        .order_by(desc(Alert.created_at))
    )
    return result.scalars().all()
