"""
Staxx Intelligence — Adapters Package

Exports the adapter registry that maps model IDs to the correct
provider adapter.  Import ``get_adapter`` to obtain the right
adapter for any model.
"""

from __future__ import annotations

import logging
from typing import Optional

from shadow_eval.adapters.base import AdapterRequest, AdapterResponse, BaseAdapter

logger = logging.getLogger(__name__)

# Lazy imports to avoid import-time failures (e.g. missing boto3)
_adapter_instances: list[BaseAdapter] = []
_initialised = False


def _init_adapters() -> None:
    """Lazy-load all adapter instances once."""
    global _adapter_instances, _initialised
    if _initialised:
        return

    from shadow_eval.adapters.openai_adapter import OpenAIAdapter
    from shadow_eval.adapters.anthropic_adapter import AnthropicAdapter
    from shadow_eval.adapters.bedrock_adapter import BedrockAdapter
    from shadow_eval.adapters.google_adapter import GoogleAdapter

    _adapter_instances = [
        OpenAIAdapter(),
        AnthropicAdapter(),
        BedrockAdapter(),
        GoogleAdapter(),
    ]
    _initialised = True


def get_adapter(model_id: str) -> Optional[BaseAdapter]:
    """
    Return the adapter that supports *model_id*, or None.

    The first adapter whose ``supports_model`` returns True wins.
    """
    _init_adapters()
    for adapter in _adapter_instances:
        if adapter.supports_model(model_id):
            return adapter
    logger.warning("No adapter found for model '%s'", model_id)
    return None


__all__ = [
    "AdapterRequest",
    "AdapterResponse",
    "BaseAdapter",
    "get_adapter",
]
