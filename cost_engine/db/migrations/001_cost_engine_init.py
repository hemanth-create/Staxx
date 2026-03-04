"""create cost_events hypertable and cost_aggregates

Revision ID: 001_cost_engine
Revises:
Create Date: 2026-03-03

This migration:
1. Enables the TimescaleDB extension (idempotent).
2. Creates the ``cost_events`` table and converts it to a hypertable.
3. Creates the ``cost_aggregates`` table for manual hourly rollups.
4. Creates the ``cost_hourly`` continuous aggregate materialized view.
5. Adds a continuous aggregate refresh policy (every 1 hour, lag 2 hours).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = "001_cost_engine"
down_revision = None
branch_labels = ("cost_engine",)
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 0. Enable TimescaleDB extension
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # ------------------------------------------------------------------
    # 1. cost_events table
    # ------------------------------------------------------------------
    op.create_table(
        "cost_events",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("task_type", sa.Text(), nullable=False, server_default="unclassified"),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Double(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="success"),
        sa.Column("complexity", sa.Double(), nullable=True),
        sa.PrimaryKeyConstraint("id", "time"),
    )

    # Indexes
    op.create_index("ix_cost_events_org_time", "cost_events", ["org_id", "time"])
    op.create_index("ix_cost_events_model", "cost_events", ["model"])
    op.create_index("ix_cost_events_task_type", "cost_events", ["task_type"])

    # Convert to hypertable (chunk_time_interval = 1 day)
    op.execute(
        "SELECT create_hypertable('cost_events', 'time', "
        "chunk_time_interval => INTERVAL '1 day', "
        "if_not_exists => TRUE);"
    )

    # ------------------------------------------------------------------
    # 2. cost_aggregates table (manual rollup fallback)
    # ------------------------------------------------------------------
    op.create_table(
        "cost_aggregates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bucket", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Double(), nullable=False, server_default="0"),
        sa.Column("total_input_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("avg_latency", sa.Double(), nullable=True),
        sa.Column("p95_latency", sa.Double(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_cost_agg_org_bucket", "cost_aggregates", ["org_id", "bucket"])
    op.create_index("ix_cost_agg_bucket", "cost_aggregates", ["bucket"])
    op.create_index(
        "uq_cost_agg_bucket_org_model_task",
        "cost_aggregates",
        ["bucket", "org_id", "model", "task_type"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 3. Continuous aggregate — cost_hourly
    # ------------------------------------------------------------------
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS cost_hourly
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 hour', time)                                 AS bucket,
            org_id,
            model,
            task_type,
            COUNT(*)                                                    AS call_count,
            SUM(cost_usd)                                               AS total_cost,
            SUM(input_tokens)                                           AS total_input_tokens,
            SUM(output_tokens)                                          AS total_output_tokens,
            AVG(latency_ms)                                             AS avg_latency,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)   AS p95_latency
        FROM cost_events
        GROUP BY bucket, org_id, model, task_type
        WITH NO DATA;
    """)

    # ------------------------------------------------------------------
    # 4. Automatic refresh policy for the continuous aggregate
    # ------------------------------------------------------------------
    op.execute("""
        SELECT add_continuous_aggregate_policy('cost_hourly',
            start_offset    => INTERVAL '3 hours',
            end_offset      => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour',
            if_not_exists   => TRUE
        );
    """)


def downgrade() -> None:
    # Remove refresh policy first
    op.execute(
        "SELECT remove_continuous_aggregate_policy('cost_hourly', if_exists => TRUE);"
    )
    # Drop continuous aggregate
    op.execute("DROP MATERIALIZED VIEW IF EXISTS cost_hourly CASCADE;")
    # Drop tables
    op.drop_table("cost_aggregates")
    op.drop_table("cost_events")
