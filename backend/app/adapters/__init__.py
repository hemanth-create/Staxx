from app.adapters.base import BaseAdapter, AdapterConfig, GenerationResult
from app.adapters.openai import OpenAIAdapter
from app.adapters.anthropic import AnthropicAdapter

def get_adapter(provider_name: str) -> BaseAdapter:
    """Factory for instantiating model adapters based on provider name."""
    provider_name = provider_name.lower()
    if provider_name == "openai":
        return OpenAIAdapter()
    elif provider_name == "anthropic":
        return AnthropicAdapter()
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")

__all__ = [
    "BaseAdapter", 
    "AdapterConfig", 
    "GenerationResult", 
    "OpenAIAdapter", 
    "AnthropicAdapter",
    "get_adapter"
]
