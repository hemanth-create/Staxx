"""
Staxx Intelligence — Recommendations DB Queries

All database interactions for the recommendations package.
Uses raw SQLAlchemy Core (text + mappings) to stay consistent with the
rest of the Staxx backend.  No ORM sessions are used for reads — only
for writes where the ORM simplifies upsert logic.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from recommendations.generator import RiskTolerance, SwapCard
from scoring.schemas import ScoringResult

logger = logging.getLogger(__name__)

_RISK_STATUS_MAP: dict[RiskTolerance, list[str]] = {
    "conservative": ["STRONG_YES"],
    "moderate": ["STRONG_YES", "YES"],
    "aggressive": ["STRONG_YES", "YES", "MAYBE"],
}


# ---------------------------------------------------------------------------
# Scoring results — read from scoring engine tables
# ---------------------------------------------------------------------------


async def fetch_scoring_results_for_org(
    session: AsyncSession,
    org_id: str,
) -> list[ScoringResult]:
    """
    Load the latest ScoringResult for every (task_type, original_model)
    combination for this org from the scoring_results cache table.

    The scoring engine is expected to write serialised ScoringResult JSON
    into the `scoring_results` table after each scoring run.
    """
    result = await session.execute(
        text("""
            SELECT DISTINCT ON (task_type, original_model)
                payload
            FROM scoring_results
            WHERE org_id = :org_id
            ORDER BY task_type, original_model, generated_at DESC
        """),
        {"org_id": org_id},
    )
    rows = result.all()
    out: list[ScoringResult] = []
    for row in rows:
        try:
            payload = row[0]
            if isinstance(payload, str):
                payload = json.loads(payload)
            out.append(ScoringResult.model_validate(payload))
        except Exception:
            logger.exception("Failed to deserialise ScoringResult for org=%s", org_id)
    return out


# ---------------------------------------------------------------------------
# Swap cards — read
# ---------------------------------------------------------------------------


async def fetch_approved_cards(
    session: AsyncSession,
    org_id: str,
    risk_tolerance: RiskTolerance = "moderate",
) -> dict[str, list[SwapCard]]:
    """
    Fetch active (non-dismissed) swap cards for an org from the DB,
    filtered by the allowed swap_recommendation values for the given
    risk_tolerance.

    Returns a dict keyed by task_type.
    """
    allowed = _RISK_STATUS_MAP[risk_tolerance]
    placeholders = ", ".join(f":rec_{i}" for i in range(len(allowed)))
    params: dict[str, Any] = {"org_id": org_id}
    for i, val in enumerate(allowed):
        params[f"rec_{i}"] = val

    result = await session.execute(
        text(f"""
            SELECT
                id::text, org_id::text, task_type, current_model,
                recommended_model, swap_recommendation, confidence_pct,
                monthly_savings_usd, annual_savings_usd,
                monthly_savings_ci_lower, monthly_savings_ci_upper,
                original_monthly_cost_usd, projected_monthly_cost_usd,
                headline, rationale, metrics,
                created_at, status
            FROM recommendation_swaps
            WHERE org_id = :org_id
              AND status NOT IN ('dismissed')
              AND swap_recommendation IN ({placeholders})
            ORDER BY monthly_savings_usd DESC
        """),
        params,
    )
    rows = result.mappings().all()

    grouped: dict[str, list[SwapCard]] = {}
    for row in rows:
        metrics_raw = row["metrics"]
        if isinstance(metrics_raw, str):
            metrics_raw = json.loads(metrics_raw)

        from recommendations.generator import MetricsSummary

        card = SwapCard(
            id=row["id"],
            org_id=row["org_id"],
            task_type=row["task_type"],
            current_model=row["current_model"],
            recommended_model=row["recommended_model"],
            swap_recommendation=row["swap_recommendation"],
            confidence_pct=row["confidence_pct"],
            monthly_savings_usd=row["monthly_savings_usd"],
            annual_savings_usd=row["annual_savings_usd"],
            monthly_savings_ci_lower=row["monthly_savings_ci_lower"],
            monthly_savings_ci_upper=row["monthly_savings_ci_upper"],
            original_monthly_cost_usd=row["original_monthly_cost_usd"],
            projected_monthly_cost_usd=row["projected_monthly_cost_usd"],
            headline=row["headline"],
            rationale=row["rationale"],
            metrics=MetricsSummary(**metrics_raw),
            generated_at=row["created_at"],
            status=row["status"],
        )
        grouped.setdefault(row["task_type"], []).append(card)

    return grouped


async def fetch_card_by_id(
    session: AsyncSession,
    recommendation_id: str,
) -> dict[str, Any] | None:
    """Fetch a single swap card row by its UUID."""
    result = await session.execute(
        text("""
            SELECT id::text, org_id::text, status
            FROM recommendation_swaps
            WHERE id = :id::uuid
        """),
        {"id": recommendation_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Swap cards — write
# ---------------------------------------------------------------------------


async def persist_swap_cards(
    session: AsyncSession,
    cards: list[SwapCard],
) -> None:
    """
    Upsert swap cards into the DB.

    ON CONFLICT on (org_id, task_type, current_model, recommended_model):
    updates the scoring fields and preserves status / approval metadata.
    """
    for card in cards:
        metrics_json = card.metrics.model_dump_json()
        await session.execute(
            text("""
                INSERT INTO recommendation_swaps (
                    id, org_id, task_type, current_model, recommended_model,
                    swap_recommendation, confidence_pct,
                    monthly_savings_usd, annual_savings_usd,
                    monthly_savings_ci_lower, monthly_savings_ci_upper,
                    original_monthly_cost_usd, projected_monthly_cost_usd,
                    headline, rationale, metrics,
                    status, created_at, updated_at
                ) VALUES (
                    :id::uuid, :org_id::uuid, :task_type, :current_model,
                    :recommended_model, :swap_recommendation, :confidence_pct,
                    :monthly_savings_usd, :annual_savings_usd,
                    :monthly_savings_ci_lower, :monthly_savings_ci_upper,
                    :original_monthly_cost_usd, :projected_monthly_cost_usd,
                    :headline, :rationale, CAST(:metrics AS jsonb),
                    'active', NOW(), NOW()
                )
                ON CONFLICT (org_id, task_type, current_model, recommended_model)
                DO UPDATE SET
                    swap_recommendation = EXCLUDED.swap_recommendation,
                    confidence_pct = EXCLUDED.confidence_pct,
                    monthly_savings_usd = EXCLUDED.monthly_savings_usd,
                    annual_savings_usd = EXCLUDED.annual_savings_usd,
                    monthly_savings_ci_lower = EXCLUDED.monthly_savings_ci_lower,
                    monthly_savings_ci_upper = EXCLUDED.monthly_savings_ci_upper,
                    original_monthly_cost_usd = EXCLUDED.original_monthly_cost_usd,
                    projected_monthly_cost_usd = EXCLUDED.projected_monthly_cost_usd,
                    headline = EXCLUDED.headline,
                    rationale = EXCLUDED.rationale,
                    metrics = EXCLUDED.metrics,
                    updated_at = NOW()
                    -- Preserve status / approved_by / dismissed_* from existing row
            """),
            {
                "id": card.id,
                "org_id": card.org_id,
                "task_type": card.task_type,
                "current_model": card.current_model,
                "recommended_model": card.recommended_model,
                "swap_recommendation": card.swap_recommendation,
                "confidence_pct": card.confidence_pct,
                "monthly_savings_usd": card.monthly_savings_usd,
                "annual_savings_usd": card.annual_savings_usd,
                "monthly_savings_ci_lower": card.monthly_savings_ci_lower,
                "monthly_savings_ci_upper": card.monthly_savings_ci_upper,
                "original_monthly_cost_usd": card.original_monthly_cost_usd,
                "projected_monthly_cost_usd": card.projected_monthly_cost_usd,
                "headline": card.headline,
                "rationale": card.rationale,
                "metrics": metrics_json,
            },
        )
    await session.commit()
    logger.info("Persisted %d swap cards.", len(cards))


async def approve_swap_card(
    session: AsyncSession,
    recommendation_id: str,
    approved_by: str | None,
    notes: str | None,
) -> datetime:
    """
    Mark a swap card as approved and write an audit log entry.

    Returns the updated_at timestamp.
    """
    now = datetime.now(timezone.utc)
    await session.execute(
        text("""
            UPDATE recommendation_swaps
            SET status = 'approved',
                approved_by = :approved_by,
                approved_at = :now,
                updated_at = :now
            WHERE id = :id::uuid
        """),
        {"id": recommendation_id, "approved_by": approved_by, "now": now},
    )
    # Fetch org_id for audit log
    result = await session.execute(
        text("SELECT org_id::text FROM recommendation_swaps WHERE id = :id::uuid"),
        {"id": recommendation_id},
    )
    row = result.first()
    org_id = row[0] if row else "unknown"

    await session.execute(
        text("""
            INSERT INTO swap_audit_log (swap_id, org_id, action, actor, notes, created_at)
            VALUES (:swap_id::uuid, :org_id::uuid, 'approved', :actor, :notes, :now)
        """),
        {
            "swap_id": recommendation_id,
            "org_id": org_id,
            "actor": approved_by,
            "notes": notes,
            "now": now,
        },
    )
    await session.commit()
    return now


async def dismiss_swap_card(
    session: AsyncSession,
    recommendation_id: str,
    dismissed_by: str | None,
    reason: str | None,
) -> datetime:
    """
    Mark a swap card as dismissed and write an audit log entry.

    Returns the updated_at timestamp.
    """
    now = datetime.now(timezone.utc)
    await session.execute(
        text("""
            UPDATE recommendation_swaps
            SET status = 'dismissed',
                dismissed_by = :dismissed_by,
                dismissed_at = :now,
                dismiss_reason = :reason,
                updated_at = :now
            WHERE id = :id::uuid
        """),
        {
            "id": recommendation_id,
            "dismissed_by": dismissed_by,
            "reason": reason,
            "now": now,
        },
    )
    result = await session.execute(
        text("SELECT org_id::text FROM recommendation_swaps WHERE id = :id::uuid"),
        {"id": recommendation_id},
    )
    row = result.first()
    org_id = row[0] if row else "unknown"

    await session.execute(
        text("""
            INSERT INTO swap_audit_log (swap_id, org_id, action, actor, notes, created_at)
            VALUES (:swap_id::uuid, :org_id::uuid, 'dismissed', :actor, :notes, :now)
        """),
        {
            "swap_id": recommendation_id,
            "org_id": org_id,
            "actor": dismissed_by,
            "notes": reason,
            "now": now,
        },
    )
    await session.commit()
    return now


# ---------------------------------------------------------------------------
# Alerts — read
# ---------------------------------------------------------------------------


async def fetch_active_alerts(
    session: AsyncSession,
    org_id: str,
    alert_type: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch active alerts for an org with optional type/severity filters.
    """
    conditions = ["org_id = :org_id", "status = 'active'"]
    params: dict[str, Any] = {"org_id": org_id, "limit": limit}

    if alert_type:
        conditions.append("alert_type = :alert_type")
        params["alert_type"] = alert_type

    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity

    where_clause = " AND ".join(conditions)
    result = await session.execute(
        text(f"""
            SELECT
                id::text, org_id::text,
                swap_id::text,
                alert_type, severity, message, metadata,
                status, created_at
            FROM recommendation_alerts
            WHERE {where_clause}
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 0
                    WHEN 'warning' THEN 1
                    ELSE 2
                END,
                created_at DESC
            LIMIT :limit
        """),
        params,
    )
    return [dict(row._mapping) for row in result.all()]


# ---------------------------------------------------------------------------
# Org spend — read
# ---------------------------------------------------------------------------


async def fetch_org_monthly_cost(
    session: AsyncSession,
    org_id: str,
) -> float:
    """
    Return total LLM spend for the org over the last 30 days.
    Used as the `original_monthly_cost` baseline for ROI projections.
    """
    result = await session.execute(
        text("""
            SELECT COALESCE(SUM(cost_usd), 0) AS total
            FROM cost_events
            WHERE org_id = :org_id::uuid
              AND time >= NOW() - INTERVAL '30 days'
              AND status = 'success'
        """),
        {"org_id": org_id},
    )
    row = result.first()
    return float(row[0]) if row else 0.0
