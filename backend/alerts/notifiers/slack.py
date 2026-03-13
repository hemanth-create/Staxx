"""Slack notifier for alert messages."""

from typing import Dict, Any
import logging
import aiohttp
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class SlackNotifier(BaseNotifier):
    """Send alerts to Slack via webhook."""

    async def send(self, alert: Dict[str, Any]) -> bool:
        """
        Send alert to Slack.

        Args:
            alert: Alert dictionary

        Returns:
            True if message posted successfully
        """
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            logger.warning("No Slack webhook URL configured")
            return False

        payload = self._build_slack_message(alert)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    success = response.status == 200
                    if not success:
                        logger.error(f"Slack API returned {response.status}")
                    return success
        except Exception as e:
            logger.error(f"Failed to send Slack message: {str(e)}")
            return False

    def _build_slack_message(self, alert: Dict[str, Any]) -> dict:
        """Build Slack message payload with formatting."""
        severity = alert.get("severity", "info").lower()
        color_map = {
            "critical": "#ef4444",
            "warning": "#f59e0b",
            "info": "#3b82f6",
        }
        color = color_map.get(severity, "#6b7280")

        return {
            "attachments": [
                {
                    "color": color,
                    "title": alert.get("title", "Alert"),
                    "text": alert.get("description", ""),
                    "fields": [
                        {
                            "title": "Severity",
                            "value": severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Type",
                            "value": alert.get("alert_type", "unknown"),
                            "short": True
                        }
                    ] + self._build_extra_fields(alert),
                    "footer": "Staxx Alerts",
                    "ts": int(alert.get("created_at", 0))
                }
            ]
        }

    @staticmethod
    def _build_extra_fields(alert: Dict[str, Any]) -> list:
        """Build additional fields for Slack message."""
        fields = []

        if alert.get("model"):
            fields.append({
                "title": "Model",
                "value": alert["model"],
                "short": True
            })

        if alert.get("metric_name"):
            fields.append({
                "title": "Metric",
                "value": alert["metric_name"],
                "short": True
            })

        if alert.get("task_type"):
            fields.append({
                "title": "Task Type",
                "value": alert["task_type"],
                "short": True
            })

        return fields
