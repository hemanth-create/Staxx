"""Generic webhook notifier for custom integrations."""

from typing import Dict, Any
import logging
import aiohttp
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class WebhookNotifier(BaseNotifier):
    """Send alerts to arbitrary HTTP webhooks."""

    async def send(self, alert: Dict[str, Any]) -> bool:
        """
        Send alert via webhook POST.

        Args:
            alert: Alert dictionary

        Returns:
            True if webhook returned success status
        """
        webhook_url = self.config.get("url")
        if not webhook_url:
            logger.warning("No webhook URL configured")
            return False

        headers = self._build_headers()
        payload = self._build_payload(alert)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    success = 200 <= response.status < 300
                    if not success:
                        logger.warning(f"Webhook returned {response.status}")
                    return success
        except asyncio.TimeoutError:
            logger.error("Webhook request timed out")
            return False
        except Exception as e:
            logger.error(f"Webhook request failed: {str(e)}")
            return False

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for webhook request."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Staxx/1.0"
        }

        # Add custom headers from config
        custom_headers = self.config.get("headers", {})
        headers.update(custom_headers)

        # Add authentication if configured
        if self.config.get("auth_token"):
            headers["Authorization"] = f"Bearer {self.config['auth_token']}"

        return headers

    def _build_payload(self, alert: Dict[str, Any]) -> dict:
        """Build webhook payload."""
        payload_format = self.config.get("payload_format", "staxx")

        if payload_format == "slack":
            # Slack-compatible format
            return {
                "text": f"*[{alert.get('severity', 'info').upper()}] {alert.get('title', 'Alert')}*\n"
                        f"{alert.get('description', '')}",
                "attachments": [
                    {
                        "color": self._get_color(alert.get("severity")),
                        "fields": [
                            {"title": "Type", "value": alert.get("alert_type", ""), "short": True},
                            {"title": "Severity", "value": alert.get("severity", ""), "short": True},
                        ]
                    }
                ]
            }
        else:
            # Default Staxx format
            return {
                "alert_id": alert.get("id"),
                "title": alert.get("title"),
                "description": alert.get("description"),
                "severity": alert.get("severity"),
                "alert_type": alert.get("alert_type"),
                "created_at": alert.get("created_at"),
                "model": alert.get("model"),
                "metric_name": alert.get("metric_name"),
                "task_type": alert.get("task_type"),
            }

    @staticmethod
    def _get_color(severity: str) -> str:
        """Get color for severity."""
        colors = {
            "critical": "#ef4444",
            "warning": "#f59e0b",
            "info": "#3b82f6",
        }
        return colors.get(severity, "#6b7280")


# Avoid undefined asyncio
import asyncio
