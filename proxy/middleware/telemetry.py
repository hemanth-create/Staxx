"""
Staxx Proxy Gateway — Async telemetry publisher.

Publishes telemetry events to a Redis Stream (``staxx:telemetry``) in a
fire-and-forget fashion.  If Redis is unreachable the event is appended to a
local JSONL fallback file so that **no customer request is ever affected**.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import orjson
import structlog
from redis.asyncio import Redis

from proxy.config import settings

logger = structlog.get_logger(__name__)

# Module-level Redis handle — set by ``init_telemetry`` during lifespan.
_redis: Redis | None = None
_fallback_path: Path = Path(settings.telemetry_fallback_path)


# ── lifecycle helpers ───────────────────────────────────────────────────
async def init_telemetry() -> None:
    """Create the module-level async Redis connection."""
    global _redis  # noqa: PLW0603
    _redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    try:
        await _redis.ping()
        logger.info("telemetry.redis_connected", url=settings.redis_url)
    except Exception:
        logger.warning(
            "telemetry.redis_unavailable_at_startup",
            url=settings.redis_url,
        )


async def close_telemetry() -> None:
    """Gracefully close the Redis connection."""
    global _redis  # noqa: PLW0603
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("telemetry.redis_closed")


# ── public API ──────────────────────────────────────────────────────────
def publish_telemetry_event(event: dict[str, Any]) -> None:
    """Schedule telemetry publishing as a background task.

    This function is **non-blocking** — it creates an ``asyncio.Task``
    and returns immediately so the HTTP response is never delayed.
    """
    asyncio.create_task(_safe_publish(event))


async def _safe_publish(event: dict[str, Any]) -> None:
    """Attempt to publish to Redis; fall back to local file on failure."""
    try:
        await _publish_to_redis(event)
    except Exception:
        logger.warning("telemetry.redis_publish_failed", exc_info=True)
        _write_fallback(event)


async def _publish_to_redis(event: dict[str, Any]) -> None:
    """XADD the event to the telemetry Redis Stream."""
    if _redis is None:
        raise RuntimeError("Redis handle not initialised")

    # Redis Streams require flat string values.  We serialise complex
    # sub-fields (request_body, response_body) as JSON strings.
    flat: dict[str, str] = {}
    for key, value in event.items():
        if isinstance(value, (dict, list)):
            flat[key] = orjson.dumps(value).decode()
        elif value is None:
            flat[key] = ""
        else:
            flat[key] = str(value)

    await _redis.xadd(
        settings.telemetry_stream,
        flat,
        maxlen=settings.telemetry_maxlen,
        approximate=True,
    )
    logger.debug(
        "telemetry.published",
        org_id=event.get("org_id"),
        model=event.get("model"),
    )


def _write_fallback(event: dict[str, Any]) -> None:
    """Append event as a JSON line to the local fallback file.

    This is a *synchronous* write but it only runs when Redis is down,
    which is an exceptional situation.  The file can be drained later
    by a recovery script.
    """
    try:
        _fallback_path.parent.mkdir(parents=True, exist_ok=True)
        with _fallback_path.open("ab") as fh:
            fh.write(orjson.dumps(event))
            fh.write(b"\n")
        logger.info("telemetry.fallback_written", path=str(_fallback_path))
    except Exception:
        # Last resort — just log it.  Never crash the proxy.
        logger.error("telemetry.fallback_write_failed", exc_info=True)


# ── helpers ─────────────────────────────────────────────────────────────
def build_telemetry_event(
    *,
    org_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    request_body: dict[str, Any],
    response_body: dict[str, Any] | str,
    status_code: int,
    error: str | None = None,
) -> dict[str, Any]:
    """Construct a well-formed telemetry event dictionary."""
    return {
        "org_id": org_id,
        "timestamp": str(int(time.time() * 1000)),
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "request_body": request_body,
        "response_body": response_body,
        "status_code": status_code,
        "error": error or "",
    }
