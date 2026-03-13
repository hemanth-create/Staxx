-- ============================================================================
-- Staxx Intelligence - PostgreSQL + TimescaleDB Initialization
-- ============================================================================
-- This script is run automatically by Postgres on first startup.
-- It creates the TimescaleDB extension and base schema.
-- ============================================================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ─────────────────────────────────────────────────────────────────────────────
-- Core Staxx Tables (from app/models/*.py)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY,
    provider_model_id VARCHAR NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '{}',
    pricing JSONB NOT NULL DEFAULT '{}',
    valid_from TIMESTAMP WITH TIME ZONE,
    valid_until TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_model_versions_provider_model_id
    ON model_versions(provider_model_id);

-- Production calls (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS production_calls (
    id UUID NOT NULL,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    model_version_id UUID NOT NULL REFERENCES model_versions(id),
    task_type VARCHAR NOT NULL,
    cost_usd FLOAT NOT NULL,
    latency_ms FLOAT NOT NULL,
    PRIMARY KEY (id, ts)
);

CREATE INDEX IF NOT EXISTS ix_production_calls_model_version_id
    ON production_calls(model_version_id);

CREATE INDEX IF NOT EXISTS ix_production_calls_task_type
    ON production_calls(task_type);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('production_calls', 'ts', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS eval_runs (
    id UUID PRIMARY KEY,
    model_version_id UUID NOT NULL REFERENCES model_versions(id),
    task_type VARCHAR NOT NULL,
    prompt_hash VARCHAR NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    latency_ms FLOAT NOT NULL DEFAULT 0.0,
    cost_usd FLOAT NOT NULL DEFAULT 0.0,
    json_valid BOOLEAN,
    output_ref VARCHAR,
    n_run INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_eval_runs_model_version_id
    ON eval_runs(model_version_id);

CREATE INDEX IF NOT EXISTS ix_eval_runs_prompt_hash
    ON eval_runs(prompt_hash);

CREATE INDEX IF NOT EXISTS ix_eval_runs_task_type
    ON eval_runs(task_type);

-- ─────────────────────────────────────────────────────────────────────────────
-- Platform Layer Tables (from platform/db/models.py)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    slug VARCHAR NOT NULL UNIQUE,
    plan VARCHAR DEFAULT 'free',
    stripe_customer_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_organizations_slug ON organizations(slug);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR DEFAULT 'member',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);

CREATE INDEX IF NOT EXISTS ix_users_org_id ON users(org_id);

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key_hash VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_api_keys_org_id ON api_keys(org_id);

CREATE INDEX IF NOT EXISTS ix_api_keys_key_hash ON api_keys(key_hash);

CREATE TABLE IF NOT EXISTS org_invitations (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR NOT NULL,
    token_hash VARCHAR NOT NULL UNIQUE,
    role VARCHAR DEFAULT 'member',
    accepted BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_org_invitations_org_id ON org_invitations(org_id);

CREATE INDEX IF NOT EXISTS ix_org_invitations_token_hash ON org_invitations(token_hash);

CREATE INDEX IF NOT EXISTS ix_org_invitations_email ON org_invitations(email);

-- ─────────────────────────────────────────────────────────────────────────────
-- Initialization Complete
-- ─────────────────────────────────────────────────────────────────────────────
-- All tables created successfully. Alembic migrations will handle future schema changes.
