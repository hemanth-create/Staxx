"""
Staxx Intelligence — Alert & Drift Monitor

Celery beat periodic tasks that continuously monitor implemented swaps for:
  - Quality drift (error rate, JSON validity degradation)
  - Cost drift (model pricing changes)
  - Volume drift (traffic volume changes affecting absolute savings)
  - New opportunity detection (cheaper models released)

Alerts are written to the `recommendation_alerts` table and optionally
dispatched via webhooks / Slack.

Celery beat schedule is registered at the bottom of this module.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from celery import shared_task
from celery.schedules import crontab
from sqlalchemy import text

from app.config import settings
from app.core.db import AsyncSessionLocal
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Drift thresholds (defaults; overridden per-org from DB)
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS: dict[str, float] = {
    # Quality drift — alert if metric worsens by more than this fraction
    "error_rate_delta_abs": 0.02,       # 2 percentage-point increase in errors
    "json_validity_drop_abs": 0.03,     # 3 pp drop in JSON validity
    # Cost drift — alert if per-call cost of the new model changes by more than
    "cost_delta_pct": 0.15,             # 15% price change
    # Volume drift — alert if monthly call volume changes by more than
    "volume_delta_pct": 0.30,           # 30% traffic change (positive or negative)
}

# ---------------------------------------------------------------------------
# DB helpers (async, wrapped for sync Celery tasks)
# ---------------------------------------------------------------------------


async def _load_active_swaps(session: Any) -> list[dict[str, Any]]:
    """Load all approved/implemented swaps with their baseline metrics."""
    result = await session.execute(
        text("""
            SELECT
                r.id,
                r.org_id,
                r.task_type,
                r.current_model,
                r.recommended_model,
                r.baseline_error_rate,
                r.baseline_json_validity_rate,
                r.baseline_cost_per_call_usd,
                r.baseline_monthly_volume,
                r.approved_at
            FROM recommendation_swaps r
            WHERE r.status = 'approved'
              AND r.approved_at IS NOT NULL
        """)
    )
    return [dict(row._mapping) for row in result.all()]


async def _load_org_thresholds(session: Any, org_id: str) -> dict[str, float]:
    """Load per-org alert thresholds, falling back to defaults."""
    result = await session.execute(
        text("""
            SELECT threshold_key, threshold_value
            FROM org_alert_thresholds
            WHERE org_id = :org_id
        """),
        {"org_id": org_id},
    )
    rows = result.all()
    thresholds = dict(DEFAULT_THRESHOLDS)
    for row in rows:
        thresholds[row[0]] = float(row[1])
    return thresholds


async def _get_current_metrics(
    session: Any,
    org_id: str,
    task_type: str,
    model: str,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """Fetch recent production metrics for an (org, task_type, model) tuple."""
    result = await session.execute(
        text("""
            SELECT
                COALESCE(AVG(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END), 0) AS error_rate,
                COALESCE(AVG(CASE WHEN json_valid = true THEN 1 ELSE 0 END), NULL) AS json_validity_rate,
                COALESCE(AVG(cost_usd), 0) AS avg_cost_per_call,
                COUNT(*) AS call_volume
            FROM shadow_eval_runs
            WHERE org_id = :org_id
              AND task_type = :task_type
              AND candidate_model = :model
              AND created_at >= NOW() - INTERVAL '1 day' * :days
        """),
        {
            "org_id": org_id,
            "task_type": task_type,
            "model": model,
            "days": lookback_days,
        },
    )
    row = result.mappings().first()
    if row is None:
        return {}
    return dict(row)


async def _insert_alert(
    session: Any,
    org_id: str,
    swap_id: str,
    alert_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any],
) -> str:
    """Insert a drift alert and return the new alert id."""
    result = await session.execute(
        text("""
            INSERT INTO recommendation_alerts
                (org_id, swap_id, alert_type, severity, message, metadata, created_at, status)
            VALUES
                (:org_id, :swap_id, :alert_type, :severity, :message,
                 CAST(:metadata AS jsonb), NOW(), 'active')
            RETURNING id::text
        """),
        {
            "org_id": org_id,
            "swap_id": swap_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "metadata": str(metadata).replace("'", '"'),
        },
    )
    await session.commit()
    row = result.first()
    return str(row[0]) if row else ""


async def _load_known_models(session: Any) -> set[str]:
    """Load the set of model identifiers we already know about."""
    result = await session.execute(
        text("SELECT provider_model_id FROM model_versions")
    )
    return {row[0] for row in result.all()}


async def _load_pricing_catalog() -> dict[str, float]:
    """
    Return a dict of model_id → price_per_1k_output_tokens from our
    internal pricing table.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT provider_model_id,
                       (pricing->>'output_cost_per_1k')::float AS price
                FROM model_versions
                WHERE pricing->>'output_cost_per_1k' IS NOT NULL
            """)
        )
        return {row[0]: float(row[1]) for row in result.all()}


# ---------------------------------------------------------------------------
# Drift detection helpers
# ---------------------------------------------------------------------------


def _check_quality_drift(
    swap: dict[str, Any],
    current: dict[str, Any],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    """Return list of alert dicts for quality drift, if any."""
    alerts: list[dict[str, Any]] = []

    baseline_err = swap.get("baseline_error_rate") or 0.0
    current_err = current.get("error_rate") or 0.0
    err_delta = current_err - baseline_err
    if err_delta > thresholds["error_rate_delta_abs"]:
        alerts.append({
            "type": "quality_drift",
            "severity": "warning" if err_delta < 0.05 else "critical",
            "message": (
                f"Error rate for {swap['recommended_model']} on {swap['task_type']} "
                f"has increased by {err_delta * 100:.2f}pp "
                f"(baseline: {baseline_err * 100:.2f}%, now: {current_err * 100:.2f}%)."
            ),
            "metadata": {
                "baseline_error_rate": baseline_err,
                "current_error_rate": current_err,
                "delta": err_delta,
            },
        })

    baseline_jv = swap.get("baseline_json_validity_rate")
    current_jv = current.get("json_validity_rate")
    if baseline_jv is not None and current_jv is not None:
        jv_drop = baseline_jv - current_jv
        if jv_drop > thresholds["json_validity_drop_abs"]:
            alerts.append({
                "type": "quality_drift",
                "severity": "warning" if jv_drop < 0.05 else "critical",
                "message": (
                    f"JSON validity for {swap['recommended_model']} on {swap['task_type']} "
                    f"dropped by {jv_drop * 100:.2f}pp "
                    f"(baseline: {baseline_jv * 100:.1f}%, now: {current_jv * 100:.1f}%)."
                ),
                "metadata": {
                    "baseline_json_validity": baseline_jv,
                    "current_json_validity": current_jv,
                    "drop": jv_drop,
                },
            })

    return alerts


def _check_cost_drift(
    swap: dict[str, Any],
    current: dict[str, Any],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    """Return alert dicts if cost per call has drifted beyond threshold."""
    alerts: list[dict[str, Any]] = []
    baseline_cost = swap.get("baseline_cost_per_call_usd") or 0.0
    current_cost = current.get("avg_cost_per_call") or 0.0

    if baseline_cost <= 0:
        return alerts

    delta_pct = abs((current_cost - baseline_cost) / baseline_cost)
    if delta_pct > thresholds["cost_delta_pct"]:
        direction = "increased" if current_cost > baseline_cost else "decreased"
        alerts.append({
            "type": "cost_drift",
            "severity": "info" if current_cost < baseline_cost else "warning",
            "message": (
                f"Cost per call for {swap['recommended_model']} on {swap['task_type']} "
                f"has {direction} by {delta_pct * 100:.1f}% "
                f"(baseline: ${baseline_cost:.6f}, now: ${current_cost:.6f}). "
                f"Recalculate savings projections."
            ),
            "metadata": {
                "baseline_cost_per_call": baseline_cost,
                "current_cost_per_call": current_cost,
                "delta_pct": delta_pct,
            },
        })
    return alerts


def _check_volume_drift(
    swap: dict[str, Any],
    current: dict[str, Any],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    """Return alert dicts if call volume has changed enough to affect savings."""
    alerts: list[dict[str, Any]] = []
    baseline_vol = swap.get("baseline_monthly_volume") or 0
    # current volume is over lookback_days=7; scale to monthly
    current_vol_weekly = current.get("call_volume") or 0
    current_vol_monthly = current_vol_weekly * (30 / 7)

    if baseline_vol <= 0:
        return alerts

    delta_pct = abs((current_vol_monthly - baseline_vol) / baseline_vol)
    if delta_pct > thresholds["volume_delta_pct"]:
        direction = "grown" if current_vol_monthly > baseline_vol else "shrunk"
        alerts.append({
            "type": "volume_drift",
            "severity": "info",
            "message": (
                f"Traffic volume for {swap['task_type']} on {swap['recommended_model']} "
                f"has {direction} by {delta_pct * 100:.0f}% "
                f"(baseline: {baseline_vol:,} calls/mo, "
                f"projected now: {current_vol_monthly:,.0f} calls/mo). "
                f"Savings projections may be outdated."
            ),
            "metadata": {
                "baseline_monthly_volume": baseline_vol,
                "estimated_current_monthly_volume": current_vol_monthly,
                "delta_pct": delta_pct,
            },
        })
    return alerts


# ---------------------------------------------------------------------------
# Core async monitor logic
# ---------------------------------------------------------------------------


async def _run_drift_check() -> dict[str, int]:
    """
    Full drift check pass.

    Returns a summary dict: {"swaps_checked": N, "alerts_raised": M}
    """
    async with AsyncSessionLocal() as session:
        swaps = await _load_active_swaps(session)
        if not swaps:
            logger.info("No active swaps to monitor.")
            return {"swaps_checked": 0, "alerts_raised": 0}

        alerts_raised = 0
        for swap in swaps:
            org_id = str(swap["org_id"])
            swap_id = str(swap["id"])
            thresholds = await _load_org_thresholds(session, org_id)

            current = await _get_current_metrics(
                session,
                org_id=org_id,
                task_type=swap["task_type"],
                model=swap["recommended_model"],
            )

            if not current:
                logger.debug("No recent data for swap %s, skipping.", swap_id)
                continue

            all_alerts = (
                _check_quality_drift(swap, current, thresholds)
                + _check_cost_drift(swap, current, thresholds)
                + _check_volume_drift(swap, current, thresholds)
            )

            for alert in all_alerts:
                await _insert_alert(
                    session,
                    org_id=org_id,
                    swap_id=swap_id,
                    alert_type=alert["type"],
                    severity=alert["severity"],
                    message=alert["message"],
                    metadata=alert["metadata"],
                )
                alerts_raised += 1
                logger.warning(
                    "Alert raised [%s][%s]: %s",
                    alert["severity"],
                    alert["type"],
                    alert["message"],
                )

        return {"swaps_checked": len(swaps), "alerts_raised": alerts_raised}


async def _run_opportunity_detection() -> dict[str, int]:
    """
    Scan for new/cheaper models that might generate new swap opportunities.

    This is a lightweight pass that simply detects model_versions entries
    with newer valid_from dates than the last scan, and creates an
    informational alert per org that has active usage on the potentially
    displaced model family.
    """
    alerts_raised = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT DISTINCT
                    mv.id::text AS model_id,
                    mv.provider_model_id,
                    mv.valid_from,
                    mv.pricing
                FROM model_versions mv
                WHERE mv.valid_from > NOW() - INTERVAL '7 days'
                  AND mv.valid_from IS NOT NULL
            """)
        )
        new_models = [dict(row._mapping) for row in result.all()]

        if not new_models:
            return {"new_models_detected": 0, "alerts_raised": 0}

        # Find orgs that are actively spending on the same model family
        for model in new_models:
            new_id = model["provider_model_id"]

            # Determine family prefix (e.g., "gpt-4" from "gpt-4o-mini-2024-07-18")
            family = new_id.split("-")[0:2]
            family_prefix = "-".join(family)

            orgs_result = await session.execute(
                text("""
                    SELECT DISTINCT org_id::text
                    FROM cost_events
                    WHERE model ILIKE :prefix
                      AND time >= NOW() - INTERVAL '30 days'
                """),
                {"prefix": f"{family_prefix}%"},
            )
            org_ids = [row[0] for row in orgs_result.all()]

            for org_id in org_ids:
                await _insert_alert(
                    session,
                    org_id=org_id,
                    swap_id="",
                    alert_type="new_opportunity",
                    severity="info",
                    message=(
                        f"New model detected: {new_id}. "
                        f"It may offer lower cost than your current {family_prefix} usage. "
                        f"Scheduling shadow evaluation."
                    ),
                    metadata={
                        "new_model_id": new_id,
                        "pricing": model.get("pricing"),
                    },
                )
                alerts_raised += 1

    return {"new_models_detected": len(new_models), "alerts_raised": alerts_raised}


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------


