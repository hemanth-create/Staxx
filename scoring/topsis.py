"""
Staxx Intelligence — TOPSIS Multi-Criteria Ranking

Technique for Order of Preference by Similarity to Ideal Solution.
Ranks candidate models across multiple criteria with configurable
weights per organisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class TOPSISWeights:
    """
    Configurable weights for TOPSIS criteria.

    All weights must sum to 1.0.  Default weights reflect the
    business priority: cost savings are most important.
    """

    cost: float = 0.35
    latency: float = 0.25
    quality: float = 0.20
    error: float = 0.15
    consistency: float = 0.05

    def __post_init__(self) -> None:
        total = self.cost + self.latency + self.quality + self.error + self.consistency
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"TOPSIS weights must sum to 1.0, got {total:.4f}"
            )

    def as_array(self) -> np.ndarray:
        """Return weights as a numpy array in criterion order."""
        return np.array([
            self.cost,
            self.latency,
            self.quality,
            self.error,
            self.consistency,
        ])


@dataclass(frozen=True)
class TOPSISInput:
    """
    Input for a single candidate in the TOPSIS decision matrix.

    Criteria:
      0. cost_savings_pct  — higher is better ↑
      1. latency_p95_ms    — lower is better  ↓
      2. quality_score     — higher is better ↑ (json_validity or 1.0 if N/A)
      3. error_rate        — lower is better  ↓
      4. consistency_cv    — lower is better  ↓
    """

    candidate_model: str
    cost_savings_pct: float
    latency_p95_ms: float
    quality_score: float
    error_rate: float
    consistency_cv: float


# Which criteria are "benefit" (higher=better) vs "cost" (lower=better)
_BENEFIT_CRITERIA = {0, 2}  # cost_savings_pct, quality_score
_COST_CRITERIA = {1, 3, 4}  # latency, error_rate, consistency_cv


def topsis_rank(
    candidates: list[TOPSISInput],
    weights: Optional[TOPSISWeights] = None,
) -> dict[str, float]:
    """
    Rank candidates using TOPSIS.

    Args:
        candidates: List of candidate inputs with metric values.
        weights: Optional custom weights (uses defaults if None).

    Returns:
        Dict mapping candidate_model → TOPSIS score (0.0 to 1.0).
        Higher score = better candidate.
    """
    if not candidates:
        return {}

    if weights is None:
        weights = TOPSISWeights()

    n = len(candidates)
    if n == 1:
        # Single candidate — assign score based on absolute quality
        c = candidates[0]
        # Simple heuristic: score based on savings and low error rate
        score = min(1.0, max(0.0, (
            0.5
            + 0.3 * min(c.cost_savings_pct / 100, 0.5)
            - 0.3 * c.error_rate
            + 0.1 * c.quality_score
            - 0.05 * min(c.consistency_cv, 1.0)
        )))
        return {c.candidate_model: round(score, 4)}

    # --- Step 1: Build the decision matrix ---
    matrix = np.zeros((n, 5))
    for i, c in enumerate(candidates):
        matrix[i] = [
            c.cost_savings_pct,
            c.latency_p95_ms,
            c.quality_score,
            c.error_rate,
            c.consistency_cv,
        ]

    # --- Step 2: Normalise (vector normalisation) ---
    norms = np.sqrt(np.sum(matrix ** 2, axis=0))
    # Avoid division by zero
    norms[norms == 0] = 1.0
    normalised = matrix / norms

    # --- Step 3: Apply weights ---
    w = weights.as_array()
    weighted = normalised * w

    # --- Step 4: Determine ideal best and worst ---
    ideal_best = np.zeros(5)
    ideal_worst = np.zeros(5)

    for j in range(5):
        if j in _BENEFIT_CRITERIA:
            ideal_best[j] = np.max(weighted[:, j])
            ideal_worst[j] = np.min(weighted[:, j])
        else:
            ideal_best[j] = np.min(weighted[:, j])
            ideal_worst[j] = np.max(weighted[:, j])

    # --- Step 5: Calculate distances ---
    dist_to_best = np.sqrt(np.sum((weighted - ideal_best) ** 2, axis=1))
    dist_to_worst = np.sqrt(np.sum((weighted - ideal_worst) ** 2, axis=1))

    # --- Step 6: Calculate relative closeness ---
    denominator = dist_to_best + dist_to_worst
    # Avoid division by zero
    denominator[denominator == 0] = 1.0
    scores = dist_to_worst / denominator

    return {
        candidates[i].candidate_model: round(float(scores[i]), 4)
        for i in range(n)
    }
