"""
Staxx Intelligence — Scoring Engine Orchestrator

Main ``score()`` function that:
  1. Loads shadow eval run data from the database
  2. Loads original model baseline data from cost_events
  3. Computes all metrics per candidate
  4. Runs TOPSIS ranking
  5. Detects Pareto frontier
  6. Calculates swap confidence
  7. Returns a typed ``ScoringResult``
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from scoring.confidence import compute_swap_confidence
from scoring.metrics import (
    OriginalModelData,
    RunData,
    compute_cost_savings,
    compute_error_rate,
    compute_json_validity_rate,
    compute_latency,
    compute_output_consistency_cv,
    compute_output_length_ratio,
)
from scoring.pareto import build_pareto_candidate, find_pareto_optimal
from scoring.schemas import InsufficientDataResult, ModelScore, ScoringResult
from scoring.topsis import TOPSISInput, TOPSISWeights, topsis_rank

logger = logging.getLogger(__name__)

# Minimum runs required for scoring
MIN_RUNS = 20


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


async def _load_candidate_runs(
    session: AsyncSession,
    org_id: UUID,
    task_type: str,
    original_model: str,
    candidate_model: str,
) -> list[dict[str, Any]]:
    """Load shadow eval runs for a specific candidate combo."""
    result = await session.execute(
        text("""
            SELECT
                cost_usd,
                latency_ms,
                output_tokens,
                json_valid,
                error,
                output_empty,
                output_truncated
            FROM shadow_eval_runs
            WHERE org_id = :org_id
              AND task_type = :task_type
              AND original_model = :original_model
              AND candidate_model = :candidate_model
            ORDER BY created_at DESC
        """),
        {
            "org_id": str(org_id),
            "task_type": task_type,
            "original_model": original_model,
            "candidate_model": candidate_model,
        },
    )
    return [dict(r._mapping) for r in result.all()]


async def _load_original_baseline(
    session: AsyncSession,
    org_id: UUID,
    task_type: str,
    model: str,
) -> OriginalModelData:
    """
    Load baseline data for the original model from cost_events.

    Computes avg cost/latency/output_tokens and monthly volume
    from the last 30 days of production data.
    """
    result = await session.execute(
        text("""
            SELECT
                COALESCE(AVG(cost_usd), 0) AS avg_cost,
                COALESCE(AVG(latency_ms), 0) AS avg_latency,
                COALESCE(AVG(output_tokens), 0) AS avg_output_tokens,
                COUNT(*) AS total_calls,
                COALESCE(SUM(cost_usd), 0) AS total_cost
            FROM cost_events
            WHERE org_id = :org_id
              AND task_type = :task_type
              AND model = :model
              AND time >= NOW() - INTERVAL '30 days'
              AND status = 'success'
        """),
        {
            "org_id": str(org_id),
            "task_type": task_type,
            "model": model,
        },
    )
    row = result.mappings().first()

    if row is None or row["total_calls"] == 0:
        return OriginalModelData(
            avg_cost_per_call=0.0,
            avg_latency_ms=0.0,
            avg_output_tokens=0.0,
            monthly_call_volume=0,
            monthly_cost_usd=0.0,
            cost_per_call_array=np.array([]),
        )

    # Also load individual cost values for bootstrap CI
    cost_result = await session.execute(
        text("""
            SELECT cost_usd
            FROM cost_events
            WHERE org_id = :org_id
              AND task_type = :task_type
              AND model = :model
              AND time >= NOW() - INTERVAL '30 days'
              AND status = 'success'
            LIMIT 1000
        """),
        {
            "org_id": str(org_id),
            "task_type": task_type,
            "model": model,
        },
    )
    cost_values = np.array([r[0] for r in cost_result.all()], dtype=np.float64)

    return OriginalModelData(
        avg_cost_per_call=float(row["avg_cost"]),
        avg_latency_ms=float(row["avg_latency"]),
        avg_output_tokens=float(row["avg_output_tokens"]),
        monthly_call_volume=int(row["total_calls"]),
        monthly_cost_usd=float(row["total_cost"]),
        cost_per_call_array=cost_values,
    )


async def _get_candidate_models(
    session: AsyncSession,
    org_id: UUID,
    task_type: str,
    original_model: str,
) -> list[dict[str, Any]]:
    """Get all candidate models with their run counts."""
    result = await session.execute(
        text("""
            SELECT
                candidate_model,
                total_runs,
                valid_runs
            FROM shadow_eval_progress
            WHERE org_id = :org_id
              AND task_type = :task_type
              AND original_model = :original_model
        """),
        {
            "org_id": str(org_id),
            "task_type": task_type,
            "original_model": original_model,
        },
    )
    return [dict(r._mapping) for r in result.all()]


# ---------------------------------------------------------------------------
# Run data extraction
# ---------------------------------------------------------------------------


def _extract_run_data(runs: list[dict[str, Any]]) -> RunData:
    """Convert raw DB rows into numpy arrays for metric computation."""
    n = len(runs)
    if n == 0:
        return RunData(
            cost_usd=np.array([], dtype=np.float64),
            latency_ms=np.array([], dtype=np.float64),
            output_tokens=np.array([], dtype=np.float64),
            json_valid=np.array([], dtype=np.float64),
            has_json_data=False,
            errors=np.array([], dtype=bool),
            sample_size=0,
        )

    costs = np.array([r.get("cost_usd") or 0.0 for r in runs], dtype=np.float64)
    latencies = np.array([r.get("latency_ms") or 0 for r in runs], dtype=np.float64)
    output_tokens = np.array([r.get("output_tokens") or 0 for r in runs], dtype=np.float64)
    errors = np.array([r.get("error") is not None for r in runs], dtype=bool)

    # JSON validity: use NaN for non-JSON tasks (where json_valid is None)
    json_values = []
    has_json = False
    for r in runs:
        jv = r.get("json_valid")
        if jv is None:
            json_values.append(np.nan)
        else:
            json_values.append(1.0 if jv else 0.0)
            has_json = True

    json_valid = np.array(json_values, dtype=np.float64)

    return RunData(
        cost_usd=costs,
        latency_ms=latencies,
        output_tokens=output_tokens,
        json_valid=json_valid,
        has_json_data=has_json,
        errors=errors,
        sample_size=n,
    )


# ---------------------------------------------------------------------------
# Score a single candidate
# ---------------------------------------------------------------------------


def score_candidate(
    candidate_model: str,
    run_data: RunData,
    original: OriginalModelData,
    seed: Optional[int] = None,
) -> ModelScore:
    """
    Compute all metrics for a single candidate model.

    This function is pure computation — no I/O.
    """
    # Cost savings
    monthly_savings, cost_ci = compute_cost_savings(run_data, original, seed=seed)

    # Calculate savings percentage for TOPSIS/Pareto
    if original.monthly_cost_usd > 0:
        savings_pct = (monthly_savings / original.monthly_cost_usd) * 100
    else:
        savings_pct = 0.0

    # Latency
    latency = compute_latency(run_data, original)

    # Quality
    json_rate = compute_json_validity_rate(run_data)
    error_rate = compute_error_rate(run_data)

    # Consistency
    cv = compute_output_consistency_cv(run_data)
    length_ratio = compute_output_length_ratio(run_data, original)

    return ModelScore(
        candidate_model=candidate_model,
        sample_size=run_data.sample_size,
        cost_savings_monthly_usd=round(monthly_savings, 2),
        cost_savings_ci_95=(round(cost_ci.ci_lower, 2), round(cost_ci.ci_upper, 2)),
        latency_p50_ms=latency.p50_ms,
        latency_p95_ms=latency.p95_ms,
        latency_p99_ms=latency.p99_ms,
        latency_delta_pct=latency.delta_pct,
        json_validity_rate=round(json_rate, 4) if json_rate is not None else None,
        error_rate=round(error_rate, 4),
        output_consistency_cv=cv,
        output_length_ratio=length_ratio,
        # Placeholders — filled in by TOPSIS / Pareto / Confidence later
        topsis_score=0.0,
        is_pareto_optimal=False,
        swap_confidence=0,
        swap_recommendation="INSUFFICIENT_DATA",
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


async def score(
    session: AsyncSession,
    org_id: str,
    task_type: str,
    original_model: str,
    weights: Optional[TOPSISWeights] = None,
    seed: Optional[int] = None,
) -> ScoringResult | InsufficientDataResult:
    """
    Score all candidate models for a given (org, task, original_model).

    This is the main entry point of the Scoring Engine.

    Args:
        session: Async DB session.
        org_id: Organisation UUID string.
        task_type: Task type to score.
        original_model: The production model being evaluated.
        weights: Optional custom TOPSIS weights.
        seed: Optional RNG seed for reproducible bootstrap CIs.

    Returns:
        ``ScoringResult`` with all candidates scored, or
        ``InsufficientDataResult`` if there aren't enough runs.
    """
    org_uuid = UUID(org_id)

    # Load original model baseline
    original_data = await _load_original_baseline(
        session, org_uuid, task_type, original_model
    )

    # Get list of candidate models and their progress
    candidate_info = await _get_candidate_models(
        session, org_uuid, task_type, original_model
    )

    if not candidate_info:
        return ScoringResult(
            org_id=org_id,
            task_type=task_type,
            original_model=original_model,
            original_monthly_cost=original_data.monthly_cost_usd,
            candidates=[],
            best_candidate=None,
        )

    # Score each candidate
    scored_candidates: list[ModelScore] = []
    topsis_inputs: list[TOPSISInput] = []
    savings_pcts: dict[str, float] = {}

    for info in candidate_info:
        cand_model = info["candidate_model"]
        valid_runs = info.get("valid_runs", 0)

        # Load runs for this candidate
        runs = await _load_candidate_runs(
            session, org_uuid, task_type, original_model, cand_model
        )

        if len(runs) < MIN_RUNS:
            # Not enough data — skip this candidate but don't fail the whole query
            logger.info(
                "Insufficient data for %s → %s: %d/%d runs",
                original_model, cand_model, len(runs), MIN_RUNS,
            )
            continue

        run_data = _extract_run_data(runs)
        model_score = score_candidate(cand_model, run_data, original_data, seed=seed)

        # Calculate savings pct for TOPSIS / Pareto
        if original_data.monthly_cost_usd > 0:
            s_pct = (model_score.cost_savings_monthly_usd / original_data.monthly_cost_usd) * 100
        else:
            s_pct = 0.0
        savings_pcts[cand_model] = s_pct

        # Build TOPSIS input
        topsis_inputs.append(TOPSISInput(
            candidate_model=cand_model,
            cost_savings_pct=s_pct,
            latency_p95_ms=model_score.latency_p95_ms,
            quality_score=model_score.json_validity_rate if model_score.json_validity_rate is not None else 1.0,
            error_rate=model_score.error_rate,
            consistency_cv=model_score.output_consistency_cv,
        ))

        scored_candidates.append(model_score)

    if not scored_candidates:
        return ScoringResult(
            org_id=org_id,
            task_type=task_type,
            original_model=original_model,
            original_monthly_cost=original_data.monthly_cost_usd,
            candidates=[],
            best_candidate=None,
        )

    # --- TOPSIS ranking ---
    topsis_scores = topsis_rank(topsis_inputs, weights)

    # --- Pareto frontier ---
    pareto_candidates = [
        build_pareto_candidate(
            candidate_model=t.candidate_model,
            cost_savings_pct=t.cost_savings_pct,
            latency_p95_ms=t.latency_p95_ms,
            quality_score=t.quality_score,
            error_rate=t.error_rate,
            consistency_cv=t.consistency_cv,
        )
        for t in topsis_inputs
    ]
    pareto_set = find_pareto_optimal(pareto_candidates)

    # --- Swap confidence ---
    final_candidates: list[ModelScore] = []
    for ms in scored_candidates:
        t_score = topsis_scores.get(ms.candidate_model, 0.0)
        is_pareto = ms.candidate_model in pareto_set

        confidence, recommendation = compute_swap_confidence(
            cost_savings_monthly=ms.cost_savings_monthly_usd,
            cost_ci=type("CI", (), {
                "ci_lower": ms.cost_savings_ci_95[0],
                "ci_upper": ms.cost_savings_ci_95[1],
                "estimate": ms.cost_savings_monthly_usd,
            })(),
            error_rate=ms.error_rate,
            json_validity_rate=ms.json_validity_rate,
            latency_delta_pct=ms.latency_delta_pct,
            output_length_ratio=ms.output_length_ratio,
            sample_size=ms.sample_size,
            topsis_score=t_score,
        )

        # Create updated ModelScore with TOPSIS/Pareto/Confidence
        updated = ms.model_copy(update={
            "topsis_score": t_score,
            "is_pareto_optimal": is_pareto,
            "swap_confidence": confidence,
            "swap_recommendation": recommendation,
        })
        final_candidates.append(updated)

    # Sort by swap_confidence descending
    final_candidates.sort(key=lambda c: c.swap_confidence, reverse=True)

    # Determine best candidate (highest confidence with >= YES)
    best = None
    for c in final_candidates:
        if c.swap_recommendation in ("STRONG_YES", "YES"):
            best = c.candidate_model
            break

    return ScoringResult(
        org_id=org_id,
        task_type=task_type,
        original_model=original_model,
        original_monthly_cost=round(original_data.monthly_cost_usd, 2),
        candidates=final_candidates,
        best_candidate=best,
    )


# ---------------------------------------------------------------------------
# Pure computation (no DB) — for testing
# ---------------------------------------------------------------------------


def score_from_data(
    org_id: str,
    task_type: str,
    original_model: str,
    original_data: OriginalModelData,
    candidates_data: dict[str, list[dict[str, Any]]],
    weights: Optional[TOPSISWeights] = None,
    seed: Optional[int] = None,
) -> ScoringResult:
    """
    Score candidates from pre-loaded data (no database access).

    Useful for testing and batch processing.

    Args:
        org_id: Organisation UUID string.
        task_type: Task type.
        original_model: Production model.
        original_data: Pre-loaded original model baseline.
        candidates_data: Dict mapping candidate_model → list of run dicts.
        weights: Optional TOPSIS weights.
        seed: RNG seed for reproducibility.

    Returns:
        ``ScoringResult`` with all candidates scored.
    """
    scored_candidates: list[ModelScore] = []
    topsis_inputs: list[TOPSISInput] = []

    for cand_model, runs in candidates_data.items():
        if len(runs) < MIN_RUNS:
            continue

        run_data = _extract_run_data(runs)
        model_score = score_candidate(cand_model, run_data, original_data, seed=seed)

        if original_data.monthly_cost_usd > 0:
            s_pct = (model_score.cost_savings_monthly_usd / original_data.monthly_cost_usd) * 100
        else:
            s_pct = 0.0

        topsis_inputs.append(TOPSISInput(
            candidate_model=cand_model,
            cost_savings_pct=s_pct,
            latency_p95_ms=model_score.latency_p95_ms,
            quality_score=model_score.json_validity_rate if model_score.json_validity_rate is not None else 1.0,
            error_rate=model_score.error_rate,
            consistency_cv=model_score.output_consistency_cv,
        ))
        scored_candidates.append(model_score)

    if not scored_candidates:
        return ScoringResult(
            org_id=org_id,
            task_type=task_type,
            original_model=original_model,
            original_monthly_cost=original_data.monthly_cost_usd,
            candidates=[],
            best_candidate=None,
        )

    # TOPSIS
    topsis_scores = topsis_rank(topsis_inputs, weights)

    # Pareto
    pareto_candidates = [
        build_pareto_candidate(
            candidate_model=t.candidate_model,
            cost_savings_pct=t.cost_savings_pct,
            latency_p95_ms=t.latency_p95_ms,
            quality_score=t.quality_score,
            error_rate=t.error_rate,
            consistency_cv=t.consistency_cv,
        )
        for t in topsis_inputs
    ]
    pareto_set = find_pareto_optimal(pareto_candidates)

    # Confidence
    final: list[ModelScore] = []
    for ms in scored_candidates:
        t_score = topsis_scores.get(ms.candidate_model, 0.0)
        is_pareto = ms.candidate_model in pareto_set

        confidence, recommendation = compute_swap_confidence(
            cost_savings_monthly=ms.cost_savings_monthly_usd,
            cost_ci=type("CI", (), {
                "ci_lower": ms.cost_savings_ci_95[0],
                "ci_upper": ms.cost_savings_ci_95[1],
                "estimate": ms.cost_savings_monthly_usd,
            })(),
            error_rate=ms.error_rate,
            json_validity_rate=ms.json_validity_rate,
            latency_delta_pct=ms.latency_delta_pct,
            output_length_ratio=ms.output_length_ratio,
            sample_size=ms.sample_size,
            topsis_score=t_score,
        )

        updated = ms.model_copy(update={
            "topsis_score": t_score,
            "is_pareto_optimal": is_pareto,
            "swap_confidence": confidence,
            "swap_recommendation": recommendation,
        })
        final.append(updated)

    final.sort(key=lambda c: c.swap_confidence, reverse=True)

    best = None
    for c in final:
        if c.swap_recommendation in ("STRONG_YES", "YES"):
            best = c.candidate_model
            break

    return ScoringResult(
        org_id=org_id,
        task_type=task_type,
        original_model=original_model,
        original_monthly_cost=round(original_data.monthly_cost_usd, 2),
        candidates=final,
        best_candidate=best,
    )
