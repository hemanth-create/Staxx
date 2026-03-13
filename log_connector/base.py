"""Base log connector interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class LogEntry:
    """Normalized log entry from any source."""

    def __init__(
        self,
        timestamp: datetime,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        status: str,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.timestamp = timestamp
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.latency_ms = latency_ms
        self.status = status
        self.error = error
        self.metadata = metadata or {}


class BaseLogConnector(ABC):
    """Abstract base for log connectors."""

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the log source."""
        pass

    @abstractmethod
    async def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> List[LogEntry]:
        """Fetch logs from the source."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Test connectivity to the log source."""
        pass
