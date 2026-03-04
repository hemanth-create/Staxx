"""
Staxx Intelligence — Scoring Engine Pydantic Schemas

Output models for the scoring pipeline. All results are serialised
through these schemas for API consumption and dashboard rendering.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ModelScore(BaseModel):
    """Score card for a single candidate model."""

    candidate_model: str
    sample_size: int = Field(ge=0, description="Number of valid shadow eval runs")

    # --- Cost ---
    cost_savings_monthly_usd: float = Field(
        description="Projected monthly savings in USD"
    )
    cost_savings_ci_95: tuple[float, float] = Field(
        description="95% bootstrap CI on monthly savings (lower, upper)"
    )

    # --- Latency ---
    latency_p50_ms: float = Field(description="Candidate p50 latency in ms")
    latency_p95_ms: float = Field(description="Candidate p95 latency in ms")
    latency_p99_ms: float = Field(description="Candidate p99 latency in ms")
    latency_delta_pct: float = Field(
        description="Latency change vs original (%); negative = faster"
    )

    # --- Quality ---
    json_validity_rate: Optional[float] = Field(
        None, description="Fraction of outputs passing JSON validation (None if N/A)"
    )
    error_rate: float = Field(ge=0, le=1, description="Fraction of runs with errors")

    # --- Consistency ---
    output_consistency_cv: float = Field(
        description="Coefficient of variation of output token lengths"
    )
    output_length_ratio: float = Field(
        description="Avg candidate output tokens / avg original output tokens"
    )

    # --- Composite scores ---
    topsis_score: float = Field(
        ge=0.0, le=1.0, description="TOPSIS multi-criteria score"
    )
    is_pareto_optimal: bool = Field(
        description="True if not dominated on any metric pair"
    )
    swap_confidence: int = Field(
        ge=0, le=100, description="Overall swap confidence (0–100)"
    )
    swap_recommendation: str = Field(
        description="STRONG_YES | YES | MAYBE | NO | INSUFFICIENT_DATA"
    )


class ScoringResult(BaseModel):
    """Full scoring output for one (org, task, original_model) combination."""

    org_id: str
    task_type: str
    original_model: str
    original_monthly_cost: float = Field(
        description="Estimated current monthly spend on the original model"
    )
    candidates: list[ModelScore] = Field(default_factory=list)
    best_candidate: Optional[str] = Field(
        None,
        description="Candidate with highest swap_confidence ≥ YES, or None",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class InsufficientDataResult(BaseModel):
    """Returned when there are fewer than 20 valid runs."""

    org_id: str
    task_type: str
    original_model: str
    candidate_model: str
    status: str = "insufficient_data"
    current_count: int
    required_count: int = 20
