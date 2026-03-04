"""
Staxx Intelligence — Abstract Model Adapter Interface

Every LLM provider adapter must implement this interface so the
evaluator and scheduler can treat all models uniformly.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class AdapterRequest:
    """Normalised input for any LLM provider."""

    model: str
    messages: list[dict[str, str]]  # [{"role": "system"|"user"|"assistant", "content": "..."}]
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout_seconds: float = 30.0


@dataclass
class AdapterResponse:
    """Normalised output from any LLM provider."""

    text_output: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    error: Optional[str] = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error is None and len(self.text_output) > 0


class BaseAdapter(abc.ABC):
    """
    Abstract base class for LLM provider adapters.

    All adapters:
      • Accept an ``AdapterRequest``
      • Return an ``AdapterResponse`` with normalised fields
      • Handle timeouts, retries, and error mapping internally
    """

    PROVIDER: str = "unknown"

    @abc.abstractmethod
    async def invoke(self, request: AdapterRequest) -> AdapterResponse:
        """Send the request to the provider and return a normalised response."""
        ...

    @abc.abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """Return True if this adapter can serve the given model identifier."""
        ...
