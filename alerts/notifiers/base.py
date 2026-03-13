"""Base notifier interface."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from alerts.db.models import Alert


class BaseNotifier(ABC):
    """Abstract base notifier for alert delivery."""

    @abstractmethod
    async def send(self, alert: Alert, recipient: str) -> bool:
        """
        Send alert notification.

        Args:
            alert: Alert object to send
            recipient: Recipient address (email, Slack channel, webhook URL)

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    def format_alert(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for delivery."""
        return {
            "id": str(alert.id),
            "type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "task_type": alert.task_type,
            "model": alert.model,
            "metric_name": alert.metric_name,
            "current_value": alert.current_value,
            "threshold_value": alert.threshold_value,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }
