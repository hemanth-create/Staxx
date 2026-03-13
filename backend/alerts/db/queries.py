"""Queries for alerts database operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc

from .models import Alert, AlertThreshold, NotificationLog, AlertSeverity, AlertType


class AlertQueries:
    """Database queries for alerts."""

    @staticmethod
    def create_alert(
        session: Session,
        org_id: str,
        alert_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        description: str,
        model: Optional[str] = None,
        task_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            id=alert_id,
            org_id=org_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            model=model,
            task_type=task_type,
            metric_name=metric_name,
            metadata_json=metadata,
        )
        session.add(alert)
        session.commit()
        return alert

    @staticmethod
    def get_alerts(
        session: Session,
        org_id: str,
        status: Optional[str] = None,  # "active", "resolved", "all"
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Alert], int]:
        """Get alerts with optional filtering."""
        query = session.query(Alert).filter(Alert.org_id == org_id)

        if status == "active":
            query = query.filter(Alert.resolved_at.is_(None))
        elif status == "resolved":
            query = query.filter(Alert.resolved_at.isnot(None))

        if severity:
            query = query.filter(Alert.severity == severity)

        if alert_type:
            query = query.filter(Alert.alert_type == alert_type)

        total = query.count()
        alerts = query.order_by(desc(Alert.created_at)).limit(limit).offset(offset).all()

        return alerts, total

    @staticmethod
    def get_alert(session: Session, alert_id: str) -> Optional[Alert]:
        """Get a specific alert."""
        return session.query(Alert).filter(Alert.id == alert_id).first()

    @staticmethod
    def acknowledge_alert(
        session: Session, alert_id: str, user_id: Optional[str] = None
    ) -> bool:
        """Mark an alert as acknowledged."""
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return False

        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user_id
        session.commit()
        return True

    @staticmethod
    def resolve_alert(
        session: Session, alert_id: str, user_id: Optional[str] = None
    ) -> bool:
        """Mark an alert as resolved."""
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return False

        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = user_id
        session.commit()
        return True

    @staticmethod
    def check_duplicate_alert(
        session: Session,
        org_id: str,
        alert_type: AlertType,
        model: Optional[str] = None,
        metric_name: Optional[str] = None,
        hours_back: int = 1,
    ) -> bool:
        """Check if a similar alert already exists (to avoid duplicates)."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours_back)

        query = session.query(Alert).filter(
            and_(
                Alert.org_id == org_id,
                Alert.alert_type == alert_type,
                Alert.resolved_at.is_(None),
                Alert.created_at >= cutoff,
            )
        )

        if model:
            query = query.filter(Alert.model == model)
        if metric_name:
            query = query.filter(Alert.metric_name == metric_name)

        return query.first() is not None


class AlertThresholdQueries:
    """Queries for alert threshold configuration."""

    @staticmethod
    def get_threshold(session: Session, org_id: str) -> Optional[AlertThreshold]:
        """Get alert threshold configuration for an org."""
        return (
            session.query(AlertThreshold)
            .filter(AlertThreshold.org_id == org_id)
            .first()
        )

    @staticmethod
    def create_threshold(session: Session, org_id: str) -> AlertThreshold:
        """Create default alert thresholds for an org."""
        import uuid

        threshold = AlertThreshold(id=str(uuid.uuid4()), org_id=org_id)
        session.add(threshold)
        session.commit()
        return threshold

    @staticmethod
    def update_threshold(
        session: Session, org_id: str, **updates
    ) -> Optional[AlertThreshold]:
        """Update alert threshold configuration."""
        threshold = (
            session.query(AlertThreshold)
            .filter(AlertThreshold.org_id == org_id)
            .first()
        )
        if not threshold:
            return None

        for key, value in updates.items():
            if hasattr(threshold, key):
                setattr(threshold, key, value)

        session.commit()
        return threshold


class NotificationLogQueries:
    """Queries for notification logs."""

    @staticmethod
    def log_notification(
        session: Session,
        notification_id: str,
        alert_id: str,
        method: str,
        destination: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> NotificationLog:
        """Log a notification attempt."""
        log = NotificationLog(
            id=notification_id,
            alert_id=alert_id,
            method=method,
            destination=destination,
            success=success,
            error_message=error_message,
        )
        session.add(log)
        session.commit()
        return log

    @staticmethod
    def get_notification_logs(
        session: Session, alert_id: str
    ) -> List[NotificationLog]:
        """Get all notification logs for an alert."""
        return (
            session.query(NotificationLog)
            .filter(NotificationLog.alert_id == alert_id)
            .order_by(desc(NotificationLog.created_at))
            .all()
        )
