"""
Staxx Intelligence — Candidate Selector

Given an original model and task type, selects all cheaper candidate
models suitable for shadow evaluation.

Selection criteria:
  1. Candidate must cost less than the original model (based on the
     pricing catalog's total cost = avg of input + output per 1M tokens).
  2. Candidate must be compatible with the task type (e.g. code gen
     models should still be general-purpose LLMs).
  3. Candidate must have a working adapter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from cost_engine.pricing_catalog import ModelPricing, get_catalog
from shadow_eval.adapters import get_adapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CandidateModel:
    """A model that is cheaper than the original and eligible for shadow eval."""

    canonical_name: str
    provider: str
    input_per_1m_tokens: float
    output_per_1m_tokens: float
    avg_cost_per_1m_tokens: float  # (input + output) / 2 — used for ranking
    savings_pct: float  # Estimated savings percentage vs the original model


# ---------------------------------------------------------------------------
# Task-type compatibility matrix
# ---------------------------------------------------------------------------
# Some models are not suitable for certain task types.  For example,
# very small models may struggle with complex code generation.
# This is a conservative allowlist — models not listed are allowed
# for all tasks by default.

_TASK_BLOCKLIST: dict[str, set[str]] = {
    # Task types where very small models are blocked
    "code_generation": {"llama-3.1-8b", "mistral-nemo"},
    "multi_turn_chat": {"llama-3.1-8b"},
}

# Models that are only suitable for specific task types
# (empty = suitable for all tasks)
_MODEL_ALLOWED_TASKS: dict[str, set[str]] = {
    # All models are allowed for all tasks by default
}


def _avg_cost(pricing: ModelPricing) -> float:
    """Simple average of input + output cost per 1M tokens."""
    return (pricing.input_per_1m_tokens + pricing.output_per_1m_tokens) / 2


def _is_compatible(model_name: str, task_type: str) -> bool:
    """Check if a model is compatible with a task type."""
    # Check blocklist
    blocked_models = _TASK_BLOCKLIST.get(task_type, set())
    if model_name.lower() in {m.lower() for m in blocked_models}:
        return False

    # Check model-specific allowlist (if any)
    allowed_tasks = _MODEL_ALLOWED_TASKS.get(model_name.lower())
    if allowed_tasks is not None and task_type not in allowed_tasks:
        return False

    return True


def select_candidates(
    original_model: str,
    task_type: str,
    max_candidates: int = 5,
    min_savings_pct: float = 10.0,
) -> list[CandidateModel]:
    """
    Select candidate models cheaper than *original_model* for
    shadow evaluation of *task_type* prompts.

    Args:
        original_model: The model currently used in production.
        task_type: The classified task type (e.g. summarization, extraction).
        max_candidates: Maximum number of candidates to return.
        min_savings_pct: Minimum savings threshold (%) to include a candidate.

    Returns:
        List of ``CandidateModel`` sorted by savings percentage (highest first).
    """
    catalog = get_catalog()

    # Get pricing for the original model
    original_pricing = catalog.get_pricing(original_model)
    original_avg = _avg_cost(original_pricing)

    if original_avg <= 0:
        logger.warning("Original model '%s' has zero cost — no candidates to evaluate", original_model)
        return []

    # Get all models from the catalog
    all_models = catalog.list_models()

    candidates: list[CandidateModel] = []

    for model_pricing in all_models:
        # Skip the original model itself
        if model_pricing.canonical_name.lower() == original_pricing.canonical_name.lower():
            continue

        # Skip models that are NOT cheaper
        candidate_avg = _avg_cost(model_pricing)
        if candidate_avg >= original_avg:
            continue

        # Skip models with no adapter
        adapter = get_adapter(model_pricing.canonical_name)
        if adapter is None:
            logger.debug(
                "Skipping %s — no adapter available",
                model_pricing.canonical_name,
            )
            continue

        # Skip models incompatible with the task type
        if not _is_compatible(model_pricing.canonical_name, task_type):
            logger.debug(
                "Skipping %s — incompatible with task type '%s'",
                model_pricing.canonical_name,
                task_type,
            )
            continue

        # Calculate savings percentage
        savings_pct = ((original_avg - candidate_avg) / original_avg) * 100

        if savings_pct < min_savings_pct:
            continue

        candidates.append(
            CandidateModel(
                canonical_name=model_pricing.canonical_name,
                provider=model_pricing.provider,
                input_per_1m_tokens=model_pricing.input_per_1m_tokens,
                output_per_1m_tokens=model_pricing.output_per_1m_tokens,
                avg_cost_per_1m_tokens=candidate_avg,
                savings_pct=round(savings_pct, 2),
            )
        )

    # Sort by savings percentage (highest first) and limit
    candidates.sort(key=lambda c: c.savings_pct, reverse=True)
    return candidates[:max_candidates]
