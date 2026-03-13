"""Platform layer tables

Revision ID: 0002
Revises: 0001
Create Date: 2024-03-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations table
    op.create_table('organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('plan', sa.String(), nullable=False, server_default='free'),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint('uq_organizations_slug', 'organizations', ['slug'])
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=False)

    # Users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_index(op.f('ix_users_org_id'), 'users', ['org_id'], unique=False)

    # API Keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint('uq_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index(op.f('ix_api_keys_org_id'), 'api_keys', ['org_id'], unique=False)

    # Organization Invitations table
    op.create_table('org_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='member'),
        sa.Column('accepted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint('uq_org_invitations_token_hash', 'org_invitations', ['token_hash'])
    op.create_index(op.f('ix_org_invitations_org_id'), 'org_invitations', ['org_id'], unique=False)
    op.create_index(op.f('ix_org_invitations_token_hash'), 'org_invitations', ['token_hash'], unique=False)
    op.create_index(op.f('ix_org_invitations_email'), 'org_invitations', ['email'], unique=False)


def downgrade() -> None:
    op.drop_table('org_invitations')
    op.drop_table('api_keys')
    op.drop_table('users')
    op.drop_table('organizations')
