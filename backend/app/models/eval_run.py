import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class EvalRun(Base):
    """
    Stores background shadow evaluation results for N=20 runs per prompt.
    """
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String, index=True, nullable=False)
    
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Evaluation dimensions
    json_valid: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    # Reference to S3 bucket object ID containing the raw output payload
    output_ref: Mapped[str] = mapped_column(String, nullable=True)
    
    n_run: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
