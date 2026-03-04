"""
Staxx Intelligence — Shadow Evaluator (Celery Worker)

Executes a single shadow evaluation: replays one prompt against
one candidate model, validates the output, stores it in S3,
and persists the result + progress to PostgreSQL.

Usage:
    celery -A shadow_eval.evaluator worker \
        --loglevel=info --queues=shadow_eval \
        --concurrency=8
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import uuid
from typing import Any, Optional

from celery import Celery

from cost_engine.calculator import calculate_cost
from shadow_eval.adapters import AdapterRequest, get_adapter
from shadow_eval.db.models import AsyncSessionLocal
from shadow_eval.db.queries import insert_eval_run, is_prompt_evaluated
from shadow_eval.storage import get_storage
from shadow_eval.validators import validate_output

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery app
# ---------------------------------------------------------------------------

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "shadow_eval",
    broker=os.getenv("CELERY_BROKER_URL", _REDIS_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", _REDIS_URL),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "shadow_eval.evaluator.run_shadow_eval": {"queue": "shadow_eval"},
    },
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def compute_prompt_hash(messages: list[dict[str, str]]) -> str:
    """SHA-256 hash of the prompt messages for dedup."""
    content = "|".join(
        f"{m.get('role', '')}:{m.get('content', '')}" for m in messages
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Core evaluation logic (async)
# ---------------------------------------------------------------------------


async def _run_shadow_eval_async(
    org_id: str,
    task_type: str,
    original_model: str,
    candidate_model: str,
    messages: list[dict[str, str]],
    prompt_hash: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """
    Execute a single shadow evaluation:
    1. Check idempotency (skip if already evaluated)
    2. Call the candidate model via the unified adapter
    3. Validate the output
    4. Store full output in S3
    5. Persist results to PostgreSQL
    6. Update progress tracker
    """
    org_uuid = uuid.UUID(org_id)

    # Compute or use provided prompt hash
    if not prompt_hash:
        prompt_hash = compute_prompt_hash(messages)

    # --- 1. Idempotency check ------------------------------------------------
    async with AsyncSessionLocal() as session:
        if await is_prompt_evaluated(session, org_uuid, candidate_model, prompt_hash):
            logger.debug(
                "Already evaluated: %s → %s hash=%s — skipping",
                original_model, candidate_model, prompt_hash[:12],
            )
            return {"status": "skipped", "reason": "already_evaluated"}

    # --- 2. Call candidate model via adapter ----------------------------------
    adapter = get_adapter(candidate_model)
    if adapter is None:
        logger.error("No adapter for candidate model '%s'", candidate_model)
        return {"status": "error", "reason": f"no_adapter_for_{candidate_model}"}

    request = AdapterRequest(
        model=candidate_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=float(os.getenv("SHADOW_EVAL_TIMEOUT", "30")),
    )

    response = await adapter.invoke(request)

    # --- 3. Validate output ---------------------------------------------------
    finish_reason = response.raw_response.get("choices", [{}])[0].get("finish_reason") if response.raw_response else None
    validation = validate_output(
        text_output=response.text_output,
        task_type=task_type,
        finish_reason=finish_reason,
        max_tokens=max_tokens,
    )

    # --- 4. Calculate cost of the shadow call ---------------------------------
    cost_result = calculate_cost(
        model_id=candidate_model,
        input_tokens=response.input_tokens or None,
        output_tokens=response.output_tokens or None,
    )

    # --- 5. Store full output in S3 -------------------------------------------
    s3_key = ""
    if response.text_output:
        try:
            storage = get_storage()
            s3_key = storage.store_output(
                org_id=org_id,
                task_type=task_type,
                original_model=original_model,
                candidate_model=candidate_model,
                prompt_hash=prompt_hash,
                output_text=response.text_output,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "latency_ms": response.latency_ms,
                    "cost_usd": cost_result.final_cost_usd,
                    "json_valid": validation.json_valid,
                    "output_empty": validation.output_empty,
                    "output_truncated": validation.output_truncated,
                    "error": response.error,
                },
            )
        except Exception as exc:
            logger.warning("S3 storage failed (non-fatal): %s", exc)
            s3_key = ""

    # --- 6. Persist to database -----------------------------------------------
    async with AsyncSessionLocal() as session:
        run = await insert_eval_run(
            session,
            org_id=org_uuid,
            task_type=task_type,
            original_model=original_model,
            candidate_model=candidate_model,
            prompt_hash=prompt_hash,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
            cost_usd=cost_result.final_cost_usd,
            json_valid=validation.json_valid,
            output_empty=validation.output_empty,
            output_truncated=validation.output_truncated,
            error=response.error,
            s3_output_key=s3_key,
        )

    if run is None:
        return {"status": "skipped", "reason": "duplicate_insert"}

    return {
        "status": "completed",
        "run_id": str(run.id),
        "candidate_model": candidate_model,
        "latency_ms": response.latency_ms,
        "cost_usd": cost_result.final_cost_usd,
        "valid": validation.is_valid,
        "error": response.error,
    }


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@celery_app.task(
    name="shadow_eval.evaluator.run_shadow_eval",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
)
def run_shadow_eval(
    self,
    org_id: str,
    task_type: str,
    original_model: str,
    candidate_model: str,
    messages: list[dict[str, str]],
    prompt_hash: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """
    Celery task entry-point for a single shadow evaluation.

    Args:
        org_id: Organisation UUID string.
        task_type: Classified task type.
        original_model: The production model.
        candidate_model: The cheaper candidate model.
        messages: OpenAI-format messages list.
        prompt_hash: Pre-computed SHA-256 hash (optional).
        max_tokens: Max output tokens for the candidate call.
        temperature: Temperature for the candidate call.
    """
    try:
        result = asyncio.run(
            _run_shadow_eval_async(
                org_id=org_id,
                task_type=task_type,
                original_model=original_model,
                candidate_model=candidate_model,
                messages=messages,
                prompt_hash=prompt_hash,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        )
        return result
    except Exception as exc:
        logger.exception(
            "Shadow eval failed: %s → %s (org=%s): %s",
            original_model, candidate_model, org_id, exc,
        )
        raise self.retry(exc=exc)
