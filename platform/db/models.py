"""
SQLAlchemy ORM models for the Staxx platform multi-tenant layer.

Tables defined here:
  - organizations
  - users
  - api_keys
  - org_invitations  (required for the invite flow; add via migration)
"""

import uuid

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    plan = Column(String(50), default="free", nullable=False)
    stripe_customer_id = Column(Text, nullable=True)
    stripe_subscription_id = Column(Text, nullable=True)
    # Stripe metered billing subscription item ID (for usage reporting)
    stripe_usage_item_id = Column(Text, nullable=True)
    risk_tolerance = Column(String(50), default="moderate", nullable=False)
    created_at = Column(TIMESTAMPTZ, server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="org", lazy="noload")
    api_keys = relationship("APIKey", back_populates="org", lazy="noload")
    invitations = relationship("OrgInvitation", back_populates="org", lazy="noload")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    role = Column(String(50), default="viewer", nullable=False)
    created_at = Column(TIMESTAMPTZ, server_default=func.now(), nullable=False)

    org = relationship("Organization", back_populates="users", lazy="noload")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    key_hash = Column(Text, nullable=False)
    key_prefix = Column(String(16), nullable=False)  # first 8 chars of random portion
    label = Column(Text, nullable=True)
    created_at = Column(TIMESTAMPTZ, server_default=func.now(), nullable=False)
    revoked_at = Column(TIMESTAMPTZ, nullable=True)

    org = relationship("Organization", back_populates="api_keys", lazy="noload")


class OrgInvitation(Base):
    """
    Stores pending org invitations. Token is a short-lived UUID sent in the invite URL.

    Migration note: This table is not in the original schema spec. Run:
        ALTER TABLE ... or add it via Alembic migration.
    """

    __tablename__ = "org_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    invited_email = Column(Text, nullable=False)
    role = Column(String(50), default="viewer", nullable=False)
    token = Column(Text, unique=True, nullable=False)
    accepted = Column(Boolean, default=False, nullable=False)
    expires_at = Column(TIMESTAMPTZ, nullable=False)
    created_at = Column(TIMESTAMPTZ, server_default=func.now(), nullable=False)

    org = relationship("Organization", back_populates="invitations", lazy="noload")
