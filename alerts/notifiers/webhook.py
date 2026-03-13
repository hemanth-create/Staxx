"""Generic webhook notifier for custom integrations."""

import logging
from typing import Optional
import aiohttp
from alerts.notifiers.base import BaseNotifier
from alerts.db.models import Alert

logger = logging.getLogger(__name__)


class WebhookNotifier(BaseNotifier):
    """Send alerts to custom webhook URLs."""

    async def send(self, alert: Alert, webhook_url: str) -> bool:
        """Send alert to webhook endpoint."""
        try:
            payload = self.format_alert(alert)

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Staxx-Alert-System/1.0",
                }
                async with session.post(
                    webhook_url, json=payload, headers=headers, timeout=15
                ) as resp:
                    success = resp.status in (200, 201, 202, 204)
                    if not success:
                        logger.warning(
                            f"Webhook returned {resp.status} for alert {alert.id}"
                        )
                    return success

        except asyncio.TimeoutError:
            logger.error(f"Webhook timeout for alert {alert.id}")
            return False
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


import asyncio
