from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class AdapterConfig(BaseModel):
    """Configuration passed to all adapters during evaluation."""
    model: str
    temperature: float = 0.0
    max_tokens: int = 1000
    json_mode: bool = False
    system_prompt: Optional[str] = None


class GenerationResult(BaseModel):
    """Standardized output from any model adapter."""
    content: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    error: Optional[str] = None


class BaseAdapter(ABC):
    """
    Abstract base class for LLM Provider adapters.
    Ensures a consistent interface for the shadow evaluation worker.
    """

    @abstractmethod
    async def generate(self, prompt: str, config: AdapterConfig) -> GenerationResult:
        """
        Executes a generation request against the provider.
        Must handle its own timing and token counting if the provider doesn't supply it.
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens using the provider's specific tokenizer (e.g., tiktoken).
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the identifier for this provider."""
        pass
