"""
Staxx Intelligence — Shadow Eval Database Queries

All write and read operations for shadow evaluation data.
Handles idempotent inserts, progress upserts, and read queries
for the scoring engine and dashboard.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shadow_eval.db.models import ShadowEvalProgress, ShadowEvalRun

logger = logging.getLogger(__name__)

# Minimum valid runs required for statistical significance
MIN_VALID_RUNS = 20


# ---------------------------------------------------------------------------
# Write: Insert eval run + update progress
# ---------------------------------------------------------------------------


async def insert_eval_run(
    session: AsyncSession,
    *,
    org_id: UUID,
    task_type: str,
    original_model: str,
    candidate_model: str,
    prompt_hash: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    latency_ms: Optional[int] = None,
    cost_usd: Optional[float] = None,
    json_valid: Optional[bool] = None,
    output_empty: bool = False,
    output_truncated: bool = False,
    error: Optional[str] = None,
    s3_output_key: Optional[str] = None,
) -> Optional[ShadowEvalRun]:
    """
    Insert a shadow eval run and update the progress tracker.

    Idempotent: if a run with the same (org_id, candidate_model, prompt_hash)
    already exists, the insert is skipped and None is returned.

    Returns:
        The inserted ``ShadowEvalRun``, or None if a duplicate was skipped.
    """
    # Check for existing run (idempotency via unique index)
    existing = await session.execute(
        select(ShadowEvalRun.id).where(
            ShadowEvalRun.org_id == org_id,
            ShadowEvalRun.candidate_model == candidate_model,
            ShadowEvalRun.prompt_hash == prompt_hash,
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.debug(
            "Duplicate shadow eval skipped: org=%s candidate=%s hash=%s",
            org_id, candidate_model, prompt_hash,
        )
        return None

    # Determine if the run is "valid" (no error, not empty, not truncated)
    is_valid = (
        error is None
        and not output_empty
        and not output_truncated
        and (json_valid is not False)  # None (not a JSON task) counts as valid
    )

    # Insert the run
    run = ShadowEvalRun(
        org_id=org_id,
        task_type=task_type,
        original_model=original_model,
        candidate_model=candidate_model,
        prompt_hash=prompt_hash,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        json_valid=json_valid,
        output_empty=output_empty,
        output_truncated=output_truncated,
        error=error,
        s3_output_key=s3_output_key,
    )
    session.add(run)

    # Upsert progress tracker
    valid_increment = 1 if is_valid else 0
    await session.execute(
        text("""
            INSERT INTO shadow_eval_progress
                (org_id, task_type, original_model, candidate_model,
                 total_runs, valid_runs, last_run_at)
            VALUES
                (:org_id, :task_type, :original_model, :candidate_model,
                 1, :valid_inc, :now)
            ON CONFLICT (org_id, task_type, original_model, candidate_model)
            DO UPDATE SET
                total_runs  = shadow_eval_progress.total_runs + 1,
                valid_runs  = shadow_eval_progress.valid_runs + :valid_inc,
                last_run_at = :now
        """),
        {
            "org_id": str(org_id),
            "task_type": task_type,
            "original_model": original_model,
            "candidate_model": candidate_model,
            "valid_inc": valid_increment,
            "now": datetime.now(timezone.utc),
        },
    )

    await session.commit()
    await session.refresh(run)

    logger.info(
        "Shadow eval run saved: org=%s %s → %s task=%s valid=%s",
        org_id, original_model, candidate_model, task_type, is_valid,
    )
    return run


# ---------------------------------------------------------------------------
# Read: Check if this prompt was already evaluated
# ---------------------------------------------------------------------------


async def is_prompt_evaluated(
    session: AsyncSession,
    org_id: UUID,
    candidate_model: str,
    prompt_hash: str,
) -> bool:
    """Return True if this (org, candidate, prompt_hash) combo exists."""
    result = await session.execute(
        select(ShadowEvalRun.id).where(
            ShadowEvalRun.org_id == org_id,
            ShadowEvalRun.candidate_model == candidate_model,
            ShadowEvalRun.prompt_hash == prompt_hash,
        )
    )
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Read: Get progress for an org
# ---------------------------------------------------------------------------


async def get_eval_progress(
    session: AsyncSession,
    org_id: UUID,
    task_type: Optional[str] = None,
    original_model: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Get shadow eval progress for an organisation.

    Returns a list of progress records with a ``status`` field:
    'sufficient' if valid_runs >= 20, else 'insufficient'.
    """
    query = select(ShadowEvalProgress).where(
        ShadowEvalProgress.org_id == org_id
    )
    if task_type:
        query = query.where(ShadowEvalProgress.task_type == task_type)
    if original_model:
        query = query.where(ShadowEvalProgress.original_model == original_model)

    result = await session.execute(query)
    rows = result.scalars().all()

    return [
        {
            "org_id": str(row.org_id),
            "task_type": row.task_type,
            "original_model": row.original_model,
            "candidate_model": row.candidate_model,
            "total_runs": row.total_runs,
            "valid_runs": row.valid_runs,
            "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
            "status": "sufficient" if row.valid_runs >= MIN_VALID_RUNS else "insufficient",
            "runs_needed": max(0, MIN_VALID_RUNS - row.valid_runs),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Read: Get eval runs for scoring
# ---------------------------------------------------------------------------


async def get_eval_runs_for_scoring(
    session: AsyncSession,
    org_id: UUID,
    task_type: str,
    original_model: str,
    candidate_model: str,
) -> list[ShadowEvalRun]:
    """
    Retrieve all valid (non-error) shadow eval runs for a specific
    model swap combination.  Used by the Scoring Engine.
    """
    result = await session.execute(
        select(ShadowEvalRun).where(
            ShadowEvalRun.org_id == org_id,
            ShadowEvalRun.task_type == task_type,
            ShadowEvalRun.original_model == original_model,
            ShadowEvalRun.candidate_model == candidate_model,
            ShadowEvalRun.error.is_(None),
            ShadowEvalRun.output_empty.is_(False),
        ).order_by(ShadowEvalRun.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Read: Check what prompts have already been evaluated
# ---------------------------------------------------------------------------


async def get_evaluated_prompt_hashes(
    session: AsyncSession,
    org_id: UUID,
    candidate_model: str,
    limit: int = 10000,
) -> set[str]:
    """
    Return the set of prompt hashes already evaluated for a given
    (org_id, candidate_model) pair.  Used for dedup before dispatch.
    """
    result = await session.execute(
        select(ShadowEvalRun.prompt_hash).where(
            ShadowEvalRun.org_id == org_id,
            ShadowEvalRun.candidate_model == candidate_model,
        ).limit(limit)
    )
    return {row[0] for row in result.all()}
