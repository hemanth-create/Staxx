"""
Staxx Intelligence — SQLAlchemy + TimescaleDB Models

Defines the ``cost_events`` hypertable and ``cost_aggregates`` rollup
table using SQLAlchemy 2.0 mapped_column syntax.

Note: The actual ``create_hypertable()`` and continuous aggregate
DDL is executed in the Alembic migration, since SQLAlchemy does not
support TimescaleDB extensions natively.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Double,
    Index,
    Integer,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class CostBase(DeclarativeBase):
    """Declarative base for cost-engine models only."""

    pass


# ---------------------------------------------------------------------------
# cost_events — TimescaleDB hypertable
# ---------------------------------------------------------------------------


class CostEvent(CostBase):
    """
    Raw cost event written for every LLM API call.

    Partitioned by ``time`` via TimescaleDB ``create_hypertable``.
    The hypertable DDL is in the Alembic migration — SQLAlchemy only
    sees a regular table definition here.
    """

    __tablename__ = "cost_events"

    # Composite PK required by TimescaleDB: the time column must be
    # part of any unique constraint / primary key.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        default=lambda: datetime.now(timezone.utc),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    task_type: Mapped[str] = mapped_column(Text, nullable=False, default="unclassified")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Double, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    complexity: Mapped[float] = mapped_column(Double, nullable=True)

    __table_args__ = (
        Index("ix_cost_events_org_time", "org_id", "time"),
        Index("ix_cost_events_model", "model"),
        Index("ix_cost_events_task_type", "task_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<CostEvent org={self.org_id} model={self.model} "
            f"cost=${self.cost_usd:.6f} @ {self.time}>"
        )


# ---------------------------------------------------------------------------
# cost_aggregates — pre-computed hourly rollups (fallback to manual rollup
# if TimescaleDB continuous aggregates are not available)
# ---------------------------------------------------------------------------


class CostAggregate(CostBase):
    """
    Hourly pre-aggregated cost data.

    In production, the ``cost_hourly`` continuous aggregate (defined in the
    migration) is preferred for reads.  This table serves as a manual
    fallback that the worker updates in real-time for instant dashboard
    responsiveness before the continuous aggregate refreshes.
    """

    __tablename__ = "cost_aggregates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(Text, nullable=False)
    call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost: Mapped[float] = mapped_column(Double, nullable=False, default=0.0)
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    avg_latency: Mapped[float] = mapped_column(Double, nullable=True)
    p95_latency: Mapped[float] = mapped_column(Double, nullable=True)

    __table_args__ = (
        Index("ix_cost_agg_org_bucket", "org_id", "bucket"),
        Index("ix_cost_agg_bucket", "bucket"),
        Index(
            "uq_cost_agg_bucket_org_model_task",
            "bucket",
            "org_id",
            "model",
            "task_type",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CostAggregate bucket={self.bucket} org={self.org_id} "
            f"model={self.model} calls={self.call_count} cost=${self.total_cost:.4f}>"
        )


# ---------------------------------------------------------------------------
# Async engine + session factory
# ---------------------------------------------------------------------------

_DATABASE_URL = os.getenv(
    "COST_ENGINE_DATABASE_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/llm_intel",
    ),
)

engine = create_async_engine(_DATABASE_URL, echo=False, pool_size=10, max_overflow=20)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncSession:
    """Yield an async database session (for use as a FastAPI dependency)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session  # type: ignore[misc]
        finally:
            await session.close()
