# LLM Cost Efficiency Intelligence (Staxx) - Codebase Overview

> **Target Audience:** This document is explicitly tailored for an Large Language Model (LLM) agent or AI assistant to quickly understand the Staxx project architecture, components, and design philosophy before analyzing or modifying the broader codebase.

## 1. Project Identity & Positioning
- **Name:** Staxx Intelligence (also referred to as the "LLM CFO" or "LLM Cost Efficiency Intelligence").
- **Core Wedge / Value Proposition:** Staxx is not a pre-deployment model explorer. It is a **production intelligence layer**. It intercepts live production LLM traffic, calculates real-time API spend, and asynchronously runs "Shadow Evaluations" against cheaper model alternatives.
- **Goal:** To mathematically prove cost-saving swap opportunities without risking production degradation, using the customer's *actual production prompts* (no golden datasets required).
- **Core Rule:** "For each use case, which model gives equivalent quality at lower cost — and how confident are we?"

## 2. System Architecture (Clean Architecture)
The project is built on a decoupled, asynchronous architecture to ensure the capture layer adds minimal latency overhead to production systems.

```text
[Production App] --> [SDK Capture Layer] --(Async Publish)--> [Redis Streams]
                                                                     |
                                  +----------------------------------+----------------------------------+
                                  |                                                                     |
                         [Metrics Worker (Celery)]                                           [Shadow Eval Worker (Celery)]
                         - Calculates real-time costs                                        - Runs candidate models
                         - Aggregates latency (p50/p95/p99)                                  - Enforces N>=20 statistically valid runs
                         - Checks JSON validity                                              - Calculates TOPSIS & Pareto rankings
                                  |                                                                     |
                                  +-----------------------[ Storage Layer ]-----------------------------+
                                                          - PostgreSQL (Metadata, Eval Runs)
                                                          - TimescaleDB (Time-Series Cost Data)
                                                          - S3/MinIO (Raw outputs)
                                                                     |
                                                            [FastAPI Backend]
                                                                     |
                                                         [React Frontend Dashboard]
```

## 3. Directory Structure & Component Details

### `sdk/llm_intel/` (Python Drop-in Client)
- **Purpose:** Frictionless wrappers meant to intercept existing API calls with zero behavior change.
- **Implementation:** 
  - `client.py` overrides `AsyncOpenAI` and `AsyncAnthropic` base classes.
  - Measures execution time (`latency_ms`), extracts token counts, optionally tags `task_type`.
  - Dispatches metrics to the backend continuously without blocking the main application thread (`asyncio.create_task`).

### `backend/app/` (FastAPI + Celery)
- **Role:** Execution core handling ingestion, cost aggregation, and shadow evaluation dispatching.
- **`main.py` & `api/router.py`:** Standard FastAPI entrypoints housing HTTP REST routes (e.g., `/capture`).
- **`workers/celery_app.py`:** Celery app configuration pointing to Redis.
- **`workers/metrics_worker.py` (Implied):** Reads the Redis stream to perform token costing and metadata insertion into TimescaleDB/Postgres.
- **`models/` & `adapters/`:** Data definitions (Pydantic models, SQLAlchemy schemas) and standard unified interfaces for interacting with LLM providers during shadow evaluations.

### `frontend/` (React + Tailwind + Recharts)
- **Role:** The "Cost Intelligence" dashboard visualizing TimescaleDB aggregations.
- **Key File:** `src/App.jsx`
- **Design Philosophy:** Premium, high-end, luxury aesthetic (glassmorphism UI, smooth Framer Motion animations, complex Recharts).
- **Functionality:** Fetches `/api/v1/costs/breakdown` to display "Spend Topology by Task", active models, and projected savings based on shadow evaluation confidence limits.

### `infrastructure/` (Docker Compose)
- Contains configurations to spin up local instances of the storage layer.
- Components running locally: **Postgres (with TimescaleDB extension)**, **Redis** (for Celery queues and caching), and **MinIO** (for S3 storage abstraction of raw output logs).

## 4. Key Engineering Constraints & Logic Rules
When analyzing or generating code for Staxx, adhere to these architectural mandates outlined in `approval.md`:

1. **Async Evaluation Pipeline Only:** No synchronous evaluation calls. Every evaluation operation *must* be pushed to a Celery job queue.
2. **N>=20 Rule:** Shadow evaluations require a strict minimum of 20 runs. Any recommendation UI or scoring engine logic must gracefully handle the "Insufficient Data" state if `N < 20`.
3. **Statistical Validity:** The Scoring Engine V2 relies heavily on computing Confidence Intervals (CI), coefficient of variation (CV), Pareto frontiers, and TOPSIS rankings. Never rank models linearly based on single biased metrics.
4. **Zero Ground-Truth (No Golden Datasets):** Evaluate models objectively measuring variables like cost per task, latency p95, JSON schema validity, error rates, and output consistency, *not* semantic accuracy derived from potentially biased "LLM-as-a-judge" mechanisms.
5. **Model Versioning:** Always use precise model versions (e.g., `gpt-4o-2024-08-06`) in database queries and comparisons, never generic display names.

## 5. Summary for AI Context
This repository contains a full-stack, enterprise-targeted application. Most system optimizations should focus on safely decoupling ingestion (SDK) from heavy data-processing (Celery workers). Frontend enhancements should focus on communicating statistical certainty and cost-savings accurately, matching the existing "premium" glassmorphic UI patterns.

---
*Generated for LLM analysis and codebase architectural mapping.*
