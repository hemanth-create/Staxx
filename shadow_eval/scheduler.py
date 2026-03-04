"""
Staxx Intelligence — Shadow Eval Scheduler (Celery Beat)

Periodically selects prompts eligible for shadow evaluation and
dispatches evaluation tasks to Celery workers.

Schedule: Runs every 15 minutes by default (configurable via
SHADOW_EVAL_INTERVAL_SECONDS env var).

Selection logic:
  1. Query recent cost_events for distinct (org, model, task_type) combos
  2. For each combo, select a random sample of prompts
  3. Filter out: already evaluated, PII-containing, opted-out orgs
  4. For each eligible prompt × candidate model, dispatch a shadow eval task

Usage:
    celery -A shadow_eval.scheduler beat --loglevel=info
    celery -A shadow_eval.scheduler worker --queues=shadow_scheduler --concurrency=2
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from typing import Any, Optional
from uuid import UUID

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import text

from shadow_eval.candidate_selector import select_candidates
from shadow_eval.db.models import AsyncSessionLocal
from shadow_eval.db.queries import get_evaluated_prompt_hashes
from shadow_eval.evaluator import celery_app as evaluator_celery, compute_prompt_hash
from shadow_eval.validators import check_pii

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery app (reuses the evaluator's Celery instance for shared broker)
# ---------------------------------------------------------------------------

celery_app = evaluator_celery

# Schedule interval in seconds (default: 15 minutes)
_INTERVAL = int(os.getenv("SHADOW_EVAL_INTERVAL_SECONDS", "900"))

# Maximum prompts to sample per (org, model, task_type) combo per cycle
_SAMPLE_SIZE = int(os.getenv("SHADOW_EVAL_SAMPLE_SIZE", "10"))

# Lookback window for selecting recent prompts (hours)
_LOOKBACK_HOURS = int(os.getenv("SHADOW_EVAL_LOOKBACK_HOURS", "24"))

# Orgs opted out of shadow evaluation (comma-separated UUIDs)
_OPTED_OUT_ORGS: set[str] = set(
    filter(None, os.getenv("SHADOW_EVAL_OPTED_OUT_ORGS", "").split(","))
)

# S3 key prefix for retrieving stored prompts
_PROMPT_S3_PREFIX = os.getenv("PROMPT_S3_PREFIX", "prompts/")


# ---------------------------------------------------------------------------
# Configure Celery beat schedule
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    **celery_app.conf.get("beat_schedule", {}),
    "shadow-eval-select-prompts": {
        "task": "shadow_eval.scheduler.select_and_dispatch",
        "schedule": _INTERVAL,
        "options": {"queue": "shadow_scheduler"},
    },
}


# ---------------------------------------------------------------------------
# Core scheduling logic (async)
# ---------------------------------------------------------------------------


async def _get_eligible_combos(
    lookback_hours: int = _LOOKBACK_HOURS,
) -> list[dict[str, Any]]:
    """
    Query cost_events for distinct (org_id, model, task_type) combos
    with recent activity, to determine which prompts need shadow evals.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    org_id::text,
                    model,
                    task_type,
                    COUNT(*) AS recent_calls
                FROM cost_events
                WHERE time >= NOW() - INTERVAL ':hours hours'
                  AND status = 'success'
                GROUP BY org_id, model, task_type
                HAVING COUNT(*) >= 5
                ORDER BY recent_calls DESC
                LIMIT 100
            """.replace(":hours", str(lookback_hours)))
        )
        return [dict(r._mapping) for r in result.all()]


async def _sample_prompts_for_combo(
    org_id: str,
    model: str,
    task_type: str,
    sample_size: int = _SAMPLE_SIZE,
) -> list[dict[str, Any]]:
    """
    Get a random sample of recent prompts for a specific combo.

    Retrieves prompt data from cost_events. In production, the full
    prompt text would be fetched from S3 using the stored reference.
    For now, we retrieve what's available directly.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id::text,
                    org_id::text,
                    model,
                    task_type,
                    input_tokens,
                    output_tokens,
                    time
                FROM cost_events
                WHERE org_id = :org_id
                  AND model = :model
                  AND task_type = :task_type
                  AND status = 'success'
                  AND time >= NOW() - INTERVAL '48 hours'
                ORDER BY RANDOM()
                LIMIT :limit
            """),
            {
                "org_id": org_id,
                "model": model,
                "task_type": task_type,
                "limit": sample_size * 3,  # Over-sample for filtering
            },
        )
        return [dict(r._mapping) for r in result.all()]


async def _fetch_prompt_messages(
    org_id: str,
    event_id: str,
) -> Optional[list[dict[str, str]]]:
    """
    Fetch the original prompt messages for a cost event.

    Attempts to retrieve from S3 storage. Returns None if not available.
    """
    try:
        from shadow_eval.storage import get_storage
        storage = get_storage()
        s3_key = f"{_PROMPT_S3_PREFIX}{org_id}/{event_id}.json"
        data = storage.retrieve_output(s3_key)
        if data and "messages" in data:
            return data["messages"]
        return None
    except Exception as exc:
        logger.debug("Could not fetch prompt from S3 for event %s: %s", event_id, exc)
        return None


async def _select_and_dispatch_async() -> dict[str, Any]:
    """
    Main scheduling logic:
    1. Find active (org, model, task_type) combos
    2. Sample prompts for each
    3. Filter out PII and already-evaluated prompts
    4. Select candidate models
    5. Dispatch shadow eval tasks
    """
    stats = {
        "combos_found": 0,
        "prompts_sampled": 0,
        "prompts_filtered_pii": 0,
        "prompts_filtered_dup": 0,
        "prompts_filtered_opted_out": 0,
        "tasks_dispatched": 0,
        "candidates_per_combo": {},
    }

    # 1. Get eligible combos
    combos = await _get_eligible_combos()
    stats["combos_found"] = len(combos)

    if not combos:
        logger.info("No eligible combos for shadow evaluation")
        return stats

    for combo in combos:
        org_id = combo["org_id"]
        model = combo["model"]
        task_type = combo["task_type"]

        # Skip opted-out orgs
        if org_id in _OPTED_OUT_ORGS:
            stats["prompts_filtered_opted_out"] += 1
            continue

        # 2. Select candidate models (cheaper alternatives)
        candidates = select_candidates(
            original_model=model,
            task_type=task_type,
            max_candidates=5,
        )

        if not candidates:
            logger.debug("No cheaper candidates for %s on task '%s'", model, task_type)
            continue

        stats["candidates_per_combo"][f"{model}/{task_type}"] = len(candidates)

        # 3. Sample prompts
        prompts = await _sample_prompts_for_combo(org_id, model, task_type)
        stats["prompts_sampled"] += len(prompts)

        if not prompts:
            continue

        # 4. For each candidate, get already-evaluated hashes
        for candidate in candidates:
            async with AsyncSessionLocal() as session:
                evaluated_hashes = await get_evaluated_prompt_hashes(
                    session, UUID(org_id), candidate.canonical_name
                )

            dispatched_for_candidate = 0

            for prompt_event in prompts:
                # Stop after sample_size successful dispatches per candidate
                if dispatched_for_candidate >= _SAMPLE_SIZE:
                    break

                event_id = prompt_event["id"]

                # Try to fetch the actual prompt messages from S3
                messages = await _fetch_prompt_messages(org_id, event_id)

                if messages is None:
                    # If we can't fetch the prompt, create a placeholder
                    # that indicates the prompt needs manual retrieval
                    # In production, this would be a hard skip
                    logger.debug(
                        "No prompt text available for event %s — skipping",
                        event_id,
                    )
                    continue

                # Compute prompt hash for dedup
                prompt_hash = compute_prompt_hash(messages)

                # Skip already evaluated
                if prompt_hash in evaluated_hashes:
                    stats["prompts_filtered_dup"] += 1
                    continue

                # PII check on concatenated message content
                full_text = " ".join(m.get("content", "") for m in messages)
                pii_result = check_pii(full_text)
                if pii_result.contains_pii:
                    stats["prompts_filtered_pii"] += 1
                    logger.debug(
                        "PII detected in prompt %s: %s — skipping",
                        event_id, pii_result.matched_types,
                    )
                    continue

                # 5. Dispatch shadow eval task
                evaluator_celery.send_task(
                    "shadow_eval.evaluator.run_shadow_eval",
                    kwargs={
                        "org_id": org_id,
                        "task_type": task_type,
                        "original_model": model,
                        "candidate_model": candidate.canonical_name,
                        "messages": messages,
                        "prompt_hash": prompt_hash,
                    },
                    queue="shadow_eval",
                )

                dispatched_for_candidate += 1
                stats["tasks_dispatched"] += 1

    logger.info(
        "Shadow eval scheduling complete: %d combos, %d tasks dispatched, "
        "%d PII filtered, %d duplicates skipped",
        stats["combos_found"],
        stats["tasks_dispatched"],
        stats["prompts_filtered_pii"],
        stats["prompts_filtered_dup"],
    )
    return stats


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@celery_app.task(
    name="shadow_eval.scheduler.select_and_dispatch",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def select_and_dispatch(self) -> dict[str, Any]:
    """
    Celery beat task: Select eligible prompts and dispatch
    shadow evaluation jobs to workers.
    """
    try:
        return asyncio.run(_select_and_dispatch_async())
    except Exception as exc:
        logger.exception("Shadow eval scheduling failed: %s", exc)
        raise self.retry(exc=exc)
