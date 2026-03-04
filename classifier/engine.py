"""
Staxx Task Classifier — Main orchestration engine.

The public API is a single function::

    result = classify(input_data)

Orchestration flow:
  1. Normalise raw request body into a ``ClassifierInput``.
  2. Run **Tier 1 (rule engine)**  — fast keyword + pattern matching.
  3. If Tier 1 confidence ≥ 0.85 → return immediately.
  4. Otherwise run **Tier 2 (ML classifier)** if available.
  5. Compute **prompt complexity score** (always, regardless of tier).
  6. Return a ``TaskClassification`` result.
"""

from __future__ import annotations

import logging
from typing import Any

from classifier import complexity_scorer, ml_classifier, rule_engine
from classifier.schemas import (
    ClassificationTier,
    ClassifierInput,
    TaskClassification,
    TaskType,
)

logger = logging.getLogger(__name__)


# ── Public API ─────────────────────────────────────────────────────────

def classify(
    raw_body: dict[str, Any] | None = None,
    *,
    input_data: ClassifierInput | None = None,
) -> TaskClassification:
    """Classify an LLM API call into a task type.

    Pass **either** ``raw_body`` (the original JSON request body) or a
    pre-built ``ClassifierInput``.

    Args:
        raw_body: The full request body dict (OpenAI / Anthropic format).
        input_data: Pre-built normalised input (takes precedence).

    Returns:
        A fully populated ``TaskClassification``.
    """
    # ── 1. Normalise input ──────────────────────────────────────────
    if input_data is not None:
        inp = input_data
    elif raw_body is not None:
        inp = _normalise_input(raw_body)
    else:
        raise ValueError("Either raw_body or input_data must be provided.")

    # ── 2. Tier 1: Rule Engine ──────────────────────────────────────
    best_rule, _all_rules = rule_engine.classify(inp)

    if best_rule is not None and best_rule.score >= rule_engine.TIER1_CONFIDENCE_THRESHOLD:
        complexity = complexity_scorer.score(inp)
        return TaskClassification(
            task_type=best_rule.task_type.value,
            confidence=round(best_rule.score, 4),
            classification_tier=ClassificationTier.RULE_ENGINE.value,
            signals=[s.label for s in best_rule.signals],
            prompt_complexity_score=round(complexity, 4),
        )

    # ── 3. Tier 2: ML Classifier (fallback) ─────────────────────────
    ml_result = _try_ml_classification(inp)
    if ml_result is not None:
        return ml_result

    # ── 4. Fall back to best Tier 1 result (even below threshold) ───
    complexity = complexity_scorer.score(inp)

    if best_rule is not None:
        return TaskClassification(
            task_type=best_rule.task_type.value,
            confidence=round(best_rule.score, 4),
            classification_tier=ClassificationTier.RULE_ENGINE.value,
            signals=[s.label for s in best_rule.signals],
            prompt_complexity_score=round(complexity, 4),
        )

    # Use the top-scoring entry from all_rules even if below threshold.
    # This gives a best-effort classification rather than "other".
    top_rules = sorted(_all_rules, key=lambda r: r.score, reverse=True)
    if top_rules and top_rules[0].score > 0:
        top = top_rules[0]
        from classifier.rule_engine import _SCORE_CEILING
        normalised_score = min(top.score / _SCORE_CEILING, 1.0)
        return TaskClassification(
            task_type=top.task_type.value,
            confidence=round(normalised_score, 4),
            classification_tier=ClassificationTier.RULE_ENGINE.value,
            signals=[s.label for s in top.signals],
            prompt_complexity_score=round(complexity, 4),
        )

    # ── 5. Absolute fallback ────────────────────────────────────────
    return TaskClassification(
        task_type=TaskType.OTHER.value,
        confidence=0.0,
        classification_tier=ClassificationTier.RULE_ENGINE.value,
        signals=[],
        prompt_complexity_score=round(complexity, 4),
    )


# ── Input normalisation ───────────────────────────────────────────────

def _normalise_input(raw_body: dict[str, Any]) -> ClassifierInput:
    """Convert a raw request body dict into a ``ClassifierInput``.

    Handles both OpenAI and Anthropic request formats:
      - OpenAI: ``{"messages": [...], "model": "...", ...}``
      - Anthropic: ``{"messages": [...], "model": "...", "system": "..."}``
    """
    messages = raw_body.get("messages", [])
    model = raw_body.get("model", "unknown")
    response_format = raw_body.get("response_format")
    max_tokens = raw_body.get("max_tokens")

    # Anthropic puts the system prompt in a top-level "system" field.
    anthropic_system = raw_body.get("system")
    if anthropic_system and isinstance(anthropic_system, str):
        # Prepend as a system message if not already present.
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            messages = [{"role": "system", "content": anthropic_system}] + list(messages)

    return ClassifierInput(
        messages=messages,
        model=model,
        response_format=response_format,
        max_tokens=max_tokens,
        raw_body=raw_body,
    )


# ── ML tier helper ─────────────────────────────────────────────────────

def _try_ml_classification(inp: ClassifierInput) -> TaskClassification | None:
    """Attempt Tier 2 ML classification.

    Returns ``None`` if the ML backend is unavailable (torch not
    installed, model failed to load, etc.).
    """
    if not ml_classifier.is_available():
        logger.debug("ML classifier unavailable — staying on Tier 1.")
        return None

    try:
        clf = ml_classifier.get_default_classifier()
        task_type, confidence, _raw_scores = clf.predict(inp.full_prompt)

        complexity = complexity_scorer.score(inp)

        return TaskClassification(
            task_type=task_type.value,
            confidence=round(confidence, 4),
            classification_tier=ClassificationTier.ML_CLASSIFIER.value,
            signals=["ml_model_prediction"],
            prompt_complexity_score=round(complexity, 4),
        )
    except Exception:
        logger.error("ML classification failed — falling back", exc_info=True)
        return None
