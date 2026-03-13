"""
Usage tracking per org per billing period.

Strategy:
  1. Every proxied/SDK request increments a Redis counter:
         INCR  usage:{org_id}:{YYYY-MM}
  2. A periodic Celery task (or cron endpoint) reads those counters and:
     a. Reports accumulated usage to Stripe metered billing
     b. Resets the Redis counter after a successful Stripe report
  3. Plan quota enforcement: before allowing a request, check the counter
     against the plan limit (PLAN_LIMITS).

Redis keys:
  usage:{org_id}:{YYYY-MM}       → integer counter (lifetime increments)
  usage_reported:{org_id}:{YYYY-MM} → integer (already reported to Stripe)
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis

from platform.billing.stripe_client import PLAN_LIMITS, report_usage
from platform.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _billing_period() -> str:
    """Return current billing period string, e.g. '2025-08'."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def _usage_key(org_id: UUID, period: str | None = None) -> str:
    period = period or _billing_period()
    return f"usage:{org_id}:{period}"


def _reported_key(org_id: UUID, period: str | None = None) -> str:
    period = period or _billing_period()
    return f"usage_reported:{org_id}:{period}"


# ---------------------------------------------------------------------------
# Increment
# ---------------------------------------------------------------------------


async def increment_usage(org_id: UUID, count: int = 1) -> int:
    """
    Increment the request counter for this org in the current billing period.
    Returns the new total count.
    """
    r = _get_redis()
    key = _usage_key(org_id)
    new_total: int = await r.incrby(key, count)
    # Set TTL to 35 days so stale keys are cleaned up automatically
    await r.expire(key, 60 * 60 * 24 * 35)
    return new_total


# ---------------------------------------------------------------------------
# Quota check
# ---------------------------------------------------------------------------


async def get_usage(org_id: UUID, period: str | None = None) -> int:
    """Return the current usage count for the org in the given billing period."""
    r = _get_redis()
    raw = await r.get(_usage_key(org_id, period))
    return int(raw) if raw else 0


async def check_quota(org_id: UUID, plan: str) -> tuple[bool, int, int]:
    """
    Check whether the org is within their plan quota.

    Returns:
        (within_quota, current_usage, limit)
        limit == -1 means unlimited.
    """
    limit = PLAN_LIMITS.get(plan, 10_000)
    if limit == -1:
        return True, 0, -1
    current = await get_usage(org_id)
    return current < limit, current, limit


# ---------------------------------------------------------------------------
# Stripe usage reporting
# ---------------------------------------------------------------------------


async def flush_usage_to_stripe(
    org_id: UUID,
    stripe_usage_item_id: str,
    period: str | None = None,
) -> int:
    """
    Report the delta (unreported usage) to Stripe for the given org+period.

    This is idempotent: it only reports usage that hasn't been reported yet.
    Returns the number of units reported.

    Call this:
      - From a periodic Celery task (e.g. every hour)
      - At end of billing period
      - On explicit sync request
    """
    r = _get_redis()
    period = period or _billing_period()
    total = int(await r.get(_usage_key(org_id, period)) or 0)
    already_reported = int(await r.get(_reported_key(org_id, period)) or 0)
    delta = total - already_reported

    if delta <= 0:
        logger.debug("No new usage to report for org %s period %s", org_id, period)
        return 0

    idempotency_key = f"{org_id}-{period}-{already_reported}"
    await report_usage(stripe_usage_item_id, delta, idempotency_key=idempotency_key)

    # Update the reported counter
    await r.set(_reported_key(org_id, period), total, ex=60 * 60 * 24 * 35)
    logger.info("Reported %d units for org %s period %s", delta, org_id, period)
    return delta


async def get_usage_summary(org_id: UUID) -> dict:
    """
    Return a dict with current and previous period usage for display in the dashboard.
    """
    r = _get_redis()
    current_period = _billing_period()

    # Compute previous period string
    now = datetime.now(timezone.utc)
    if now.month == 1:
        prev_period = f"{now.year - 1}-12"
    else:
        prev_period = f"{now.year}-{now.month - 1:02d}"

    current = int(await r.get(_usage_key(org_id, current_period)) or 0)
    previous = int(await r.get(_usage_key(org_id, prev_period)) or 0)

    return {
        "current_period": current_period,
        "current_usage": current,
        "previous_period": prev_period,
        "previous_usage": previous,
    }
