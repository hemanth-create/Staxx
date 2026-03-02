"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2024-03-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. model_versions
    op.create_table('model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_model_id', sa.String(), nullable=False),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('pricing', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_versions_provider_model_id'), 'model_versions', ['provider_model_id'], unique=False)

    # 2. production_calls
    op.create_table('production_calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ),
        sa.PrimaryKeyConstraint('id', 'ts')  # TimescaleDB requires partitioning column in PK if UUID is used
    )
    op.create_index(op.f('ix_production_calls_model_version_id'), 'production_calls', ['model_version_id'], unique=False)
    op.create_index(op.f('ix_production_calls_task_type'), 'production_calls', ['task_type'], unique=False)

    # TimescaleDB Specific: create hypertable
    # The 'ts' column is the partition chunking key
    op.execute("SELECT create_hypertable('production_calls', 'ts', if_not_exists => TRUE);")

    # 3. eval_runs
    op.create_table('eval_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('prompt_hash', sa.String(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('json_valid', sa.Boolean(), nullable=True),
        sa.Column('output_ref', sa.String(), nullable=True),
        sa.Column('n_run', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eval_runs_model_version_id'), 'eval_runs', ['model_version_id'], unique=False)
    op.create_index(op.f('ix_eval_runs_prompt_hash'), 'eval_runs', ['prompt_hash'], unique=False)
    op.create_index(op.f('ix_eval_runs_task_type'), 'eval_runs', ['task_type'], unique=False)


def downgrade() -> None:
    op.drop_table('eval_runs')
    op.drop_table('production_calls')
    op.drop_table('model_versions')
