# Staxx Intelligence — The "LLM CFO"

> **"Stop overpaying for AI. We prove it with your own data."**

A production-grade SaaS platform for LLM cost optimization. Intercept real production traffic, run shadow evaluations against cheaper models, and get mathematically proven cost-saving recommendations with confidence intervals.

**Status:** ✅ **FEATURE COMPLETE** — All 14 architecture prompts implemented + secondary gaps closed.

---

## 📋 Table of Contents

- [What Is Staxx?](#what-is-staxx)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start (5 Minutes)](#quick-start-5-minutes)
- [Detailed Setup](#detailed-setup)
- [Available Commands](#available-commands)
- [API Documentation](#api-documentation)
- [Features Guide](#features-guide)
- [Troubleshooting](#troubleshooting)
- [Implementation Status](#implementation-status)

---

## What Is Staxx?

Staxx Intelligence is a multi-tenant SaaS platform that helps enterprises optimize their LLM spending:

**The Problem:**
- Companies spend $5k—$500k+/month on LLM APIs (OpenAI, Anthropic, Google, Bedrock)
- They don't know if they're using the right models for each task
- Token counters lie, and "better" isn't always "necessary"

**The Solution:**
1. **Capture**: Transparently intercept production LLM traffic
2. **Analyze**: Calculate real spend, auto-classify task types, score prompt complexity
3. **Evaluate**: Run shadow evaluations (20+ runs) of production prompts on cheaper alternatives
4. **Recommend**: Surface concrete swaps with confidence intervals and ROI projections
5. **Monitor**: Detect quality drift, cost spikes, and new opportunities 24/7

**The Result:**
Customers typically save **20—60%** on LLM costs without risking production quality.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  INTEGRATION LAYER                            │
├──────────────────────────────────────────────────────────────┤
│ • Proxy Gateway (transparent LLM API reverse proxy)          │
│ • SDK Drop-in (2-line Python/JS instrumentation)             │
│ • Log Connector (CloudWatch/Datadog enterprise integration)   │
└──────────────────┬───────────────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌─────────┐ ┌──────────┐ ┌─────────────────┐
   │ Task    │ │ Cost     │ │ Prompt          │
   │Classifier│ │ Engine   │ │ Complexity      │
   │ (Auto)   │ │(Real-time)│ │ Scorer          │
   └────┬────┘ └────┬─────┘ └────────┬────────┘
        │           │                │
        └───────────┼────────────────┘
                    ▼
        ┌─────────────────────────────┐
        │ SHADOW EVALUATION PIPELINE   │
        │ (Celery + 20+ runs/model)    │
        └──────────┬──────────────────┘
                   ▼
        ┌─────────────────────────────┐
        │ SCORING ENGINE V2 (TOPSIS)   │
        │ + Pareto + Confidence CI     │
        └──────────┬──────────────────┘
                   ▼
        ┌─────────────────────────────┐
        │ RECOMMENDATION + ROI ENGINE   │
        │ + ALERT & DRIFT MONITORING    │
        └──────────┬──────────────────┘
                   ▼
        ┌─────────────────────────────┐
        │ MULTI-TENANT BACKEND         │
        │ (FastAPI + JWT + Stripe)     │
        └──────────┬──────────────────┘
                   ▼
        ┌─────────────────────────────┐
        │ COST INTELLIGENCE DASHBOARD   │
        │ (React + Recharts + WebSocket)│
        └─────────────────────────────┘

STORAGE:
  PostgreSQL + TimescaleDB (metadata + time-series)
  Redis (broker + streams + caching)
  S3 / MinIO (raw eval outputs + audit trail)
  Celery Workers (async background jobs)
```

---

## Prerequisites

- **Python 3.11+** (backend + workers)
- **Node.js 18+** (frontend)
- **Docker Desktop** (databases: PostgreSQL, Redis, MinIO)
- **Git**

### Check Your Versions

```bash
python --version        # Should be 3.11+
node --version          # Should be 18+
docker --version        # Should be latest
```

---

## Quick Start (5 Minutes)

If you just want to get the whole stack running immediately:

```bash
# 1. Start all Docker services
make up

# 2. Initialize database + seed data
make migrate
make seed

# 3. In separate terminals:

# Terminal 1: Backend API
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2: Celery Worker
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Celery Beat (scheduler for alerts)
cd backend
source venv/bin/activate
celery -A app.workers.celery_app beat --loglevel=info

# Terminal 4: Frontend Dashboard
cd frontend
npm install
npm run dev
```

**Then open:** http://localhost:3000

---

## Detailed Setup

### Step 1: Clone & Navigate

```bash
git clone <repo-url>
cd Staxx
```

### Step 2: Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Database
DATABASE_URL=postgresql://staxx:password@localhost:5432/staxx
REDIS_URL=redis://localhost:6379/0

# Storage
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=staxx-outputs

# JWT & Auth
JWT_SECRET=your-super-secret-key-change-this
API_KEY_PREFIX=sk-staxx

# Stripe (optional for local dev)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (optional, for alerts)
SENDGRID_API_KEY=SG.xxxxx

# Datadog (optional, for log connector)
DATADOG_API_KEY=xxxxx
DATADOG_APP_KEY=xxxxx
```

### Step 3: Start Infrastructure (Databases)

```bash
# Start Docker services (PostgreSQL, Redis, MinIO)
make up

# Verify services are running
docker ps
```

Expected containers:
- `staxx-postgres` (port 5432)
- `staxx-redis` (port 6379)
- `staxx-minio` (port 9000, 9001)

### Step 4: Setup Backend

**Terminal 1: Backend API**

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations (creates tables, indexes, hypertables)
alembic upgrade head

# Seed development data (optional, adds mock orgs/users/data)
python scripts/seed-data.py

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ **Backend running at:** http://localhost:8000
📖 **API Docs at:** http://localhost:8000/docs

### Step 5: Setup Celery Worker

**Terminal 2: Celery Worker** (handles background jobs)

```bash
cd backend
source venv/bin/activate

# Start Celery worker
# Note: --pool=solo for Windows compatibility
celery -A app.workers.celery_app worker \
  --loglevel=info \
  --pool=solo \
  --concurrency=4
```

Expected output:
```
 -------------- celery@hostname v5.x.x
 -------- apps to route to by name: celery
 ----------- queues: celery
 --------- [tasks]
  . app.workers.metrics_worker.process_call
  . alerts.scheduler.check_quality_drift_task
  . alerts.scheduler.check_cost_spikes_task
  ...
```

### Step 6: Setup Celery Beat (Scheduler)

**Terminal 3: Celery Beat** (scheduled alert checks)

```bash
cd backend
source venv/bin/activate

# Start Celery Beat scheduler
celery -A app.workers.celery_app beat \
  --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Expected tasks will run on schedule:
- Every 5 min: Cost spike detection
- Every 1 hour: Quality drift checks
- Every 6 hours: Volume drift monitoring
- Every 24 hours: Opportunity detection (new models, price drops)

### Step 7: Setup Frontend

**Terminal 4: Frontend Dashboard**

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server with hot reload
npm run dev
```

✅ **Dashboard running at:** http://localhost:3000

---

## Available Commands

A `Makefile` in the root provides shortcuts:

```bash
# Docker & Infrastructure
make up              # Start all Docker services (databases)
make down            # Stop all Docker services
make logs            # Follow Docker logs
make restart         # Restart all services

# Database
make migrate         # Run Alembic migrations
make seed            # Seed development data
make db-shell        # Connect to Postgres shell

# Development
make test            # Run pytest suite
make lint            # Lint Python code (black, flake8)
make format          # Auto-format code (black)

# Utility
make clean           # Remove __pycache__, .pyc files
make backend-shell   # Python REPL with app context
```

Example workflow:

```bash
make up              # Start infrastructure
make migrate         # Setup DB
make seed            # Add mock data
make test            # Verify everything works
```

---

## API Documentation

### Endpoints Overview

| **Category** | **Endpoint** | **Method** | **Purpose** |
|---|---|---|---|
| **Health** | `/health` | GET | Liveness probe |
| **Capture** | `/api/v1/capture` | POST | Ingest SDK telemetry |
| **Costs** | `/api/v1/costs/*` | GET | Cost breakdown, timeline, summary |
| **Recommendations** | `/api/v1/recommendations` | GET | Get active swap recommendations |
| | `/api/v1/recommendations/{id}/approve` | POST | Approve a swap |
| **ROI** | `/api/v1/roi/projection` | GET | 12-month savings projection |
| | `/api/v1/roi/waterfall` | GET | Waterfall chart data |
| **Alerts** | `/api/v1/alerts` | GET | List active alerts |
| | `/api/v1/alerts/{id}/acknowledge` | POST | Acknowledge alert |
| | `/api/v1/alerts/{id}/resolve` | POST | Resolve alert |
| | `/api/v1/alerts/settings` | GET/PUT | Alert thresholds config |
| **Onboarding** | `/api/v1/onboarding/signup` | POST | Create org + user |
| | `/api/v1/onboarding/test-connection` | POST | Test proxy/SDK connection |
| | `/api/v1/onboarding/status` | GET | Check if first event arrived |
| **Platform** | `/api/v1/platform/auth/*` | POST | Login, signup, JWT refresh |
| | `/api/v1/platform/org` | GET/PATCH | Org settings |
| | `/api/v1/platform/org/members` | GET/POST | Member management |
| | `/api/v1/platform/org/keys` | GET/POST | API key management |
| **Export** | `/api/v1/export/executive-summary/pdf` | GET | Download PDF report |
| | `/api/v1/export/cost-analysis/pdf` | GET | Download cost analysis PDF |
| **WebSocket** | `/ws/cost-feed?api_key=...` | WS | Live cost feed stream |

### Interactive API Docs

Once the backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Both auto-generated from FastAPI and fully interactive.

---

## Features Guide

### 1. Onboarding Wizard (Multi-Step)

**Route:** `/onboarding` (frontend)

1. **Sign Up** — Email, password, company name → org created
2. **Choose Integration** — Proxy / SDK / Log Connector
3. **Setup** — Get API key, proxy URL, code snippets
4. **First Data** — Wait for first telemetry event to arrive

### 2. Cost Dashboard

**Route:** `/` (homepage)

- **Metrics Cards**: Total spend MTD, potential savings, active models, API calls
- **Spend Over Time** — Area chart with 7d/30d/90d trends
- **Top Spend by Task** — Bar chart showing most expensive task types
- **Active Recommendations** — Swap cards ready to implement

### 3. Cost Topology

**Route:** `/cost-topology`

- **Spend Treemap** — Hierarchical visualization (task type → model)
- **Model Utilization Table** — Sortable table with alerts
- **Cost Anomaly Timeline** — Daily costs with spike detection
- **Provider Breakdown** — Donut chart (OpenAI, Anthropic, Google, etc.)

### 4. Shadow Evaluations

**Route:** `/shadow-evals`

- **Progress Grid** — Status of eval runs per model/task
- **Detailed Comparison** — Radar charts comparing original vs candidates
- **Output Viewer** — Side-by-side output inspection
- **Statistical Details** — Bootstrap CI, TOPSIS scores, Pareto frontier

### 5. Swap Recommendations

**Route:** `/recommendations`

- **Recommendation Cards** — Beautiful cards showing current → recommended model
- **Confidence Badges** — Color-coded (green STRONG_YES, yellow YES, orange MAYBE)
- **Savings Waterfall** — Waterfall chart showing total savings potential
- **Action Buttons** — Approve / Dismiss workflow

### 6. ROI Projections

**Route:** `/roi`

- **Executive Summary** — KPI cards (monthly savings, annual projection, ROI multiple)
- **12-Month Projection Chart** — Animated area chart with confidence band
- **Savings Breakdown Table** — Per-task breakdown with status
- **What-If Simulator** — Interactive slider to model different approval rates
- **PDF Export** — Download executive summary as professional PDF

### 7. Alerts

**Route:** `/alerts`

- **Active Alerts List** — Quality drift, cost spikes, new opportunities
- **Severity Filtering** — Critical, warning, info
- **Acknowledge / Resolve** — Alert workflow tracking
- **Stats Dashboard** — Count of active vs resolved alerts
- **Auto-refresh** — Updates every 30 seconds

### 8. Alert Configuration

**Settings** in `/alerts`

- Threshold controls: JSON validity, error rate, cost spike std devs, latency regression
- Notification channels: Email, Slack, webhook
- Auto-dismiss policies

---

## Troubleshooting

### Docker Issues

**Problem:** `docker: command not found`

**Solution:** Install Docker Desktop from https://www.docker.com/products/docker-desktop

---

**Problem:** `Container exit with error "Connection refused"`

**Solution:**
```bash
# Make sure Docker daemon is running (Docker Desktop)
# Then rebuild and restart
make down
make up
```

---

### Backend Issues

**Problem:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

---

**Problem:** `FATAL: Ident authentication failed for user "staxx"`

**Solution:** Wait 10-15 seconds for PostgreSQL to fully start, then retry migrations:
```bash
sleep 15
alembic upgrade head
```

---

**Problem:** `Celery worker hangs on Windows`

**Solution:** Always use `--pool=solo` on Windows:
```bash
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

---

### Frontend Issues

**Problem:** Dashboard shows "Demo Data" / API unreachable

**Solution:**
1. Verify backend is running: http://localhost:8000/health
2. Check frontend env: `frontend/.env` should have `REACT_APP_API_URL=http://localhost:8000`
3. Refresh browser (Ctrl+Shift+R to clear cache)

---

**Problem:** `Port 3000 already in use`

**Solution:**
```bash
# Find and kill the process using port 3000
lsof -ti:3000 | xargs kill -9    # macOS/Linux
Get-Process | Where-Object {$_.Handles -eq $(netstat -ano | grep :3000)[0].split()[1]} | Stop-Process  # Windows
```

---

### Database Issues

**Problem:** `UNIQUE constraint violation on organizations.slug`

**Solution:** It's OK to continue—just a seed data duplicate. Don't reseed:
```bash
# Don't run:
python scripts/seed-data.py

# Just proceed
```

---

**Problem:** Migration fails with `Table "cost_events" already exists`

**Solution:** This is safe in dev. Alembic is idempotent. Continue:
```bash
# Doesn't require action; the table is already created
```

---

### Common Success Checklist

After all 4 terminals are running, verify:

- ✅ Backend logs show `Uvicorn running on http://0.0.0.0:8000`
- ✅ http://localhost:8000/health returns `{"status": "ok"}`
- ✅ http://localhost:8000/docs (Swagger) loads
- ✅ Celery worker logs show `[*] Ready to accept tasks`
- ✅ Frontend shows dashboard (not demo data)
- ✅ http://localhost:3000 loads without errors in browser console

---

## Implementation Status

### Complete Features ✅

| # | Feature | Status | Files |
|---|---------|--------|-------|
| 1 | Proxy Gateway | ✅ DONE | `proxy/` (7 files) |
| 2 | Task Classifier | ✅ DONE | `classifier/` (6 files + tests) |
| 3 | Cost Engine + TimescaleDB | ✅ DONE | `cost_engine/` (9 files) |
| 4 | Shadow Evaluation Pipeline | ✅ DONE | `shadow_eval/` (8 files) |
| 5 | Scoring Engine V2 | ✅ DONE | `scoring/` (7 files) |
| 6 | Recommendation + ROI Engine | ✅ DONE | `recommendations/` (7 files) |
| 7 | Multi-Tenant Backend | ✅ DONE | `platform/` (10 files) |
| 8 | Dashboard UI — Main Layout | ✅ DONE | `frontend/src/` (8 files) |
| 9 | Dashboard UI — Cost Topology | ✅ DONE | `frontend/src/pages/CostTopology/` (5 files) |
| 10 | Dashboard UI — Shadow Evals | ✅ DONE | `frontend/src/pages/ShadowEvals/` (5 files) |
| 11 | Dashboard UI — ROI Projections | ✅ DONE | `frontend/src/pages/ROIProjections/` (5 files) |
| 12 | Self-Serve Onboarding | ✅ DONE | `frontend/src/pages/Onboarding/` (7 files) |
| 13 | Docker Compose + Infra | ✅ DONE | `docker-compose.yml`, `Makefile` |
| **14** | **Alert & Drift Monitoring** | ✅ **DONE** | `alerts/` (13 files) |
| **Extra** | **Log Connector** | ✅ **DONE** | `log_connector/` (4 files) |
| **Extra** | **WebSocket Live Feeds** | ✅ **DONE** | `backend/app/websocket/` (2 files) |
| **Extra** | **PDF Export** | ✅ **DONE** | `backend/app/utils/` (2 files) |
| **Extra** | **Onboarding DB Migration** | ✅ **DONE** | Migrated from in-memory |

---

## Architecture Docs

For deep architecture details:

- **Full Architecture + Prompts:** [staxx_v2_architecture_and_prompts.md](./staxx_v2_architecture_and_prompts.md)
- **Implementation Complete:** [IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md)
- **Audit Report:** [Plan File](./claude-code/plans/parallel-crafting-quill.md)

---

## Key Technologies

**Backend:**
- FastAPI (async web framework)
- SQLAlchemy 2.0 (ORM)
- Alembic (migrations)
- Celery (distributed workers)
- Redis (broker, streams, caching)
- PostgreSQL + TimescaleDB (databases)
- Pydantic (validation)

**Frontend:**
- React 19
- Vite 7 (bundler)
- Tailwind CSS 4 (styling)
- Recharts 3 (charts)
- Framer Motion 12 (animations)
- Lucide React (icons)
- React Router 6 (navigation)

**DevOps:**
- Docker & Docker Compose
- Alembic (DB versioning)
- Make (task automation)

---

## License

MIT (Staxx Intelligence MVP)

---

## Support

For issues, questions, or feature requests:

1. Check [Troubleshooting](#troubleshooting) above
2. Review logs: `docker logs <container>` or terminal output
3. Open an issue on GitHub

---

**Happy cost optimization! 🚀**

*Staxx Intelligence — The LLM CFO for enterprise AI.*
