"""
Staxx Proxy Gateway — Token count extraction from provider responses.

Each provider returns token usage in a different shape.  This module
normalises the extraction so the telemetry layer always gets clean
``(input_tokens, output_tokens)`` integers.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def extract_openai_tokens(response_body: dict[str, Any]) -> tuple[int, int]:
    """Extract token counts from an OpenAI-compatible response.

    OpenAI responses include a top-level ``usage`` object::

        {
          "usage": {
            "prompt_tokens": 42,
            "completion_tokens": 128,
            "total_tokens": 170
          }
        }

    For streaming responses the caller should accumulate chunks and pass
    the final assembled body here, or use the ``x-usage`` trailing header
    when available.

    Returns:
        Tuple of ``(input_tokens, output_tokens)``.  Zeros when data is
        unavailable.
    """
    usage = response_body.get("usage") or {}
    input_tokens = _safe_int(usage.get("prompt_tokens"))
    output_tokens = _safe_int(usage.get("completion_tokens"))
    return input_tokens, output_tokens


def extract_anthropic_tokens(response_body: dict[str, Any]) -> tuple[int, int]:
    """Extract token counts from an Anthropic Messages response.

    Anthropic responses include a top-level ``usage`` object::

        {
          "usage": {
            "input_tokens": 42,
            "output_tokens": 128
          }
        }

    Returns:
        Tuple of ``(input_tokens, output_tokens)``.
    """
    usage = response_body.get("usage") or {}
    input_tokens = _safe_int(usage.get("input_tokens"))
    output_tokens = _safe_int(usage.get("output_tokens"))
    return input_tokens, output_tokens


def extract_tokens(
    provider: str,
    response_body: dict[str, Any],
) -> tuple[int, int]:
    """Dispatch to the correct provider-specific extractor.

    Args:
        provider: One of ``"openai"``, ``"anthropic"``.
        response_body: The parsed JSON body returned by the provider.

    Returns:
        Tuple of ``(input_tokens, output_tokens)``.
    """
    extractors = {
        "openai": extract_openai_tokens,
        "anthropic": extract_anthropic_tokens,
    }

    extractor = extractors.get(provider)
    if extractor is None:
        logger.warning("token_extractor.unknown_provider", provider=provider)
        return 0, 0

    try:
        return extractor(response_body)
    except Exception:
        logger.warning(
            "token_extractor.extraction_failed",
            provider=provider,
            exc_info=True,
        )
        return 0, 0


def estimate_tokens_from_text(text: str) -> int:
    """Rough token estimate when usage data is unavailable.

    Uses the common heuristic of ~4 characters per token for English text.
    This is only used as a last-resort fallback.
    """
    return max(1, len(text) // 4)


# ── internal helpers ────────────────────────────────────────────────────
def _safe_int(value: Any) -> int:
    """Coerce a value to ``int``, returning ``0`` on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
