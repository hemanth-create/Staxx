"""
Staxx Intelligence — Cost Metrics Celery Worker

Consumes telemetry events from Redis Stream ``staxx:telemetry``,
calculates the cost of each LLM API call, persists the raw event
to the ``cost_events`` hypertable, and updates the ``cost_aggregates``
hourly rollup table in real-time.

Usage (start the worker):
    celery -A cost_engine.worker worker \
        --loglevel=info --queues=cost_metrics \
        --concurrency=4

Usage (start the Redis Stream consumer loop):
    python -m cost_engine.worker
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

import redis
from celery import Celery
from sqlalchemy import text

from cost_engine.calculator import calculate_cost
from cost_engine.db.models import AsyncSessionLocal, CostEvent, CostAggregate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery app
# ---------------------------------------------------------------------------

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_CELERY_BROKER = os.getenv("CELERY_BROKER_URL", _REDIS_URL)
_CELERY_BACKEND = os.getenv("CELERY_RESULT_BACKEND", _REDIS_URL)

celery_app = Celery(
    "cost_engine",
    broker=_CELERY_BROKER,
    backend=_CELERY_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "cost_engine.worker.process_telemetry_event": {"queue": "cost_metrics"},
    },
)

# ---------------------------------------------------------------------------
# Redis Stream settings
# ---------------------------------------------------------------------------

_STREAM_KEY = os.getenv("TELEMETRY_STREAM_KEY", "staxx:telemetry")
_CONSUMER_GROUP = os.getenv("TELEMETRY_CONSUMER_GROUP", "cost_engine_workers")
_CONSUMER_NAME = os.getenv("TELEMETRY_CONSUMER_NAME", f"worker-{os.getpid()}")
_BATCH_SIZE = int(os.getenv("TELEMETRY_BATCH_SIZE", "10"))
_BLOCK_MS = int(os.getenv("TELEMETRY_BLOCK_MS", "5000"))

# ---------------------------------------------------------------------------
# Async persistence helpers
# ---------------------------------------------------------------------------


def _truncate_hour(dt: datetime) -> datetime:
    """Truncate a datetime to the start of the hour."""
    return dt.replace(minute=0, second=0, microsecond=0)


async def _persist_cost_event(payload: dict[str, Any]) -> None:
    """
    Process a single telemetry event:
    1. Calculate cost from the pricing catalog.
    2. Insert a ``CostEvent`` row (hypertable).
    3. Upsert the ``CostAggregate`` hourly rollup row.
    """
    model = payload.get("model", "unknown")
    org_id_raw = payload.get("org_id")
    input_tokens = payload.get("input_tokens")
    output_tokens = payload.get("output_tokens")
    input_text = payload.get("prompt", payload.get("input_text", ""))
    output_text = payload.get("completion", payload.get("output_text", ""))
    task_type = payload.get("task_type", "unclassified")
    latency_ms = payload.get("latency_ms")
    status = payload.get("status", "success")
    complexity = payload.get("complexity")
    timestamp_raw = payload.get("timestamp")

    # --- Resolve org_id -------------------------------------------------------
    if org_id_raw:
        try:
            org_id = uuid.UUID(str(org_id_raw))
        except ValueError:
            logger.error("Invalid org_id '%s' — skipping event", org_id_raw)
            return
    else:
        # Default org for events missing org_id (e.g. proxy traffic before onboarding)
        org_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    # --- Resolve timestamp ----------------------------------------------------
    if timestamp_raw:
        try:
            event_time = datetime.fromisoformat(str(timestamp_raw))
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            event_time = datetime.now(timezone.utc)
    else:
        event_time = datetime.now(timezone.utc)

    # --- Calculate cost -------------------------------------------------------
    cost_result = calculate_cost(
        model_id=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_text=input_text,
        output_text=output_text,
        org_id=str(org_id),
    )

    # --- Persist to database --------------------------------------------------
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Insert raw cost event
            event = CostEvent(
                id=uuid.uuid4(),
                time=event_time,
                org_id=org_id,
                model=cost_result.model_canonical,
                provider=cost_result.provider,
                task_type=task_type,
                input_tokens=cost_result.input_tokens_used,
                output_tokens=cost_result.output_tokens_used,
                cost_usd=cost_result.final_cost_usd,
                latency_ms=int(latency_ms) if latency_ms is not None else None,
                status=status,
                complexity=float(complexity) if complexity is not None else None,
            )
            session.add(event)

            # 2. Upsert hourly aggregate
            bucket = _truncate_hour(event_time)
            latency_val = int(latency_ms) if latency_ms is not None else None

            await session.execute(
                text("""
                    INSERT INTO cost_aggregates
                        (bucket, org_id, model, task_type,
                         call_count, total_cost,
                         total_input_tokens, total_output_tokens,
                         avg_latency, p95_latency)
                    VALUES
                        (:bucket, :org_id, :model, :task_type,
                         1, :cost,
                         :input_tokens, :output_tokens,
                         :latency, :latency)
                    ON CONFLICT (bucket, org_id, model, task_type)
                    DO UPDATE SET
                        call_count          = cost_aggregates.call_count + 1,
                        total_cost          = cost_aggregates.total_cost + EXCLUDED.total_cost,
                        total_input_tokens  = cost_aggregates.total_input_tokens + EXCLUDED.total_input_tokens,
                        total_output_tokens = cost_aggregates.total_output_tokens + EXCLUDED.total_output_tokens,
                        avg_latency         = CASE
                            WHEN EXCLUDED.avg_latency IS NOT NULL THEN
                                (cost_aggregates.avg_latency * cost_aggregates.call_count + EXCLUDED.avg_latency)
                                / (cost_aggregates.call_count + 1)
                            ELSE cost_aggregates.avg_latency
                        END
                """),
                {
                    "bucket": bucket,
                    "org_id": str(org_id),
                    "model": cost_result.model_canonical,
                    "task_type": task_type,
                    "cost": cost_result.final_cost_usd,
                    "input_tokens": cost_result.input_tokens_used,
                    "output_tokens": cost_result.output_tokens_used,
                    "latency": latency_val,
                },
            )

    logger.info(
        "Persisted cost event: org=%s model=%s task=%s cost=$%.6f tokens=%d/%d",
        org_id,
        cost_result.model_canonical,
        task_type,
        cost_result.final_cost_usd,
        cost_result.input_tokens_used,
        cost_result.output_tokens_used,
    )


# ---------------------------------------------------------------------------
# Celery task — process a single event (invoked when using Celery dispatch)
# ---------------------------------------------------------------------------


@celery_app.task(
    name="cost_engine.worker.process_telemetry_event",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def process_telemetry_event(self, payload: dict[str, Any]) -> dict[str, str]:
    """
    Celery task entry-point.  Wraps the async persistence logic.
    Retries up to 3 times on transient failures.
    """
    try:
        asyncio.run(_persist_cost_event(payload))
        return {"status": "ok"}
    except Exception as exc:
        logger.exception("Failed to process telemetry event: %s", exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Redis Stream consumer loop — direct stream consumption (alternative to
# having the proxy/SDK push into Celery).  Run with:
#     python -m cost_engine.worker
# ---------------------------------------------------------------------------

_shutdown = False


def _handle_signal(signum: int, _frame: Any) -> None:
    global _shutdown
    logger.info("Received signal %d — shutting down stream consumer...", signum)
    _shutdown = True


def run_stream_consumer() -> None:
    """
    Blocking loop that reads from Redis Stream ``staxx:telemetry``
    and dispatches each message through the Celery task (or processes
    inline if ``INLINE_PROCESSING=1``).
    """
    global _shutdown

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    inline = os.getenv("INLINE_PROCESSING", "0") == "1"

    r = redis.Redis.from_url(_REDIS_URL, decode_responses=True)

    # Ensure consumer group exists
    try:
        r.xgroup_create(_STREAM_KEY, _CONSUMER_GROUP, id="0", mkstream=True)
        logger.info("Created consumer group '%s' on stream '%s'", _CONSUMER_GROUP, _STREAM_KEY)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
        logger.debug("Consumer group '%s' already exists", _CONSUMER_GROUP)

    logger.info(
        "Stream consumer started: stream=%s group=%s consumer=%s batch=%d block=%dms inline=%s",
        _STREAM_KEY,
        _CONSUMER_GROUP,
        _CONSUMER_NAME,
        _BATCH_SIZE,
        _BLOCK_MS,
        inline,
    )

    while not _shutdown:
        try:
            messages = r.xreadgroup(
                groupname=_CONSUMER_GROUP,
                consumername=_CONSUMER_NAME,
                streams={_STREAM_KEY: ">"},
                count=_BATCH_SIZE,
                block=_BLOCK_MS,
            )
        except redis.ConnectionError:
            logger.warning("Redis connection lost — retrying in 2s...")
            import time
            time.sleep(2)
            continue

        if not messages:
            continue

        for _stream_name, entries in messages:
            for msg_id, fields in entries:
                try:
                    # The telemetry event may be stored as a single JSON
                    # blob in a "data" field, or as individual fields.
                    if "data" in fields:
                        payload = json.loads(fields["data"])
                    else:
                        payload = dict(fields)

                    if inline:
                        asyncio.run(_persist_cost_event(payload))
                    else:
                        process_telemetry_event.delay(payload)

                    # Acknowledge the message
                    r.xack(_STREAM_KEY, _CONSUMER_GROUP, msg_id)

                except Exception:
                    logger.exception("Failed to handle message %s", msg_id)

    logger.info("Stream consumer stopped.")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_stream_consumer()
