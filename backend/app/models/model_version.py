import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class ModelVersion(Base):
    """
    Registry for specific model versions.
    E.g., gpt-4o-2024-08-06
    """
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    provider_model_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    
    # JSONB columns for flexible data schemas
    capabilities: Mapped[dict] = mapped_column(JSONB, default=dict)
    pricing: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
