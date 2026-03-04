"""
Staxx Task Classifier — Tier 1: Rule Engine.

A fast, deterministic classifier that uses keyword matching, compiled
regex patterns, and structural signal detection to classify LLM prompts.

Performance target: **< 2 ms per call**.  No ML models, no I/O, no
allocations beyond the result objects.
"""

from __future__ import annotations

from typing import Any

from classifier.patterns import (
    STRUCTURAL_DETECTORS,
    TASK_KEYWORDS,
    TASK_PATTERNS,
)
from classifier.schemas import (
    ClassifierInput,
    RuleResult,
    RuleSignal,
    TaskType,
)


# ── Confidence tier threshold ──────────────────────────────────────────
TIER1_CONFIDENCE_THRESHOLD: float = 0.85

# Normalisation ceiling — accumulated raw scores above this are clamped
# to 1.0 confidence.  Tuned so that 2-3 strong signals yield ~0.90.
_SCORE_CEILING: float = 6.0


def classify(inp: ClassifierInput) -> tuple[RuleResult | None, list[RuleResult]]:
    """Run Tier 1 classification on the input.

    Returns:
        A tuple of ``(best_result_or_none, all_results)``.

        * ``best_result`` is the highest-scoring result **if** its
          normalised confidence ≥ ``TIER1_CONFIDENCE_THRESHOLD``.
          Otherwise ``None`` (meaning Tier 2 should be invoked).
        * ``all_results`` is the full ranked list for debugging /
          logging.
    """
    prompt_lower = inp.full_prompt.lower()
    results: dict[str, RuleResult] = {
        tt.value: RuleResult(task_type=tt) for tt in TaskType if tt != TaskType.OTHER
    }

    # ── 1. Keyword matching ─────────────────────────────────────────
    _apply_keywords(prompt_lower, results)

    # ── 2. Regex pattern matching ───────────────────────────────────
    _apply_patterns(inp.full_prompt, results)

    # ── 3. Structural signals ───────────────────────────────────────
    _apply_structural(inp, results)

    # ── 4. Rank and normalise ───────────────────────────────────────
    ranked = sorted(results.values(), key=lambda r: r.score, reverse=True)

    if not ranked or ranked[0].score == 0:
        return None, ranked

    best = ranked[0]
    confidence = min(best.score / _SCORE_CEILING, 1.0)

    # Build the output RuleResult with normalised confidence.
    best_normalised = RuleResult(
        task_type=best.task_type,
        score=confidence,
        signals=best.signals,
    )

    if confidence >= TIER1_CONFIDENCE_THRESHOLD:
        return best_normalised, ranked
    return None, ranked


# ── internal: keyword phase ────────────────────────────────────────────

def _apply_keywords(
    prompt_lower: str,
    results: dict[str, RuleResult],
) -> None:
    """Scan the lowered prompt for weighted keywords per task type."""
    for task_type, keywords in TASK_KEYWORDS.items():
        result = results.get(task_type)
        if result is None:
            continue
        for phrase, weight in keywords:
            if phrase in prompt_lower:
                result.score += weight
                result.signals.append(
                    RuleSignal(source="keyword", detail=phrase, weight=weight)
                )


# ── internal: regex phase ──────────────────────────────────────────────

def _apply_patterns(
    prompt_text: str,
    results: dict[str, RuleResult],
) -> None:
    """Run compiled regex patterns against the raw prompt text."""
    for task_type, patterns in TASK_PATTERNS.items():
        result = results.get(task_type)
        if result is None:
            continue
        for pattern, weight in patterns:
            if pattern.search(prompt_text):
                result.score += weight
                result.signals.append(
                    RuleSignal(
                        source="pattern",
                        detail=pattern.pattern[:80],
                        weight=weight,
                    )
                )


# ── internal: structural phase ─────────────────────────────────────────

def _apply_structural(
    inp: ClassifierInput,
    results: dict[str, RuleResult],
) -> None:
    """Run structural detectors (message count, response_format, etc.)."""
    for task_type, detectors in STRUCTURAL_DETECTORS.items():
        result = results.get(task_type)
        if result is None:
            continue
        for detector in detectors:
            detected, detail, weight = detector(inp)
            if detected:
                result.score += weight
                result.signals.append(
                    RuleSignal(source="structural", detail=detail, weight=weight)
                )