@shared_task(name="recommendations.drift_monitor.check_drift", bind=True, max_retries=3)
def check_drift(self: Any) -> dict[str, int]:
    """
    Celery task: check all active swaps for quality/cost/volume drift.

    Scheduled every hour via Celery beat.
    """
    try:
        return asyncio.get_event_loop().run_until_complete(_run_drift_check())
    except Exception as exc:
        logger.exception("Drift check failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    name="recommendations.drift_monitor.detect_new_opportunities",
    bind=True,
    max_retries=3,
)
def detect_new_opportunities(self: Any) -> dict[str, int]:
    """
    Celery task: scan for new cheaper models and alert relevant orgs.

    Scheduled daily via Celery beat.
    """
    try:
        return asyncio.get_event_loop().run_until_complete(_run_opportunity_detection())
    except Exception as exc:
        logger.exception("Opportunity detection failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)


# ---------------------------------------------------------------------------
# Celery beat schedule registration
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    **getattr(celery_app.conf, "beat_schedule", {}),
    "drift-check-hourly": {
        "task": "recommendations.drift_monitor.check_drift",
        "schedule": crontab(minute=0),  # every hour on the hour
    },
    "opportunity-detection-daily": {
        "task": "recommendations.drift_monitor.detect_new_opportunities",
        "schedule": crontab(hour=6, minute=0),  # 06:00 UTC daily
    },
}
