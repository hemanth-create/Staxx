"""
Staxx Intelligence — Shadow Eval SQLAlchemy Models

Defines:
  • ``ShadowEvalRun``     — individual evaluation run result
  • ``ShadowEvalProgress`` — progress tracker per (org, task, original, candidate)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Double,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class ShadowBase(DeclarativeBase):
    """Declarative base for shadow-eval models."""

    pass


# ---------------------------------------------------------------------------
# shadow_eval_runs
# ---------------------------------------------------------------------------


class ShadowEvalRun(ShadowBase):
    """
    Single shadow evaluation run: one prompt replayed against one
    candidate model.
    """

    __tablename__ = "shadow_eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_type: Mapped[str] = mapped_column(Text, nullable=False)
    original_model: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    input_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Double, nullable=True)

    json_valid: Mapped[bool] = mapped_column(Boolean, nullable=True)
    output_empty: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    output_truncated: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    s3_output_key: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_shadow_eval_org_task", "org_id", "task_type"),
        Index("ix_shadow_eval_models", "original_model", "candidate_model"),
        Index(
            "ix_shadow_eval_dedup",
            "org_id", "candidate_model", "prompt_hash",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ShadowEvalRun org={self.org_id} "
            f"{self.original_model} → {self.candidate_model} "
            f"cost=${self.cost_usd} @ {self.created_at}>"
        )


# ---------------------------------------------------------------------------
# shadow_eval_progress
# ---------------------------------------------------------------------------


class ShadowEvalProgress(ShadowBase):
    """
    Progress tracker: how many runs exist for each
    (org, task_type, original_model, candidate_model) tuple.

    Updated atomically via ON CONFLICT upsert in the queries module.
    """

    __tablename__ = "shadow_eval_progress"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    task_type: Mapped[str] = mapped_column(Text, primary_key=True)
    original_model: Mapped[str] = mapped_column(Text, primary_key=True)
    candidate_model: Mapped[str] = mapped_column(Text, primary_key=True)

    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ShadowEvalProgress {self.original_model} → {self.candidate_model} "
            f"task={self.task_type} valid={self.valid_runs}/{self.total_runs}>"
        )

    @property
    def has_sufficient_data(self) -> bool:
        """N ≥ 20 valid runs required for statistical confidence."""
        return self.valid_runs >= 20


# ---------------------------------------------------------------------------
# Async engine + session factory
# ---------------------------------------------------------------------------

_DATABASE_URL = os.getenv(
    "SHADOW_EVAL_DATABASE_URL",
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
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session  # type: ignore[misc]
        finally:
            await session.close()
