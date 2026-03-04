"""
Staxx Intelligence — Optimized TimescaleDB Queries

All read-path queries used by the Cost API endpoints.  Every query
leverages TimescaleDB-specific functions (``time_bucket``) and targets
the ``cost_hourly`` continuous aggregate or the ``cost_aggregates``
rollup table for maximum performance.

Functions return raw dicts ready for serialisation by the API layer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PERIOD_MAP: dict[str, timedelta] = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "14d": timedelta(days=14),
    "30d": timedelta(days=30),
    "60d": timedelta(days=60),
    "90d": timedelta(days=90),
}

_GRANULARITY_MAP: dict[str, str] = {
    "hourly": "1 hour",
    "daily": "1 day",
    "weekly": "1 week",
}


def _resolve_period(period: str) -> timedelta:
    """Convert a period string like '7d' to a timedelta."""
    td = _PERIOD_MAP.get(period)
    if td is not None:
        return td
    # Try parsing as plain integer days
    try:
        days = int(period.rstrip("d"))
        return timedelta(days=days)
    except (ValueError, AttributeError):
        logger.warning("Unrecognised period '%s', defaulting to 30d", period)
        return timedelta(days=30)


def _since(period: str) -> datetime:
    """Return the UTC datetime for 'now minus period'."""
    return datetime.now(timezone.utc) - _resolve_period(period)


# ---------------------------------------------------------------------------
# Query: Cost Breakdown by model and task type
# ---------------------------------------------------------------------------

async def query_cost_breakdown(
    session: AsyncSession,
    org_id: UUID,
    period: str = "7d",
) -> list[dict[str, Any]]:
    """
    Cost breakdown grouped by model + task type for the given period.

    Reads from the ``cost_aggregates`` table (pre-rolled-up by the worker).
    Falls back to ``cost_events`` if aggregates are empty.
    """
    since = _since(period)

    # Try aggregates first (fast path)
    result = await session.execute(
        text("""
            SELECT
                model,
                task_type,
                SUM(call_count)::bigint          AS call_count,
                SUM(total_cost)                   AS total_cost,
                SUM(total_input_tokens)::bigint   AS total_input_tokens,
                SUM(total_output_tokens)::bigint  AS total_output_tokens,
                ROUND(AVG(avg_latency)::numeric, 2)  AS avg_latency_ms
            FROM cost_aggregates
            WHERE org_id = :org_id
              AND bucket >= :since
            GROUP BY model, task_type
            ORDER BY total_cost DESC
        """),
        {"org_id": str(org_id), "since": since},
    )
    rows = result.mappings().all()

    if rows:
        return [dict(r) for r in rows]

    # Fallback: query raw hypertable directly
    result = await session.execute(
        text("""
            SELECT
                model,
                task_type,
                COUNT(*)::bigint                  AS call_count,
                SUM(cost_usd)                     AS total_cost,
                SUM(input_tokens)::bigint         AS total_input_tokens,
                SUM(output_tokens)::bigint        AS total_output_tokens,
                ROUND(AVG(latency_ms)::numeric, 2) AS avg_latency_ms
            FROM cost_events
            WHERE org_id = :org_id
              AND time >= :since
            GROUP BY model, task_type
            ORDER BY total_cost DESC
        """),
        {"org_id": str(org_id), "since": since},
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Query: Time-series cost timeline (for charts)
# ---------------------------------------------------------------------------

async def query_cost_timeline(
    session: AsyncSession,
    org_id: UUID,
    granularity: str = "hourly",
    period: str = "30d",
    model_filter: Optional[str] = None,
    task_type_filter: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Time-bucketed cost series using TimescaleDB ``time_bucket``.

    Returns a list of dicts with ``bucket``, ``total_cost``,
    ``call_count``, and optional breakdowns.
    """
    since = _since(period)
    bucket_interval = _GRANULARITY_MAP.get(granularity, "1 hour")

    filters = "WHERE org_id = :org_id AND time >= :since"
    params: dict[str, Any] = {"org_id": str(org_id), "since": since, "interval": bucket_interval}

    if model_filter:
        filters += " AND model = :model_filter"
        params["model_filter"] = model_filter

    if task_type_filter:
        filters += " AND task_type = :task_type_filter"
        params["task_type_filter"] = task_type_filter

    query = f"""
        SELECT
            time_bucket(:interval::interval, time)  AS bucket,
            model,
            task_type,
            COUNT(*)::bigint                         AS call_count,
            SUM(cost_usd)                            AS total_cost,
            SUM(input_tokens)::bigint                AS total_input_tokens,
            SUM(output_tokens)::bigint               AS total_output_tokens,
            ROUND(AVG(latency_ms)::numeric, 2)       AS avg_latency_ms
        FROM cost_events
        {filters}
        GROUP BY bucket, model, task_type
        ORDER BY bucket ASC, total_cost DESC
    """

    result = await session.execute(text(query), params)
    rows = result.mappings().all()

    # Serialise datetime objects to ISO strings
    output = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("bucket"), datetime):
            d["bucket"] = d["bucket"].isoformat()
        output.append(d)
    return output


