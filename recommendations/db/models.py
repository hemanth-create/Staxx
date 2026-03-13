"""
Staxx Intelligence — Recommendations DB Models

SQLAlchemy ORM tables:

  recommendation_swaps      — Persisted swap recommendation cards
  swap_audit_log            — Immutable approval / dismissal events
  recommendation_alerts     — Drift and opportunity alerts
  org_alert_thresholds      — Per-org configurable drift thresholds

All tables use UUIDs as primary keys and include created_at / updated_at
timestamps. Row-level security (RLS) for tenant isolation is enforced at
the Postgres level via org_id; queries always filter by org_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class RecommendationSwap(Base):
    """
    A persisted swap recommendation card.

    One row per (org, task_type, current_model, recommended_model) at a
    given point in time.  New scoring runs produce new rows rather than
    mutating old ones; the UI surfaces only status='active' | 'approved'.
    """

    __tablename__ = "recommendation_swaps"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "task_type",
            "current_model",
            "recommended_model",
            name="uq_recommendation_swap",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    current_model: Mapped[str] = mapped_column(String(256), nullable=False)
    recommended_model: Mapped[str] = mapped_column(String(256), nullable=False)

    # Scoring metadata
    swap_recommendation: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # STRONG_YES | YES | MAYBE
    confidence_pct: Mapped[int] = mapped_column(Integer, nullable=False)

    # Dollar amounts
    monthly_savings_usd: Mapped[float] = mapped_column(Float, nullable=False)
    annual_savings_usd: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_savings_ci_lower: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_savings_ci_upper: Mapped[float] = mapped_column(Float, nullable=False)
    original_monthly_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    projected_monthly_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)

    # Human-readable copy
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    # Full metrics snapshot (JSONB for flexibility)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Baseline metrics captured at approval time — used by drift monitor
    baseline_error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_json_validity_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    baseline_cost_per_call_usd: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    baseline_monthly_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | approved | dismissed
    approved_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissed_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismiss_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class SwapAuditLog(Base):
    """
    Immutable audit trail for approve / dismiss events on swap cards.

    Never updated — only inserted.
    """

    __tablename__ = "swap_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    swap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendation_swaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # approved | dismissed | reopened
    actor: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )


class RecommendationAlert(Base):
    """
    Drift and opportunity alerts raised by the drift monitor.

    Alerts are never deleted — they transition through status:
      active → acknowledged → resolved
    """

    __tablename__ = "recommendation_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    swap_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendation_swaps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # quality_drift | cost_drift | volume_drift | new_opportunity
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )  # info | warning | critical
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | acknowledged | resolved
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OrgAlertThreshold(Base):
    """
    Per-org overrides for drift detection thresholds.

    Rows are keyed by (org_id, threshold_key).  Missing rows fall back
    to the defaults defined in drift_monitor.DEFAULT_THRESHOLDS.
    """

    __tablename__ = "org_alert_thresholds"
    __table_args__ = (
        UniqueConstraint("org_id", "threshold_key", name="uq_org_threshold"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    threshold_key: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # e.g. "error_rate_delta_abs"
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )
