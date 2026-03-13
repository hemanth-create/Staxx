"""Base notifier interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseNotifier(ABC):
    """Abstract base class for all notifiers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Provider-specific configuration (API keys, URLs, etc.)
        """
        self.config = config

    @abstractmethod
    async def send(self, alert: Dict[str, Any]) -> bool:
        """
        Send an alert notification.

        Args:
            alert: Alert dictionary with title, description, severity, etc.

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    def _format_alert_message(self, alert: Dict[str, Any]) -> str:
        """Format alert into plain text message."""
        severity = alert.get("severity", "info").upper()
        title = alert.get("title", "Alert")
        description = alert.get("description", "")

        return f"[{severity}] {title}\n{description}"

    def _format_alert_html(self, alert: Dict[str, Any]) -> str:
        """Format alert into HTML message."""
        severity = alert.get("severity", "info").upper()
        title = alert.get("title", "Alert")
        description = alert.get("description", "")
        severity_color = self._get_severity_color(alert.get("severity"))

        return f"""
        <div style="border-left: 4px solid {severity_color}; padding: 12px;">
            <h3 style="margin: 0 0 8px 0; color: {severity_color};">[{severity}] {title}</h3>
            <p style="margin: 0; color: #666;">{description}</p>
        </div>
        """

    @staticmethod
    def _get_severity_color(severity: str) -> str:
        """Get hex color for severity level."""
        colors = {
            "critical": "#ef4444",
            "warning": "#f59e0b",
            "info": "#3b82f6",
        }
        return colors.get(severity, "#6b7280")
