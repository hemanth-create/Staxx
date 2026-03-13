"""CloudWatch log connector for AWS CloudWatch Logs."""

import logging
import json
from datetime import datetime
from typing import List, Optional
import boto3
from log_connector.base import BaseLogConnector, LogEntry

logger = logging.getLogger(__name__)


class CloudWatchConnector(BaseLogConnector):
    """Connect to AWS CloudWatch Logs and fetch LLM call logs."""

    def __init__(
        self,
        aws_region: str,
        log_group_name: str,
        log_stream_prefix: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize CloudWatch connector."""
        self.aws_region = aws_region
        self.log_group_name = log_group_name
        self.log_stream_prefix = log_stream_prefix

        self.client = boto3.client(
            "logs",
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    async def authenticate(self) -> bool:
        """Test CloudWatch access."""
        try:
            self.client.describe_log_groups(limit=1)
            logger.info("✓ CloudWatch authentication successful")
            return True
        except Exception as e:
            logger.error(f"CloudWatch auth failed: {e}")
            return False

    async def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> List[LogEntry]:
        """Fetch LLM logs from CloudWatch."""
        logs = []

        try:
            # Describe log streams
            response = self.client.describe_log_streams(
                logGroupName=self.log_group_name,
                logStreamNamePrefix=self.log_stream_prefix,
            )

            for stream in response.get("logStreams", []):
                stream_name = stream["logStreamName"]

                # Fetch events from stream
                events_response = self.client.get_log_events(
                    logGroupName=self.log_group_name,
                    logStreamName=stream_name,
                    startTime=int(start_time.timestamp() * 1000),
                    endTime=int(end_time.timestamp() * 1000),
                    limit=limit,
                )

                for event in events_response.get("events", []):
                    try:
                        entry = self._parse_log_event(event)
                        if entry:
                            logs.append(entry)
                    except Exception as e:
                        logger.warning(f"Failed to parse event: {e}")

        except Exception as e:
            logger.error(f"Failed to fetch CloudWatch logs: {e}")

        return logs

    async def health_check(self) -> bool:
        """Check CloudWatch connectivity."""
        try:
            self.client.describe_log_groups(limit=1)
            return True
        except Exception as e:
            logger.error(f"CloudWatch health check failed: {e}")
            return False

    def _parse_log_event(self, event: dict) -> Optional[LogEntry]:
        """Parse CloudWatch log event into LogEntry."""
        try:
            message = json.loads(event["message"])

            # Expected log format:
            # {
            #   "timestamp": "2024-03-15T10:30:00Z",
            #   "model": "gpt-4o",
            #   "input_tokens": 250,
            #   "output_tokens": 100,
            #   "latency_ms": 1200,
            #   "status": "success"
            # }

            return LogEntry(
                timestamp=datetime.fromisoformat(
                    message.get("timestamp", "").replace("Z", "+00:00")
                ),
                model=message.get("model", "unknown"),
                input_tokens=int(message.get("input_tokens", 0)),
                output_tokens=int(message.get("output_tokens", 0)),
                latency_ms=float(message.get("latency_ms", 0)),
                status=message.get("status", "unknown"),
                error=message.get("error"),
                metadata=message.get("metadata"),
            )
        except Exception as e:
            logger.warning(f"Failed to parse CloudWatch event: {e}")
            return None
