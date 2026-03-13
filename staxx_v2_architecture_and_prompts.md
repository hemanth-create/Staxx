# Staxx Intelligence — Architecture V2 & Build Prompts

> **Purpose:** Complete architecture reference + copy-paste LLM prompts to build every component of Staxx with production-grade UI.

---

## Table of Contents

1. [Project Identity](#1-project-identity)
2. [Redesigned Architecture](#2-redesigned-architecture)
3. [System Data Flow](#3-system-data-flow)
4. [Component Deep Dive](#4-component-deep-dive)
5. [Infrastructure & Deployment](#5-infrastructure--deployment)
6. [Critical Architecture Decisions](#6-critical-architecture-decisions)
7. [LLM Build Prompts](#7-llm-build-prompts)
   - [Prompt 1: Proxy Gateway](#prompt-1-proxy-gateway)
   - [Prompt 2: Task Classifier](#prompt-2-task-classifier)
   - [Prompt 3: Cost Engine & TimescaleDB](#prompt-3-cost-engine--timescaledb)
   - [Prompt 4: Shadow Evaluation Pipeline](#prompt-4-shadow-evaluation-pipeline)
   - [Prompt 5: Scoring Engine V2](#prompt-5-scoring-engine-v2)
   - [Prompt 6: Recommendation & ROI Engine](#prompt-6-recommendation--roi-engine)
   - [Prompt 7: Multi-Tenant Backend](#prompt-7-multi-tenant-backend)
   - [Prompt 8: Dashboard UI — Main Layout & Theme](#prompt-8-dashboard-ui--main-layout--theme)
   - [Prompt 9: Dashboard UI — Cost Topology Page](#prompt-9-dashboard-ui--cost-topology-page)
   - [Prompt 10: Dashboard UI — Shadow Eval Results & Swap Cards](#prompt-10-dashboard-ui--shadow-eval-results--swap-cards)
   - [Prompt 11: Dashboard UI — ROI Projections Page](#prompt-11-dashboard-ui--roi-projections-page)
   - [Prompt 12: Self-Serve Onboarding Flow](#prompt-12-self-serve-onboarding-flow)
   - [Prompt 13: Docker Compose & Infrastructure](#prompt-13-docker-compose--infrastructure)
   - [Prompt 14: Alert & Drift Monitoring System](#prompt-14-alert--drift-monitoring-system)

---

## 1. Project Identity

- **Name:** Staxx Intelligence (the "LLM CFO")
- **Tagline:** "Stop overpaying for AI. We prove it with your own data."
- **Core Value Proposition:** Staxx is a production intelligence layer. It intercepts live LLM traffic, calculates real-time API spend, and runs asynchronous shadow evaluations against cheaper model alternatives — using the customer's actual production prompts.
- **Goal:** Mathematically prove cost-saving model swap opportunities without risking production quality degradation. No golden datasets. No vibes. Just statistics.
- **Target Customer:** Any company spending $5k+/month on LLM APIs (OpenAI, Anthropic, Google, AWS Bedrock) for tasks like summarization, classification, extraction, code generation, or QA.

---

## 2. Redesigned Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INTEGRATION LAYER                               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │ Proxy Gateway │  │  SDK Drop-in │  │  Log Connector         │    │
│  │ (Zero-Code)   │  │  (2-Line)    │  │  (CloudWatch/Datadog)  │    │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘    │
│         │                  │                      │                  │
└─────────┼──────────────────┼──────────────────────┼─────────────────┘
          │                  │                      │
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   ASYNC INGESTION BUS (Redis Streams)               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────────┐
          ▼                   ▼                        ▼
┌──────────────────┐ ┌────────────────┐ ┌──────────────────────────┐
│ Task Classifier   │ │ Cost Engine    │ │ Prompt Complexity Scorer  │
│ (Auto-detect      │ │ (Real-time     │ │ (Difficulty grading per   │
│  task type from   │ │  spend per     │ │  prompt for model tier    │
│  prompt patterns) │ │  task/model)   │ │  matching)                │
└────────┬─────────┘ └───────┬────────┘ └─────────────┬────────────┘
         │                    │                        │
         ▼                    ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SHADOW EVALUATION PIPELINE                        │
│                                                                     │
│  ┌───────────────────┐    ┌───────────────────────────────────┐    │
│  │ Shadow Evaluator   │    │ Scoring Engine V2                 │    │
│  │ (Celery Workers)   │───▶│ (TOPSIS, Pareto, CI, CV)         │    │
│  │ N ≥ 20 runs min    │    │ No LLM-as-Judge — objective only │    │
│  └───────────────────┘    └──────────────┬────────────────────┘    │
│                                           │                         │
└───────────────────────────────────────────┼─────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  RECOMMENDATION & ROI ENGINE                        │
│                                                                     │
│  ┌────────────────────┐ ┌─────────────────┐ ┌───────────────────┐  │
│  │ Swap Recommendation │ │ ROI Projection  │ │ Alert & Drift     │  │
│  │ Generator           │ │ Engine          │ │ Monitor           │  │
│  │ "Switch X → Y,      │ │ Monthly savings │ │ Cost spikes,      │  │
│  │  save $Z/mo, 94%    │ │ vs subscription │ │ quality drift,    │  │
│  │  confidence"         │ │ break-even      │ │ new cheaper       │  │
│  └──────────┬─────────┘ └────────┬────────┘ │ models detected   │  │
│             │                     │          └──────────┬────────┘  │
└─────────────┼─────────────────────┼─────────────────────┼──────────┘
              │                     │                     │
              ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PLATFORM LAYER                                   │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐    │
│  │ Multi-Tenant Backend  │  │ Cost Intelligence Dashboard       │    │
│  │ (FastAPI + JWT +      │  │ (React + Tailwind + Recharts +   │    │
│  │  Stripe Billing +     │  │  Framer Motion)                  │    │
│  │  Tenant Isolation)    │  │                                   │    │
│  └──────────────────────┘  └──────────────────────────────────┘    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Self-Serve Onboarding (Sign up → API key → Data in 5 min)   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

STORAGE LAYER:
  PostgreSQL + TimescaleDB  │  Redis  │  S3/MinIO  │  Celery Workers
  (Metadata + Time-Series)  │ (Broker)│ (Raw I/O)  │ (Async Jobs)
```

---

## 3. System Data Flow

1. **Customer connects** via Proxy (swap base URL), SDK (2-line import), or Log Connector (pull from CloudWatch/Datadog).
2. **Task Classifier** auto-detects what the LLM call is doing — summarization, extraction, classification, code gen, QA, translation, etc.
3. **Cost Engine** tracks real spend per task type, per model, per customer in real-time via TimescaleDB.
4. **Shadow Evaluator** replays a statistically valid sample (N≥20) of real production prompts against cheaper candidate models — asynchronously, never touching production.
5. **Scoring Engine** compares outputs using objective metrics only: schema validity, latency p95, error rate, output length consistency, cost delta. No LLM-as-judge. Produces swap confidence scores with confidence intervals.
6. **Dashboard** shows: "You spent $12,400 on GPT-4o for summarization. Shadow evals prove Haiku handles it at 97% quality parity. Switch and save $9,800/mo."

---

## 4. Component Deep Dive

### 4.1 Integration Layer

#### Proxy Gateway (FASTEST — Zero Code)
- Customer swaps their LLM base URL to `https://proxy.staxx.ai/v1`. Staxx transparently forwards all calls to the real provider, logging everything.
- **They change ONE env var and you're capturing data.**
- Tech: FastAPI reverse proxy, async `httpx` forwarding, TLS termination, request/response logging to Redis Streams.

#### SDK Drop-in (FLEXIBLE — 2 Lines)
- Python/JS wrappers around `AsyncOpenAI`, `AsyncAnthropic`, `boto3` Bedrock clients.
- Adds optional `task_type` tagging, custom metadata fields, org-level API key binding.
- Fire-and-forget telemetry via `asyncio.create_task` — zero latency overhead.

#### Log Connector (ENTERPRISE — No Infra Changes)
- Pulls existing logs from AWS CloudWatch, Datadog, LangSmith, or custom S3 buckets.
- Customer doesn't change anything in their infra. We just read their logs.
- Celery beat schedulers poll on configurable intervals. S3 event triggers for real-time.

### 4.2 Intelligence Pipeline

#### Task Classifier (AUTO)
- Auto-detects task type from prompt patterns: summarization, extraction, classification, code generation, QA, translation, creative writing, multi-turn chat.
- **This is the KEY insight** — a company using GPT-4o for simple classification is burning money. We need to detect that automatically.
- Tech: Lightweight fine-tuned classifier (DistilBERT or rule engine), prompt pattern matching, few-shot clustering for custom task types.

#### Prompt Complexity Scorer (CORE)
- Not all summarization is equal. A 200-token summary request ≠ a 50k-token document condensation.
- Scores prompt difficulty based on: token count ratio, instruction complexity, output schema constraints, chain-of-thought depth, context window utilization.
- This score determines which model tier is appropriate for each specific prompt.

#### Cost Engine (REAL-TIME)
- Tracks actual spend per task type, per model, per customer.
- Maintains a live pricing catalog across all providers: OpenAI, Anthropic, Google, Mistral, Llama/Bedrock, Cohere, etc.
- TimescaleDB time-series aggregation for trend analysis, anomaly detection, and forecasting.

#### Shadow Evaluator (ASYNC)
- Takes a statistically valid sample of real production prompts and replays them against cheaper candidate models.
- **N ≥ 20 strict minimum** per model per task type. Any scoring below this threshold shows "Insufficient Data."
- Runs entirely asynchronously via Celery workers. Never adds latency to production. Customer sleeps well.
- Output storage in S3/MinIO for audit trail.

#### Scoring Engine V2 (STATS)
- Compares shadow outputs using **objective metrics ONLY**:
  - Schema/JSON validity rate
  - Latency p50/p95/p99
  - Error rate
  - Output length consistency (CV)
  - Cost per task delta
- **No LLM-as-judge.** Enterprise customers don't trust "GPT-4 says Haiku is fine." They DO trust "across 847 production calls, schema validity was 99.2% vs 99.4%, latency p95 dropped 40%, cost dropped 78%."
- Produces: TOPSIS multi-criteria rankings, Pareto frontier visualization, confidence intervals via bootstrap resampling, swap confidence scores.

### 4.3 Recommendation & ROI Engine

#### Swap Recommendation Generator
- Produces concrete, actionable swap cards:
  > "Switch your **summarization** task from **Claude Opus → Claude Haiku**.
  > Projected savings: **$4,200/mo**. Confidence: **94%**. Quality parity: **PASS**."
- Configurable risk tolerance thresholds per customer. Approval workflows for enterprise.

#### ROI Projection Engine
- Monthly/quarterly ROI projections based on actual traffic volume trends.
- Shows break-even timeline: Staxx subscription cost vs savings generated.
- **This IS your sales pitch.** The dashboard pays for itself in the first invoice.

#### Alert & Drift Monitor
- Continuous monitoring for: cost spikes, model deprecations, new cheaper models entering market, quality drift after swaps.
- Celery beat cron jobs, webhook notifications, Slack/email integrations.

### 4.4 Platform Layer

#### Multi-Tenant Backend
- Org-level isolation with row-level security in Postgres.
- JWT auth, API key management, usage-based billing metering via Stripe.
- Each customer gets their own namespace across all data tables.

#### Cost Intelligence Dashboard
- Premium glassmorphic UI. React + Tailwind + Recharts + Framer Motion.
- Pages: Spend Topology, Model Utilization Heatmap, Swap Cards with Confidence Meters, ROI Waterfall, Alert Feed.
- WebSocket for live cost feeds. Exportable PDF reports.

#### Self-Serve Onboarding
- Sign up → get API key + proxy URL → see data in < 5 minutes.
- Free tier: first 10k requests/month.
- Automated provisioning pipeline, health check endpoints, onboarding wizard UI.

---

## 5. Infrastructure & Deployment

### Storage Layer
| Component | Role |
|---|---|
| PostgreSQL + TimescaleDB | Metadata, eval runs, time-series cost data |
| Redis | Celery broker, streams, caching, rate limiting |
| S3 / MinIO | Raw prompt/output storage, audit trail |
| Celery Workers | Shadow evals, metrics aggregation, alerts |

### Deployment Phases

**Phase 1 — MVP (Cost: ~$50/mo)**
Single Docker Compose. Postgres + Redis + FastAPI + React. Deploy on one EC2 instance or Railway.

**Phase 2 — First 10 Customers (Cost: ~$300/mo)**
Add TimescaleDB extension, Celery workers on separate containers, S3 for output storage. Move to ECS or managed K8s.

**Phase 3 — Scale**
Multi-region proxy nodes (latency matters for transparent forwarding), horizontal Celery worker scaling, Postgres read replicas, CDN for dashboard. Terraform everything.

---

## 6. Critical Architecture Decisions

**Why Proxy-first?**
Lowest friction onboarding wins in B2B SaaS. Customer changes ONE env var. You see data in 5 minutes. SDK and log connectors come later as upsell paths.

**Why auto task classification?**
Customers don't know what tasks they're running. Auto-detecting "summarization" vs "extraction" vs "code gen" is what lets you say "you're using Opus for simple classification — that's an $8k/mo waste."

**Why N≥20 and no LLM-as-judge?**
Enterprise customers won't trust "GPT-4 says Haiku is good enough." They WILL trust "across 847 real production calls, schema validity was 99.2% vs 99.4%, latency p95 dropped 40%, cost dropped 78%."

**Why async shadow evals?**
You never add latency to production. The proxy forwards instantly. Evals happen in background workers. Zero risk to the customer's system.

---










## 7. LLM Build Prompts

> **How to use:** Copy each prompt below and paste it directly into an LLM (Claude, GPT-4, etc.) to generate production-ready code for that component. Each prompt is self-contained with full context, constraints, file structure, and quality expectations.

---

### Prompt 1: Proxy Gateway

```
You are a senior Python backend engineer building a transparent LLM API proxy for a startup called "Staxx Intelligence."

## CONTEXT
Staxx intercepts production LLM API calls to analyze costs and suggest cheaper model alternatives. The Proxy Gateway is the primary integration path — customers swap their LLM provider base URL to ours, and we transparently forward everything while logging request/response data.

## REQUIREMENTS

Build a FastAPI-based reverse proxy with the following:

### Core Proxy Logic
- Accept any OpenAI-compatible API call at `POST /v1/chat/completions`, `POST /v1/completions`, `POST /v1/embeddings`
- Accept Anthropic-compatible calls at `POST /v1/messages`
- Transparently forward the request to the real provider (OpenAI, Anthropic, etc.) using async httpx
- Support streaming responses (SSE) — proxy the stream chunk-by-chunk back to the caller with zero buffering delay
- Return the exact response the real provider would return — zero behavior change for the customer

### Authentication & Tenant Identification
- Customers pass their real provider API key in the standard Authorization header
- Customers pass their Staxx org API key via a custom `X-Staxx-Key` header
- Validate the Staxx key against a Postgres lookup to identify the tenant
- If X-Staxx-Key is missing or invalid, return 401

### Async Telemetry Logging (CRITICAL: Non-blocking)
- After forwarding the response, asynchronously publish a telemetry event to a Redis Stream (stream name: `staxx:telemetry`)
- The telemetry event must include:
  - `org_id`, `timestamp`, `provider` (openai/anthropic/bedrock)
  - `model` (exact version string, e.g., gpt-4o-2024-08-06)
  - `input_tokens`, `output_tokens` (extracted from provider response)
  - `latency_ms` (measured end-to-end)
  - `request_body` (the full prompt — stored for shadow eval replay)
  - `response_body` (the full response — for comparison baseline)
  - `status_code`, `error` (if any)
- This logging MUST NOT block the response to the customer. Use `asyncio.create_task` or background tasks.
- If Redis is down, log to a local fallback file and continue serving. Never fail the customer's request.

### File Structure
```
proxy/
├── main.py              # FastAPI app, lifespan, CORS
├── routes/
│   ├── openai_proxy.py  # /v1/chat/completions, /v1/completions, /v1/embeddings
│   └── anthropic_proxy.py # /v1/messages
├── middleware/
│   ├── auth.py          # X-Staxx-Key validation
│   └── telemetry.py     # Async Redis Stream publisher
├── services/
│   ├── forwarder.py     # httpx async forwarding logic (streaming + non-streaming)
│   └── token_extractor.py # Extract token counts from provider responses
├── config.py            # Settings via pydantic-settings (env vars)
└── requirements.txt
```

### Technical Constraints
- Python 3.11+, FastAPI, httpx (async), redis-py (async), pydantic-settings
- All I/O must be async. No blocking calls anywhere.
- Latency overhead of the proxy must be < 5ms (excluding network to provider)
- Handle provider errors gracefully — if OpenAI returns 429, forward that 429 to the customer as-is
- Add structured logging (structlog) with org_id context

### Code Quality
- Full type hints on all functions
- Docstrings on all public functions
- Error handling with custom exception classes
- Config via environment variables with sensible defaults

Generate the complete, production-ready code for all files.
```

---

### Prompt 2: Task Classifier

```
You are a senior ML/Python engineer building an automatic task classifier for LLM API calls.

## CONTEXT
Staxx Intelligence intercepts production LLM API calls and needs to automatically classify what type of task each call is performing. This classification is critical — it's what lets us say "you're spending $8k/mo on GPT-4o for simple classification tasks that Haiku could handle."

## REQUIREMENTS

Build a task classification module that analyzes the prompt content of intercepted LLM calls and classifies them into task types.

### Supported Task Types
- `summarization` — Condensing longer text into shorter text
- `extraction` — Pulling structured data from unstructured text (names, dates, entities, etc.)
- `classification` — Categorizing input into predefined labels/categories
- `code_generation` — Writing, completing, or explaining code
- `question_answering` — Answering questions based on provided context
- `translation` — Converting text between languages
- `creative_writing` — Generating original creative content (stories, marketing copy, etc.)
- `structured_output` — Generating JSON, XML, YAML, or other formatted outputs
- `multi_turn_chat` — Conversational interactions (detected via message history length)
- `other` — Fallback when confidence is below threshold

### Classification Strategy (Hybrid — Two Tiers)

**Tier 1: Rule Engine (Fast, Free, Runs First)**
- Pattern matching on system prompts and user prompts
- Keyword detection: "summarize", "extract", "classify", "translate", "write code", JSON schema presence, etc.
- Structural signals: message array length > 4 = likely multi_turn_chat, presence of `response_format: json_object` = structured_output
- Output format hints in the prompt (JSON, table, list, code blocks)
- If Tier 1 confidence ≥ 0.85, use that classification. Skip Tier 2.

**Tier 2: Lightweight ML Classifier (Fallback)**
- Use a small transformer (DistilBERT or similar) fine-tuned on labeled prompt examples
- Input: first 512 tokens of the concatenated system + user prompt
- Output: task_type + confidence score
- Only called if Tier 1 confidence < 0.85

### Output Schema
```python
class TaskClassification(BaseModel):
    task_type: str              # e.g., "summarization"
    confidence: float           # 0.0 to 1.0
    classification_tier: str    # "rule_engine" or "ml_classifier"
    signals: list[str]          # e.g., ["keyword:summarize", "system_prompt_pattern:condensation"]
    prompt_complexity_score: float  # 0.0 (trivial) to 1.0 (highly complex)
```

### Prompt Complexity Scorer (Integrated)
Alongside task classification, compute a complexity score based on:
- Total token count (input + expected output)
- Instruction specificity (vague vs. detailed system prompts)
- Output schema constraints (free-form text vs. strict JSON schema)
- Context window utilization (% of model's context used)
- Chain-of-thought indicators (step-by-step, reasoning, "think through")

### File Structure
```
classifier/
├── __init__.py
├── engine.py            # Main classify() function — orchestrates Tier 1 → Tier 2
├── rule_engine.py       # Tier 1: Pattern matching, keyword detection, structural signals
├── ml_classifier.py     # Tier 2: DistilBERT inference (lazy-loaded, optional)
├── complexity_scorer.py # Prompt complexity scoring
├── schemas.py           # Pydantic models (TaskClassification, etc.)
├── patterns.py          # Compiled regex patterns and keyword lists
└── tests/
    ├── test_rule_engine.py
    └── test_classifier.py
```

### Technical Constraints
- Python 3.11+, pydantic v2, optional: transformers + torch (for Tier 2)
- Tier 1 must complete in < 2ms per call
- Tier 2 must complete in < 50ms per call
- The module must work without PyTorch installed (Tier 2 gracefully degrades to Tier 1 only)
- Full type hints, docstrings, comprehensive test cases

Generate the complete, production-ready code for all files including tests with at least 10 diverse prompt examples.
```

---

### Prompt 3: Cost Engine & TimescaleDB

```
You are a senior Python backend engineer building a real-time cost tracking engine for LLM API calls.

## CONTEXT
Staxx Intelligence tracks how much companies spend on LLM APIs in real-time. The Cost Engine consumes telemetry events from a Redis Stream, calculates the cost of each call using a pricing catalog, and stores time-series cost data in TimescaleDB for trend analysis and dashboarding.

## REQUIREMENTS

### Pricing Catalog
- Maintain a provider pricing table with per-token costs (input and output separately) for all major models:
  - OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o1, o1-mini (use exact version strings)
  - Anthropic: claude-opus-4-20250514, claude-sonnet-4-20250514, claude-haiku-4-20250514 (and older 3.5 versions)
  - Google: gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash
  - Meta via Bedrock: llama-3.1-70b, llama-3.1-8b
  - Mistral: mistral-large, mistral-small, mistral-nemo
- Pricing must be configurable (YAML or DB table) and easy to update when providers change prices
- Support custom markup percentages per org (for resellers)

### Celery Worker: `cost_metrics_worker`
- Consumes events from Redis Stream `staxx:telemetry`
- For each event:
  1. Look up model pricing from catalog
  2. Calculate: `cost = (input_tokens * input_price) + (output_tokens * output_price)`
  3. Insert a row into TimescaleDB `cost_events` hypertable
  4. Update running aggregations in `cost_aggregates` table (hourly rollups)

### TimescaleDB Schema
```sql
-- Raw cost events (hypertable, auto-partitioned by time)
CREATE TABLE cost_events (
    time           TIMESTAMPTZ NOT NULL,
    org_id         UUID NOT NULL,
    model          TEXT NOT NULL,
    task_type      TEXT NOT NULL,
    input_tokens   INTEGER,
    output_tokens  INTEGER,
    cost_usd       DOUBLE PRECISION,
    latency_ms     INTEGER,
    status         TEXT,  -- 'success', 'error'
    complexity     DOUBLE PRECISION
);
SELECT create_hypertable('cost_events', 'time');

-- Continuous aggregate for dashboard (materialized hourly)
CREATE MATERIALIZED VIEW cost_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    org_id,
    model,
    task_type,
    COUNT(*) AS call_count,
    SUM(cost_usd) AS total_cost,
    SUM(input_tokens) AS total_input_tokens,
    SUM(output_tokens) AS total_output_tokens,
    AVG(latency_ms) AS avg_latency,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency
FROM cost_events
GROUP BY bucket, org_id, model, task_type;
```

### API Endpoints (FastAPI)
- `GET /api/v1/costs/breakdown?org_id=X&period=7d` — Cost breakdown by model and task type
- `GET /api/v1/costs/timeline?org_id=X&granularity=hourly&period=30d` — Time-series cost data for charts
- `GET /api/v1/costs/top-spenders?org_id=X` — Top 5 most expensive task/model combos
- `GET /api/v1/costs/summary?org_id=X` — Total spend, request count, avg cost per request, month-over-month trend

### File Structure
```
cost_engine/
├── __init__.py
├── pricing_catalog.py     # Model pricing lookup with YAML config
├── calculator.py          # Cost calculation logic
├── worker.py              # Celery worker consuming Redis Stream
├── db/
│   ├── models.py          # SQLAlchemy + TimescaleDB models
│   ├── migrations/        # Alembic migrations including hypertable setup
│   └── queries.py         # Optimized TimescaleDB queries for API endpoints
├── api/
│   ├── router.py          # FastAPI router with all cost endpoints
│   └── schemas.py         # Response models
├── pricing.yaml           # Provider pricing configuration
└── tests/
    └── test_calculator.py
```

### Technical Constraints
- Python 3.11+, FastAPI, Celery, SQLAlchemy 2.0 (async), redis-py, psycopg (async)
- All DB queries must use TimescaleDB-specific optimizations (time_bucket, continuous aggregates)
- Pricing catalog must be cached in memory with a 1-hour refresh interval
- Cost calculations must handle edge cases: missing token counts (estimate from char length), unknown models (log warning, use fallback pricing)

Generate the complete, production-ready code for all files.
```




---

### Prompt 4: Shadow Evaluation Pipeline

```
You are a senior Python engineer building an asynchronous shadow evaluation pipeline.

## CONTEXT
Staxx Intelligence proves cost savings by replaying real production prompts against cheaper LLM models. The Shadow Evaluator picks a sample of actual customer prompts, sends them to candidate models, and stores the outputs for comparison — all asynchronously, never touching production traffic.

## REQUIREMENTS

### Shadow Eval Flow
1. A Celery beat scheduler periodically selects prompts eligible for shadow evaluation:
   - Source: `cost_events` table, filtered by task_type and model
   - Selection: Random sample, ensuring diversity across task types
   - Exclusions: Prompts already evaluated, prompts containing PII (basic regex filter), prompts from opted-out orgs
2. For each selected prompt, dispatch a Celery task to replay it against candidate models:
   - Candidate selection: All models cheaper than the original model, filtered by task_type compatibility
   - Example: If original was `gpt-4o` for `summarization`, candidates might be `gpt-4o-mini`, `claude-haiku`, `gemini-flash`, `llama-3.1-70b`
3. Each candidate evaluation:
   - Send the exact same prompt (system + user messages) to the candidate model via a unified adapter
   - Measure: latency_ms, output_tokens, error (if any)
   - Validate: JSON schema validity (if output was expected to be JSON), output not empty, output not truncated
   - Store: Full output in S3/MinIO, metadata in Postgres `shadow_eval_runs` table
4. Track progress: For each (org_id, task_type, original_model, candidate_model) tuple, track how many valid runs exist. Surface "Insufficient Data" if N < 20.

### Unified Model Adapter
- A single interface that routes to any LLM provider:
  - OpenAI (via httpx to api.openai.com)
  - Anthropic (via httpx to api.anthropic.com)
  - AWS Bedrock (via boto3 async)
  - Google Vertex (via httpx)
- Each adapter normalizes the response to a common schema: `text_output`, `input_tokens`, `output_tokens`, `latency_ms`, `error`
- API keys for shadow evals are Staxx-owned (not the customer's keys)

### Database Schema
```sql
CREATE TABLE shadow_eval_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL,
    task_type       TEXT NOT NULL,
    original_model  TEXT NOT NULL,
    candidate_model TEXT NOT NULL,
    prompt_hash     TEXT NOT NULL,          -- SHA256 of the prompt for dedup
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    latency_ms      INTEGER,
    cost_usd        DOUBLE PRECISION,
    json_valid      BOOLEAN,               -- NULL if not a JSON task
    output_empty    BOOLEAN,
    output_truncated BOOLEAN,
    error           TEXT,
    s3_output_key   TEXT,                   -- S3 path to full output
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE shadow_eval_progress (
    org_id          UUID NOT NULL,
    task_type       TEXT NOT NULL,
    original_model  TEXT NOT NULL,
    candidate_model TEXT NOT NULL,
    total_runs      INTEGER DEFAULT 0,
    valid_runs      INTEGER DEFAULT 0,
    last_run_at     TIMESTAMPTZ,
    PRIMARY KEY (org_id, task_type, original_model, candidate_model)
);
```

### File Structure
```
shadow_eval/
├── __init__.py
├── scheduler.py           # Celery beat task: select prompts, dispatch eval jobs
├── evaluator.py           # Celery worker: run single prompt against candidate model
├── adapters/
│   ├── base.py            # Abstract adapter interface
│   ├── openai_adapter.py
│   ├── anthropic_adapter.py
│   ├── bedrock_adapter.py
│   └── google_adapter.py
├── candidate_selector.py  # Given original model + task, select cheaper candidates
├── validators.py          # JSON schema validation, output quality checks
├── storage.py             # S3/MinIO upload for raw outputs
├── db/
│   ├── models.py          # SQLAlchemy models
│   └── queries.py         # Progress tracking queries
└── tests/
    ├── test_evaluator.py
    └── test_candidate_selector.py
```

### Technical Constraints
- Python 3.11+, Celery, httpx (async), boto3, SQLAlchemy 2.0
- All external API calls must have timeouts (30s default), retries (3x with exponential backoff)
- PII filtering: Basic regex for emails, phone numbers, SSNs — skip prompts that match
- Rate limiting: Respect provider rate limits; use a token bucket per provider
- Idempotency: Same prompt + candidate model = skip if already evaluated (check prompt_hash)

Generate the complete, production-ready code for all files.
```



### Finished until here



---

### Prompt 5: Scoring Engine V2

```
You are a senior data scientist / Python engineer building a statistical scoring engine for LLM model comparisons.

## CONTEXT
Staxx Intelligence runs shadow evaluations (replaying real production prompts against cheaper models). The Scoring Engine analyzes those results and determines — with statistical rigor — whether a cheaper model can replace the current one for a given task type.

## REQUIREMENTS

### Input
- Query `shadow_eval_runs` for a specific (org_id, task_type, original_model, candidate_model) tuple
- Minimum N ≥ 20 valid runs required. If N < 20, return status "insufficient_data" with current count.

### Metrics to Compute (Per Candidate Model)
1. **Cost Savings:** Average cost delta per request + projected monthly savings (extrapolated from traffic volume)
2. **Latency Comparison:** p50, p95, p99 latency for candidate vs original. Delta and % change.
3. **JSON Schema Validity Rate:** % of outputs that pass JSON validation (if applicable to task type)
4. **Error Rate:** % of runs that returned errors
5. **Output Consistency:** Coefficient of variation (CV) of output token length — measures how stable the candidate's outputs are
6. **Output Length Ratio:** Average output tokens (candidate) / average output tokens (original) — flags truncation or verbosity

### Statistical Methods
- **Confidence Intervals:** 95% CI on all metrics using bootstrap resampling (1000 iterations)
- **TOPSIS Ranking:** Multi-criteria decision analysis across [cost, latency_p95, json_validity, error_rate, consistency]. Weights configurable per org. Default: cost=0.35, latency=0.25, quality=0.20, error=0.15, consistency=0.05
- **Pareto Frontier:** Identify candidates that are not dominated on any metric pair (cost vs quality, cost vs latency)
- **Swap Confidence Score:** A single 0-100 score representing overall confidence in recommending the swap. Computed from: statistical significance of cost savings + quality parity + sample size adequacy.

### Output Schema
```python
class ModelScore(BaseModel):
    candidate_model: str
    sample_size: int
    cost_savings_monthly_usd: float
    cost_savings_ci_95: tuple[float, float]
    latency_p50_ms: float
    latency_p95_ms: float
    latency_delta_pct: float
    json_validity_rate: float | None
    error_rate: float
    output_consistency_cv: float
    output_length_ratio: float
    topsis_score: float            # 0.0 to 1.0
    is_pareto_optimal: bool
    swap_confidence: int           # 0 to 100
    swap_recommendation: str       # "STRONG_YES", "YES", "MAYBE", "NO", "INSUFFICIENT_DATA"

class ScoringResult(BaseModel):
    org_id: str
    task_type: str
    original_model: str
    original_monthly_cost: float
    candidates: list[ModelScore]
    best_candidate: str | None     # Highest swap_confidence with >= "YES"
    generated_at: datetime
```

### File Structure
```
scoring/
├── __init__.py
├── engine.py              # Main score() function — orchestrates everything
├── metrics.py             # Individual metric calculators
├── statistics.py          # Bootstrap CI, significance tests
├── topsis.py              # TOPSIS multi-criteria ranking
├── pareto.py              # Pareto frontier detection
├── confidence.py          # Swap confidence score calculator
├── schemas.py             # Pydantic output models
└── tests/
    ├── test_engine.py
    ├── test_topsis.py
    └── test_pareto.py
```

### Technical Constraints
- Python 3.11+, numpy, scipy (for statistics), pydantic v2
- No pandas dependency (use numpy for performance)
- All computation must complete in < 500ms for up to 1000 eval runs
- Full type hints, docstrings

Generate the complete, production-ready code for all files including tests with realistic mock data.
```


### Finished until here
---

### Prompt 6: Recommendation & ROI Engine

```
You are a senior Python engineer building a recommendation and ROI projection engine.

## CONTEXT
Staxx Intelligence has scored candidate models against original models for cost savings. The Recommendation Engine consumes those scores and generates actionable, customer-facing swap recommendations with dollar amounts and ROI projections.

## REQUIREMENTS

### Swap Recommendation Generator
- Consumes `ScoringResult` objects from the Scoring Engine
- For each candidate with `swap_recommendation` in ("STRONG_YES", "YES"):
  - Generate a human-readable recommendation card
  - Include: task_type, current_model → recommended_model, monthly savings, confidence %, key metrics summary
- Group recommendations by task_type for dashboard display
- Support org-level risk tolerance settings: "conservative" (only STRONG_YES), "moderate" (STRONG_YES + YES), "aggressive" (STRONG_YES + YES + MAYBE)

### ROI Projection Engine
- Given current monthly spend and projected savings from all approved swaps:
  - Calculate: total monthly savings, annual savings, % cost reduction
  - Calculate: break-even timeline (how many months until cumulative savings > Staxx subscription cost)
  - Generate: 12-month savings projection with confidence bands (using CI from scoring engine)
  - Generate: waterfall chart data (original spend → savings per task type → new projected spend)

### Alert & Drift Monitor
- After a swap is implemented, continuously monitor:
  - Quality drift: Are error rates or JSON validity rates changing?
  - Cost drift: Is the new model's pricing changing?
  - Volume drift: Is traffic volume changing (affecting absolute savings)?
  - New opportunity detection: Has a new cheaper model been released?
- Generate alerts when any metric drifts beyond configurable thresholds

### API Endpoints
- `GET /api/v1/recommendations?org_id=X` — All active swap recommendations
- `GET /api/v1/roi/projection?org_id=X` — 12-month ROI projection
- `GET /api/v1/roi/waterfall?org_id=X` — Waterfall chart data
- `POST /api/v1/recommendations/{id}/approve` — Mark a swap as approved (for tracking)
- `POST /api/v1/recommendations/{id}/dismiss` — Dismiss a recommendation
- `GET /api/v1/alerts?org_id=X` — Active alerts

### File Structure
```
recommendations/
├── __init__.py
├── generator.py           # Swap recommendation generation
├── roi_engine.py          # ROI projections, waterfall data
├── drift_monitor.py       # Celery beat: continuous monitoring + alerting
├── api/
│   ├── router.py          # FastAPI endpoints
│   └── schemas.py         # Request/response models
├── db/
│   ├── models.py          # Recommendations, approvals, alerts tables
│   └── queries.py
└── tests/
    └── test_generator.py
```

Generate the complete, production-ready code for all files.
```
### FInished until here:
---

### Prompt 7: Multi-Tenant Backend

```
You are a senior Python backend engineer building a multi-tenant SaaS backend for Staxx Intelligence.

## CONTEXT
Staxx serves multiple companies (orgs) from a single deployment. Each org must have strict data isolation, API key management, and usage-based billing.

## REQUIREMENTS

### Multi-Tenant Architecture
- Tenant identification via JWT tokens (dashboard) or API keys (proxy, SDK)
- Row-level security: All database queries filter by `org_id`
- Tenant middleware: FastAPI dependency that extracts org_id from JWT/API key and injects it into the request state
- API key management: Each org can create/revoke API keys. Keys are hashed (SHA256) in the DB.

### Auth System
- JWT-based auth for dashboard users (email/password login)
- API key auth for programmatic access (proxy, SDK, API)
- Role-based access: `owner`, `admin`, `viewer` per org
- Org invitations: Owners can invite users via email

### Billing Integration (Stripe)
- Usage-based billing: Track request counts per org per month
- Plans: Free (10k req/mo), Starter ($99/mo, 100k req/mo), Growth ($499/mo, 1M req/mo), Enterprise (custom)
- Stripe webhook handler for subscription events
- Usage reporting to Stripe metered billing

### Database Schema
```sql
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    plan        TEXT DEFAULT 'free',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    risk_tolerance TEXT DEFAULT 'moderate',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    org_id      UUID REFERENCES organizations(id),
    role        TEXT DEFAULT 'viewer',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID REFERENCES organizations(id),
    key_hash    TEXT NOT NULL,
    key_prefix  TEXT NOT NULL,  -- First 8 chars for identification
    label       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    revoked_at  TIMESTAMPTZ
);
```

### File Structure
```
platform/
├── __init__.py
├── auth/
│   ├── jwt_handler.py     # JWT creation/validation
│   ├── api_key_auth.py    # API key validation
│   ├── password.py        # bcrypt hashing
│   └── dependencies.py    # FastAPI dependencies (get_current_user, get_current_org)
├── billing/
│   ├── stripe_client.py   # Stripe SDK wrapper
│   ├── webhooks.py        # Stripe webhook handler
│   └── usage_tracker.py   # Request counting per org
├── api/
│   ├── router.py          # Auth endpoints (login, signup, invite, API key CRUD)
│   └── schemas.py
├── db/
│   ├── models.py
│   └── queries.py
└── middleware/
    └── tenant.py          # Tenant isolation middleware
```

Generate the complete, production-ready code for all files.
```
### Finished Until Here!!
---

### Prompt 8: Dashboard UI — Main Layout & Theme

```
You are an elite frontend engineer and UI designer building a premium SaaS dashboard for Staxx Intelligence — an LLM cost optimization platform.

## DESIGN DIRECTION
- **Aesthetic:** Dark-mode, glassmorphic, premium fintech feel. Think Linear meets Stripe Dashboard meets Bloomberg Terminal.
- **Font:** "Inter" for body, "JetBrains Mono" for numbers/metrics/code. Import from Google Fonts.
- **Color Palette:**
  - Background: #09090b (zinc-950)
  - Surface: rgba(255,255,255,0.03) with 1px border rgba(255,255,255,0.06)
  - Glass panels: backdrop-filter: blur(20px), subtle gradient borders
  - Primary accent: #0ea5e9 (sky-500)
  - Success/Savings: #22c55e (green-500)
  - Warning: #f59e0b (amber-500)
  - Danger/Cost: #ef4444 (red-500)
  - Text primary: #fafafa, Text secondary: #a1a1aa, Text muted: #52525b
- **Motion:** Framer Motion for page transitions, staggered list reveals, number counting animations. Smooth but not excessive.
- **Charts:** Recharts with custom dark theme. Gradient fills under lines. Glowing dots on data points. Animated on mount.
- **Key UI Pattern:** "Metric cards" — glassmorphic rectangles showing a label, a large number, a trend arrow (up/down with color), and a sparkline.

## REQUIREMENTS

### Main Layout Shell
Build the main application layout with:
1. **Sidebar** (fixed, 240px wide):
   - Staxx logo at top (stylized "S" icon + "Staxx" text)
   - Navigation items with icons (use Lucide React): Dashboard, Cost Topology, Shadow Evals, Swap Recommendations, ROI Projections, Alerts, Settings
   - Active state: left accent border + subtle background highlight
   - Org switcher dropdown at bottom
   - Collapse to icon-only mode on mobile

2. **Top Bar** (sticky):
   - Breadcrumb navigation
   - Time range selector (24h, 7d, 30d, 90d, Custom) — styled as pill buttons
   - Search bar (glassmorphic input)
   - Notification bell with badge count
   - User avatar + dropdown

3. **Main Content Area**:
   - Smooth page transitions (fade + slight slide)
   - Loading skeletons that match the glassmorphic style

4. **Dashboard Home Page** (the default view):
   - Top row: 4 metric cards — "Total Spend (MTD)", "Potential Savings", "Active Models", "API Calls (MTD)"
   - Each card has: large number with counting animation, trend percentage vs last period, sparkline chart
   - Second row: "Spend Over Time" area chart (full width, gradient fill, animated on mount)
   - Third row: Two panels side by side:
     - Left: "Top Spend by Task" — horizontal bar chart
     - Right: "Active Swap Recommendations" — list of swap cards with confidence badges

### Tech Stack
- React 18 + Vite
- Tailwind CSS (dark mode default)
- Framer Motion for animations
- Recharts for all charts
- Lucide React for icons
- React Router v6 for navigation

### File Structure
```
src/
├── App.jsx                # Router setup, layout wrapper
├── layouts/
│   └── DashboardLayout.jsx # Sidebar + TopBar + content area
├── components/
│   ├── Sidebar.jsx
│   ├── TopBar.jsx
│   ├── MetricCard.jsx     # Reusable glassmorphic metric card
│   ├── SparkLine.jsx      # Tiny inline chart for metric cards
│   ├── GlassPanel.jsx     # Reusable glassmorphic container
│   ├── TimeRangeSelector.jsx
│   └── LoadingSkeleton.jsx
├── pages/
│   └── DashboardHome.jsx  # The main overview page
├── hooks/
│   └── useCountUp.js      # Animated number counting hook
├── theme/
│   └── chartTheme.js      # Recharts custom dark theme config
└── index.css              # Tailwind imports + custom glass utilities
```

## CRITICAL UI RULES
- Every number that represents money must use `$X,XXX` formatting with counting animation on mount
- Every percentage must show a colored arrow (green up = good for savings, red up = bad for costs)
- Charts must have gradient fills (not flat colors), animated on mount, with glowing hover tooltips
- All panels must have the glassmorphic treatment: semi-transparent bg, blur, subtle border
- Spacing must be generous — this is premium software, not a cramped admin panel
- Mobile responsive: sidebar collapses, metric cards stack vertically

Generate the complete code for ALL files. Make it stunning. This dashboard IS the product — it's what sells the startup.
```
### Finished until HERE!!!
---

### Prompt 9: Dashboard UI — Cost Topology Page

```
You are an elite frontend engineer building the "Cost Topology" page for the Staxx Intelligence dashboard.

## CONTEXT
This page is where customers see EXACTLY where their LLM money is going. It's the "aha moment" — the first time they realize they're overspending on certain task types.

## EXISTING DESIGN SYSTEM
(Copy the full design direction from Prompt 8 here — colors, fonts, glassmorphic rules, Framer Motion, Recharts theme, etc.)

## PAGE REQUIREMENTS

### Hero Section: "Spend Topology"
- Title: "Spend Topology" with subtitle: "Where your LLM budget goes"
- Time range selector (inherited from layout)

### Section 1: Spend Treemap
- A Recharts Treemap showing spend distribution by task_type → model
- Each task type is a colored rectangle, sized by spend. Models within each task are sub-rectangles.
- Colors: Each task type gets a unique color from the palette
- Hover: Shows exact spend, % of total, request count
- Click: Drills down to that task type's detail view

### Section 2: Model Utilization Table
- A styled table (glassmorphic rows, no traditional borders) showing:
  | Model | Task Type | Requests (7d) | Avg Cost/Req | Total Spend (7d) | Avg Latency (p95) | Status |
- Status column: Green badge "Optimal", Yellow "Review", Red "Overspend Detected"
- "Overspend Detected" = when shadow evals suggest a cheaper model with high confidence
- Sortable columns with animated sort indicators
- Row click: Opens a side panel with detailed metrics

### Section 3: Cost Anomaly Timeline
- A Recharts Line chart showing daily spend with anomaly markers
- Normal days: Smooth gradient area fill
- Anomaly days: Red dots with tooltip explaining the spike
- Overlay: Dotted line showing "projected spend if swaps implemented"

### Section 4: Provider Breakdown
- Donut chart: Spend by provider (OpenAI, Anthropic, Google, Bedrock)
- Center text: Total spend amount
- Legend with provider logos/colors

### Data Fetching
- Fetch from: `GET /api/v1/costs/breakdown`, `GET /api/v1/costs/timeline`, `GET /api/v1/costs/top-spenders`
- Use mock data for development (provide realistic mock data in the component)
- Loading skeletons while fetching

### File Structure
```
src/pages/
└── CostTopology/
    ├── CostTopologyPage.jsx    # Main page layout
    ├── SpendTreemap.jsx         # Treemap component
    ├── ModelUtilizationTable.jsx # Sortable table
    ├── CostAnomalyTimeline.jsx  # Line chart with anomaly markers
    ├── ProviderBreakdown.jsx    # Donut chart
    └── mockData.js              # Realistic mock data
```

Generate the complete code for all files with realistic mock data showing a company spending across 4 providers and 6 task types.
```
### Finished until Here!!!
---

### Prompt 10: Dashboard UI — Shadow Eval Results & Swap Cards

```
You are an elite frontend engineer building the "Shadow Evaluations" and "Swap Recommendations" pages for the Staxx Intelligence dashboard.

## CONTEXT
This is the MONEY page. This is where customers see the concrete proof that they can save money by switching models. Every element must communicate statistical confidence and dollar savings.

## EXISTING DESIGN SYSTEM
(Copy the full design direction from Prompt 8 here)

## PAGE 1: Shadow Evaluations

### Hero: "Shadow Evaluation Lab"
- Subtitle: "Real production prompts. Cheaper models. Zero risk."
- Stats bar: "X evaluations completed", "Y task types analyzed", "Z models tested"

### Evaluation Progress Grid
- Grid of cards, one per (task_type, original_model) combination
- Each card shows:
  - Task type icon + name
  - Original model name + monthly cost
  - Progress bar: "47/50 evaluations complete" (with N≥20 threshold marked)
  - Candidate models being tested (small model badges)
  - Status: "Collecting Data" (< 20 runs), "Analysis Ready" (≥ 20 runs), "Swap Available" (high confidence swap found)

### Detailed Comparison View (click into a card)
- Side-by-side radar chart: Original vs best candidate across all metrics (cost, latency, quality, error rate, consistency)
- Metrics table with confidence intervals shown as ± ranges
- Sample outputs viewer: Toggle between original and candidate outputs for individual prompts
- Statistical details: Sample size, bootstrap CI visualization, TOPSIS score breakdown

## PAGE 2: Swap Recommendations

### Hero: "Recommended Swaps"
- Giant number: "Total Projected Savings: $X,XXX/mo" with counting animation
- Subtitle: "Based on X,XXX shadow evaluations across Y task types"

### Swap Cards (the star of the show)
Each swap recommendation is a premium card with:
- Left section: Current setup (model name, task type, monthly cost in RED)
- Center: Animated arrow with savings amount in GREEN
- Right section: Recommended model, projected cost, confidence badge
- Bottom: Key metrics comparison (latency, quality, error rate) as small bar charts
- Action buttons: "Approve Swap" (green), "Dismiss" (ghost), "View Details" (link)
- Confidence badge: Color-coded — Green "STRONG YES (94%)", Yellow "YES (78%)", Orange "MAYBE (62%)"

### Savings Waterfall Chart
- Waterfall chart showing: Current Total → (minus each approved swap) → Projected Total
- Each bar is a swap recommendation with its savings amount
- Animated on mount, bars slide in sequentially

### File Structure
```
src/pages/
├── ShadowEvals/
│   ├── ShadowEvalsPage.jsx
│   ├── EvalProgressGrid.jsx
│   ├── EvalDetailView.jsx
│   ├── RadarComparison.jsx
│   ├── OutputViewer.jsx
│   └── mockData.js
└── SwapRecommendations/
    ├── SwapRecommendationsPage.jsx
    ├── SwapCard.jsx
    ├── SavingsWaterfall.jsx
    ├── ConfidenceBadge.jsx
    └── mockData.js
```

Generate the complete code for all files. The Swap Cards must be visually stunning — they are the core UI element that sells the product.
```
###Finished Until HERE!!!
---

### Prompt 11: Dashboard UI — ROI Projections Page

```
You are an elite frontend engineer building the "ROI Projections" page for the Staxx Intelligence dashboard.

## CONTEXT
This page answers the customer's question: "Is Staxx worth it?" The answer must be an obvious YES, backed by clear numbers and beautiful visualizations.

## EXISTING DESIGN SYSTEM
(Copy the full design direction from Prompt 8 here)

## PAGE REQUIREMENTS

### Hero Section
- Title: "Return on Investment"
- Three giant metric cards:
  1. "Monthly Savings" — Green, large dollar amount
  2. "Annual Projection" — Monthly × 12 with confidence range
  3. "ROI Multiple" — "X.Xx" (savings / Staxx subscription cost)

### Section 1: 12-Month Savings Projection Chart
- Recharts Area chart showing projected cumulative savings over 12 months
- Shaded confidence band (light green fill between CI lower and upper bounds)
- Dotted line: Staxx subscription cost (cumulative)
- Intersection point highlighted: "Break-even: Month X" with a callout annotation
- Animated on mount — line draws from left to right

### Section 2: Savings Breakdown Table
- Table showing savings per task type:
  | Task Type | Current Model | Recommended | Monthly Savings | Confidence | Status |
- Status: "Approved" (green check), "Pending Review" (yellow), "Dismissed" (gray)
- Footer row: Total savings (bold)

### Section 3: What-If Simulator
- Interactive panel: "What if you approved all recommendations?"
- Slider: Adjust "implementation rate" from 0% to 100%
- As slider moves, the savings chart, ROI multiple, and totals update in real-time
- Shows: Conservative / Expected / Optimistic scenarios based on CI bounds

### Section 4: Executive Summary Card
- A single, beautifully designed "shareable" card (screenshot-worthy) containing:
  - Company name, date range
  - Current monthly LLM spend
  - Projected savings with Staxx
  - Top 3 swap recommendations
  - ROI multiple
  - "Powered by Staxx Intelligence" footer
- "Export as PDF" button

### File Structure
```
src/pages/
└── ROIProjections/
    ├── ROIProjectionsPage.jsx
    ├── SavingsProjectionChart.jsx
    ├── SavingsBreakdownTable.jsx
    ├── WhatIfSimulator.jsx
    ├── ExecutiveSummaryCard.jsx
    └── mockData.js
```

Generate the complete code for all files with realistic mock data for a company spending $25,000/month on LLM APIs.
```
###Finished Until Here
---

### Prompt 12: Self-Serve Onboarding Flow

```
You are an elite frontend + backend engineer building a self-serve onboarding flow for Staxx Intelligence.

## CONTEXT
The onboarding flow is the most critical conversion point. A new customer must go from "just signed up" to "seeing their data in the dashboard" in under 5 minutes. Every second of friction is lost revenue.

## REQUIREMENTS

### Onboarding Steps (Wizard UI)

**Step 1: Create Account**
- Email + password signup (or Google OAuth placeholder)
- Company name input
- Animated logo and tagline

**Step 2: Choose Integration Method**
- Three cards to choose from:
  1. "Proxy Gateway" (Recommended) — "Change one URL, see data instantly"
  2. "SDK Drop-in" — "Add 2 lines of Python/JS code"
  3. "Log Connector" — "Connect your CloudWatch, Datadog, or LangSmith"
- Each card has an icon, description, estimated setup time, and a "complexity" badge (Easy / Medium / Advanced)

**Step 3: Integration Setup (dynamic based on Step 2)**
- For Proxy: Show the proxy URL, code snippet to update env var, "Test Connection" button
- For SDK: Show pip install command, code snippet, "Send Test Event" button
- For Log Connector: AWS account ID input, IAM role setup instructions, "Verify Connection" button
- All paths end with a real-time connection health check with animated status indicator

**Step 4: First Data**
- "Waiting for your first event..." with a pulsing animation
- When first event arrives (polled via WebSocket or short-polling):
  - Celebration animation (confetti or subtle particle effect)
  - Show the first captured event details: model, tokens, cost, task type
  - "Your dashboard is ready" button → navigate to main dashboard

### Backend Endpoints
- `POST /api/v1/onboarding/signup` — Create org + user, return JWT + API key
- `POST /api/v1/onboarding/test-connection` — Verify proxy/SDK is sending data
- `GET /api/v1/onboarding/status` — Check if first event has arrived

### File Structure
```
src/pages/
└── Onboarding/
    ├── OnboardingWizard.jsx      # Main wizard with step management
    ├── steps/
    │   ├── CreateAccount.jsx
    │   ├── ChooseIntegration.jsx
    │   ├── IntegrationSetup.jsx  # Dynamic based on selection
    │   └── FirstData.jsx         # Waiting + celebration
    ├── components/
    │   ├── CodeSnippet.jsx       # Styled code block with copy button
    │   ├── ConnectionStatus.jsx  # Animated connection health indicator
    │   └── StepIndicator.jsx     # Progress dots/bar
    └── mockData.js

backend/
└── onboarding/
    ├── router.py
    ├── schemas.py
    └── service.py
```

Generate the complete code for all frontend AND backend files. The onboarding must feel magical — fast, clean, zero confusion.
```
##Finished Until HERE!!!
---

### Prompt 13: Docker Compose & Infrastructure

```
You are a senior DevOps / Platform engineer setting up the complete local development and MVP deployment infrastructure for Staxx Intelligence.

## REQUIREMENTS

### Docker Compose (Local Development)
A single `docker-compose.yml` that spins up the entire Staxx stack locally:

1. **postgres** — PostgreSQL 16 with TimescaleDB extension pre-installed
   - Init script: Create databases, enable TimescaleDB, create hypertables
   - Port: 5432
   - Health check

2. **redis** — Redis 7 with persistence (AOF)
   - Port: 6379
   - Used for: Celery broker, Redis Streams, caching

3. **minio** — MinIO S3-compatible storage
   - Port: 9000 (API), 9001 (Console)
   - Auto-create bucket: `staxx-outputs`

4. **backend** — FastAPI application
   - Port: 8000
   - Hot reload for development
   - Depends on: postgres, redis
   - Environment variables for all connections

5. **proxy** — The Proxy Gateway (separate FastAPI instance)
   - Port: 8080
   - Depends on: redis, backend

6. **celery-worker** — Celery worker for shadow evals + metrics
   - Concurrency: 4
   - Depends on: postgres, redis, minio

7. **celery-beat** — Celery beat scheduler
   - Depends on: redis

8. **frontend** — React app (Vite dev server)
   - Port: 3000
   - Proxies API calls to backend

### Environment Configuration
- `.env.example` with all required variables
- `docker-compose.override.yml` for development-specific settings

### Init Scripts
- `scripts/init-db.sql` — Database initialization with all tables, hypertables, indexes
- `scripts/seed-data.py` — Generate realistic seed data for development (mock orgs, users, cost events, eval runs)

### Makefile
- `make up` — Start everything
- `make down` — Stop everything
- `make logs` — Tail all logs
- `make seed` — Run seed data script
- `make test` — Run all tests
- `make migrate` — Run Alembic migrations

Generate the complete docker-compose.yml, .env.example, init-db.sql, seed-data.py, and Makefile.
```
###Finished until here!!!
---

### Prompt 14: Alert & Drift Monitoring System

```
You are a senior Python backend engineer building an alerting and drift monitoring system for Staxx Intelligence.

## CONTEXT
After customers implement model swaps based on Staxx recommendations, we need to continuously monitor that quality and cost remain within expected bounds. If something drifts, we alert immediately.

## REQUIREMENTS

### Drift Detection Types

1. **Quality Drift** — After a swap, monitor:
   - JSON schema validity rate dropping below threshold (e.g., < 95%)
   - Error rate increasing above threshold (e.g., > 2%)
   - Output consistency (CV) degrading significantly
   - Compare rolling 24h metrics against the baseline from shadow evals

2. **Cost Drift** — Monitor:
   - Provider price changes (poll pricing pages or APIs daily)
   - Unexpected cost spikes (> 2 standard deviations above daily average)
   - Volume spikes that change absolute savings

3. **Opportunity Detection** — Monitor:
   - New model releases from providers (poll provider status pages)
   - Price drops on existing models
   - New models that could be even cheaper than current recommendation

### Alert Schema
```python
class Alert(BaseModel):
    id: str
    org_id: str
    alert_type: str  # "quality_drift", "cost_spike", "price_change", "new_opportunity"
    severity: str    # "critical", "warning", "info"
    title: str
    description: str
    task_type: str | None
    model: str | None
    metric_name: str | None
    current_value: float | None
    threshold_value: float | None
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
```

### Celery Beat Schedule
- Every 1 hour: Quality drift check across all active swaps
- Every 6 hours: Cost anomaly detection
- Every 24 hours: Provider price catalog refresh + opportunity detection
- Every 5 minutes: Real-time cost spike detection (for critical alerts)

### Notification Channels
- In-app (dashboard alert bell with badge)
- Email (via SendGrid or AWS SES)
- Slack webhook (configurable per org)
- Webhook (generic, for custom integrations)

### API Endpoints
- `GET /api/v1/alerts?org_id=X&status=active` — List active alerts
- `POST /api/v1/alerts/{id}/acknowledge` — Acknowledge an alert
- `POST /api/v1/alerts/{id}/resolve` — Resolve an alert
- `GET /api/v1/alerts/settings?org_id=X` — Get alert thresholds and notification config
- `PUT /api/v1/alerts/settings?org_id=X` — Update alert settings

### File Structure
```
alerts/
├── __init__.py
├── detectors/
│   ├── quality_drift.py   # Quality metric monitoring
│   ├── cost_anomaly.py    # Cost spike and anomaly detection
│   └── opportunity.py     # New model / price drop detection
├── notifiers/
│   ├── base.py            # Abstract notifier
│   ├── email.py           # SendGrid/SES
│   ├── slack.py           # Slack webhook
│   └── webhook.py         # Generic webhook
├── scheduler.py           # Celery beat task definitions
├── api/
│   ├── router.py
│   └── schemas.py
├── db/
│   ├── models.py
│   └── queries.py
└── tests/
    └── test_detectors.py
```

Generate the complete, production-ready code for all files.
```

---

## Quick Reference: Build Order

For fastest MVP, build in this order:

1. **Docker Compose** (Prompt 13) — Get infra running locally
2. **Proxy Gateway** (Prompt 1) — Start capturing data immediately
3. **Cost Engine** (Prompt 3) — Show customers their spend
4. **Dashboard Layout + Cost Topology** (Prompts 8, 9) — Visualize the data
5. **Task Classifier** (Prompt 2) — Auto-label the traffic
6. **Shadow Evaluator** (Prompt 4) — Start proving savings
7. **Scoring Engine** (Prompt 5) — Statistical rigor
8. **Swap Recommendations + ROI** (Prompts 6, 10, 11) — The money pages
9. **Multi-Tenant + Onboarding** (Prompts 7, 12) — Scale to multiple customers
10. **Alert System** (Prompt 14) — Retain customers with ongoing value

---

*Generated for Staxx Intelligence — LLM Cost Efficiency Platform*
*Architecture V2 — Startup Edition*