# ---------------------------------------------------------------------------
# Query: Top-spending task/model combos
# ---------------------------------------------------------------------------

async def query_top_spenders(
    session: AsyncSession,
    org_id: UUID,
    period: str = "30d",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Return the top N most expensive model + task_type combinations.
    """
    since = _since(period)

    result = await session.execute(
        text("""
            SELECT
                model,
                task_type,
                COUNT(*)::bigint        AS call_count,
                SUM(cost_usd)           AS total_cost,
                ROUND(AVG(cost_usd)::numeric, 8) AS avg_cost_per_call,
                SUM(input_tokens)::bigint  AS total_input_tokens,
                SUM(output_tokens)::bigint AS total_output_tokens,
                ROUND(AVG(latency_ms)::numeric, 2) AS avg_latency_ms
            FROM cost_events
            WHERE org_id = :org_id
              AND time >= :since
            GROUP BY model, task_type
            ORDER BY total_cost DESC
            LIMIT :limit
        """),
        {"org_id": str(org_id), "since": since, "limit": limit},
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Query: Summary — total spend, request count, avg cost, MoM trend
# ---------------------------------------------------------------------------

async def query_cost_summary(
    session: AsyncSession,
    org_id: UUID,
) -> dict[str, Any]:
    """
    High-level summary: total spend (current month), request count,
    average cost per request, and month-over-month trend percentage.
    """
    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - timedelta(days=1)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    # Current month stats
    cur = await session.execute(
        text("""
            SELECT
                COALESCE(SUM(cost_usd), 0)         AS total_spend,
                COUNT(*)::bigint                    AS request_count,
                COALESCE(AVG(cost_usd), 0)         AS avg_cost_per_request,
                COALESCE(SUM(input_tokens), 0)::bigint  AS total_input_tokens,
                COALESCE(SUM(output_tokens), 0)::bigint AS total_output_tokens
            FROM cost_events
            WHERE org_id = :org_id
              AND time >= :month_start
        """),
        {"org_id": str(org_id), "month_start": current_month_start},
    )
    current = cur.mappings().one()

    # Previous month stats (for MoM trend)
    prev = await session.execute(
        text("""
            SELECT
                COALESCE(SUM(cost_usd), 0) AS total_spend
            FROM cost_events
            WHERE org_id = :org_id
              AND time >= :prev_start
              AND time < :cur_start
        """),
        {
            "org_id": str(org_id),
            "prev_start": previous_month_start,
            "cur_start": current_month_start,
        },
    )
    previous = prev.mappings().one()

    prev_spend = float(previous["total_spend"])
    cur_spend = float(current["total_spend"])

    if prev_spend > 0:
        mom_trend_pct = round(((cur_spend - prev_spend) / prev_spend) * 100, 2)
    elif cur_spend > 0:
        mom_trend_pct = 100.0  # First month with spend
    else:
        mom_trend_pct = 0.0

    return {
        "total_spend_usd": round(cur_spend, 6),
        "request_count": int(current["request_count"]),
        "avg_cost_per_request_usd": round(float(current["avg_cost_per_request"]), 8),
        "total_input_tokens": int(current["total_input_tokens"]),
        "total_output_tokens": int(current["total_output_tokens"]),
        "current_month_start": current_month_start.isoformat(),
        "month_over_month_trend_pct": mom_trend_pct,
        "previous_month_spend_usd": round(prev_spend, 6),
    }
