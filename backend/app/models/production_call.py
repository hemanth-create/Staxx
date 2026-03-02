import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class ProductionCall(Base):
    """
    Hypertable in TimescaleDB. Time-series events for production traffic.
    """
    __tablename__ = "production_calls"

    # For TimescaleDB hypertables, if UUID is used and there's a primary key, 
    # the time partitioning column (ts) must be part of the primary key composite.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, default=lambda: datetime.now(timezone.utc)
    )
    
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
