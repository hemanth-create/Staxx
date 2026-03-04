"""
Staxx Intelligence — Cost Calculator

Stateless cost calculation logic.  Given a model identifier and
token counts (or raw text for estimation), produces a USD cost figure
using the pricing catalog.

All edge cases are handled:
  • Missing token counts  → estimate from character length
  • Unknown model         → fallback pricing + logged warning
  • Per-org markup        → applied on top of base cost
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from cost_engine.pricing_catalog import ModelPricing, get_catalog

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CostResult:
    """Immutable result of a cost calculation."""

    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    markup_usd: float
    final_cost_usd: float  # total + markup
    model_canonical: str
    provider: str
    input_tokens_used: int
    output_tokens_used: int
    was_estimated: bool  # True if token counts were estimated


def estimate_tokens(text: str, chars_per_token: int = 4) -> int:
    """
    Estimate token count from raw text length.

    Uses the configurable chars-per-token heuristic (default 4,
    roughly accurate for English with tiktoken cl100k_base).
    Returns at least 1 token for any non-empty string.
    """
    if not text:
        return 0
    return max(1, len(text) // chars_per_token)


def calculate_cost(
    model_id: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    input_text: Optional[str] = None,
    output_text: Optional[str] = None,
    org_id: Optional[str] = None,
) -> CostResult:
    """
    Calculate the cost of a single LLM API call.

    Priority for token counts:
      1. Explicit ``input_tokens`` / ``output_tokens`` if provided and > 0
      2. Estimated from ``input_text`` / ``output_text`` character length
      3. Falls back to 0 (logged as warning)

    Args:
        model_id: The model identifier as reported by the provider API.
        input_tokens: Exact input token count (if available).
        output_tokens: Exact output token count (if available).
        input_text: Raw input/prompt text (used for estimation when tokens missing).
        output_text: Raw output/completion text (used for estimation when tokens missing).
        org_id: Organisation UUID string; used to apply custom markup if configured.

    Returns:
        A ``CostResult`` with full cost breakdown.
    """
    catalog = get_catalog()
    pricing: ModelPricing = catalog.get_pricing(model_id)

    was_estimated = False

    # --- Resolve input tokens -------------------------------------------------
    if input_tokens is not None and input_tokens > 0:
        effective_input_tokens = input_tokens
    elif input_text:
        effective_input_tokens = estimate_tokens(input_text, catalog.chars_per_token)
        was_estimated = True
        logger.debug(
            "Estimated %d input tokens from %d chars for model '%s'",
            effective_input_tokens,
            len(input_text),
            model_id,
        )
    else:
        effective_input_tokens = 0
        if input_tokens is None:
            logger.warning("No input token count or text for model '%s' — input cost will be $0", model_id)

    # --- Resolve output tokens ------------------------------------------------
    if output_tokens is not None and output_tokens > 0:
        effective_output_tokens = output_tokens
    elif output_text:
        effective_output_tokens = estimate_tokens(output_text, catalog.chars_per_token)
        was_estimated = True
        logger.debug(
            "Estimated %d output tokens from %d chars for model '%s'",
            effective_output_tokens,
            len(output_text),
            model_id,
        )
    else:
        effective_output_tokens = 0
        if output_tokens is None:
            logger.warning("No output token count or text for model '%s' — output cost will be $0", model_id)

    # --- Calculate base cost --------------------------------------------------
    input_cost = (effective_input_tokens / 1_000_000) * pricing.input_per_1m_tokens
    output_cost = (effective_output_tokens / 1_000_000) * pricing.output_per_1m_tokens
    total = input_cost + output_cost

    # --- Apply org markup -----------------------------------------------------
    markup_pct = catalog.get_org_markup(org_id) if org_id else 0.0
    markup_usd = total * markup_pct
    final = total + markup_usd

    return CostResult(
        input_cost_usd=round(input_cost, 10),
        output_cost_usd=round(output_cost, 10),
        total_cost_usd=round(total, 10),
        markup_usd=round(markup_usd, 10),
        final_cost_usd=round(final, 10),
        model_canonical=pricing.canonical_name,
        provider=pricing.provider,
        input_tokens_used=effective_input_tokens,
        output_tokens_used=effective_output_tokens,
        was_estimated=was_estimated,
    )
