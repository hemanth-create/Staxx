"""Datadog log connector."""

import logging
from datetime import datetime
from typing import List, Optional
import aiohttp
from log_connector.base import BaseLogConnector, LogEntry

logger = logging.getLogger(__name__)


class DatadogConnector(BaseLogConnector):
    """Connect to Datadog and fetch LLM call logs."""

    def __init__(
        self,
        api_key: str,
        app_key: str,
        service: str = "llm-calls",
        site: str = "datadoghq.com",
    ):
        """Initialize Datadog connector."""
        self.api_key = api_key
        self.app_key = app_key
        self.service = service
        self.site = site
        self.base_url = f"https://api.{site}"

    async def authenticate(self) -> bool:
        """Test Datadog API access."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                async with session.get(
                    f"{self.base_url}/api/v1/validate",
                    headers=headers,
                    timeout=10,
                ) as resp:
                    success = resp.status == 200
                    if success:
                        logger.info("✓ Datadog authentication successful")
                    else:
                        logger.error(f"Datadog auth failed: {resp.status}")
                    return success
        except Exception as e:
            logger.error(f"Datadog auth error: {e}")
            return False

    async def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> List[LogEntry]:
        """Fetch LLM logs from Datadog."""
        logs = []

        try:
            # Use Datadog Log Query API
            query = f'service:{self.service} status:success @timestamp:[{int(start_time.timestamp())} TO {int(end_time.timestamp())}]'

            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                params = {
                    "query": query,
                    "limit": limit,
                    "sort": "timestamp",
                }

                async with session.get(
                    f"{self.base_url}/api/v2/logs/events",
                    headers=headers,
                    params=params,
                    timeout=30,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("data", []):
                            try:
                                entry = self._parse_log_item(item)
                                if entry:
                                    logs.append(entry)
                            except Exception as e:
                                logger.warning(f"Failed to parse Datadog log: {e}")

        except Exception as e:
            logger.error(f"Failed to fetch Datadog logs: {e}")

        return logs

    async def health_check(self) -> bool:
        """Check Datadog connectivity."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                async with session.get(
                    f"{self.base_url}/api/v1/validate",
                    headers=headers,
                    timeout=10,
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Datadog health check failed: {e}")
            return False

    def _get_headers(self) -> dict:
        """Get Datadog API headers."""
        return {
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key,
            "Content-Type": "application/json",
        }

    def _parse_log_item(self, item: dict) -> Optional[LogEntry]:
        """Parse Datadog log item into LogEntry."""
        try:
            attributes = item.get("attributes", {})
            content = attributes.get("message", {})

            if isinstance(content, str):
                import json

                content = json.loads(content)

            return LogEntry(
                timestamp=datetime.fromisoformat(
                    attributes.get("timestamp", "").replace("Z", "+00:00")
                ),
                model=content.get("model", "unknown"),
                input_tokens=int(content.get("input_tokens", 0)),
                output_tokens=int(content.get("output_tokens", 0)),
                latency_ms=float(content.get("latency_ms", 0)),
                status=content.get("status", "unknown"),
                error=content.get("error"),
                metadata=content.get("metadata"),
            )
        except Exception as e:
            logger.warning(f"Failed to parse Datadog item: {e}")
            return None
