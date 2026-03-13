"""Slack notifier."""

import logging
from typing import Optional
import aiohttp
from alerts.notifiers.base import BaseNotifier
from alerts.db.models import Alert

logger = logging.getLogger(__name__)


class SlackNotifier(BaseNotifier):
    """Send alerts to Slack via webhook."""

    async def send(self, alert: Alert, webhook_url: str) -> bool:
        """Send alert to Slack channel."""
        try:
            payload = self._build_slack_message(alert)
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, timeout=10) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def _build_slack_message(self, alert: Alert) -> dict:
        """Build Slack message block format."""
        color_map = {
            "critical": "#EF4444",
            "warning": "#F59E0B",
            "info": "#3B82F6",
        }
        color = color_map.get(alert.severity, "#3B82F6")

        fields = []

        if alert.task_type:
            fields.append(
                {"title": "Task Type", "value": alert.task_type, "short": True}
            )

        if alert.model:
            fields.append({"title": "Model", "value": alert.model, "short": True})

        if alert.metric_name:
            fields.append(
                {"title": "Metric", "value": alert.metric_name, "short": True}
            )

        if alert.current_value is not None:
            fields.append(
                {
                    "title": "Current Value",
                    "value": f"{alert.current_value:.4f}",
                    "short": True,
                }
            )

        return {
            "attachments": [
                {
                    "fallback": alert.title,
                    "color": color,
                    "title": alert.title,
                    "text": alert.description,
                    "fields": fields,
                    "footer": "Staxx Intelligence",
                    "ts": int(alert.created_at.timestamp())
                    if alert.created_at
                    else None,
                }
            ]
        }
