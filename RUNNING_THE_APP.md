# How to Run Staxx Intelligence — Simple Guide

## TL;DR (Copy & Paste)

```bash
# Terminal 1: Start databases
make up
make migrate

# Terminal 2: Backend API
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 3: Celery Worker
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --pool=solo

# Terminal 4: Celery Beat (optional, for scheduled alerts)
cd backend
source venv/bin/activate
celery -A app.workers.celery_app beat --loglevel=info

# Terminal 5: Frontend
cd frontend
npm install
npm run dev
```

Then open: http://localhost:3000

---

## Prerequisites

```bash
# Check these are installed
python --version      # Should be 3.11+
node --version        # Should be 18+
docker --version      # Should be latest (Desktop required)
git --version
```

If any are missing, install them:
- **Python**: https://www.python.org/downloads/
- **Node.js**: https://nodejs.org/
- **Docker Desktop**: https://www.docker.com/products/docker-desktop

---

## Step-by-Step Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Staxx
```

### Step 2: Create Environment File

Copy the template:

```bash
cp .env.example .env
```

Edit `.env` if needed (default values work for local dev).

### Step 3: Start Infrastructure (Databases)

**Terminal 1:**

```bash
# Start PostgreSQL, Redis, MinIO
make up

# Verify containers are running
docker ps

# Run database migrations
make migrate

# (Optional) Seed demo data
make seed
```

Wait for all containers to be ready (usually 10-15 seconds).

### Step 4: Start Backend API

**Terminal 2:**

```bash
cd backend

# Create Python virtual environment
python -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate
# Windows (Git Bash):
source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ **Backend running at:** http://localhost:8000
📖 **API Docs at:** http://localhost:8000/docs

### Step 5: Start Celery Worker (Background Jobs)

**Terminal 3:**

```bash
cd backend
source venv/bin/activate

# Start Celery worker
# Note: --pool=solo is required on Windows
celery -A app.workers.celery_app worker \
  --loglevel=info \
  --pool=solo \
  --concurrency=4
```

You should see:
```
[*] Ready to accept tasks
```

### Step 6: Start Celery Beat (Scheduled Tasks - Optional)

**Terminal 4:**

For automatic alert checks (quality drift, cost spikes every 5 minutes):

```bash
cd backend
source venv/bin/activate

celery -A app.workers.celery_app beat --loglevel=info
```

This enables:
- ✅ Cost spike detection (every 5 min)
- ✅ Quality drift monitoring (every 1 hour)
- ✅ New opportunity detection (every 24 hours)

### Step 7: Start Frontend Dashboard

**Terminal 5:**

```bash
cd frontend

# Install npm dependencies
npm install

# Start dev server with hot reload
npm run dev
```

✅ **Dashboard running at:** http://localhost:3000

---

## Verify Everything is Working

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### 2. Check API Docs

Open in browser:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

### 3. Check Frontend

Open in browser:
- http://localhost:3000

Should see the glassmorphic dashboard (not error messages).

### 4. Check Docker Containers

```bash
docker ps

# Should see:
# staxx-postgres   (5432)
# staxx-redis      (6379)
# staxx-minio      (9000)
```

---

## Common Tasks

### Send Test Data to Backend

```bash
curl -X POST http://localhost:8000/api/v1/capture \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "task_type": "summarization",
    "input_tokens": 1000,
    "output_tokens": 200,
    "latency_ms": 1500
  }'
```

Watch it flow through:
1. Backend receives → logs in terminal
2. Celery worker processes → logs "processing..."
3. Frontend updates → refresh http://localhost:3000

### View Database

```bash
docker exec -it staxx-postgres psql -U staxx -d staxx

# Inside psql:
\dt                # List all tables
SELECT * FROM organizations;  # View orgs
SELECT * FROM cost_events LIMIT 5;  # View cost data
\q                 # Exit
```

### View Redis Cache

```bash
docker exec -it staxx-redis redis-cli

# Inside redis:
KEYS *             # List all keys
GET your_key       # Get a value
FLUSHDB            # Clear all data
EXIT
```

### View MinIO (S3 Bucket)

Open in browser: http://localhost:9001
- Default: minioadmin / minioadmin
- Browse `staxx-outputs` bucket

---

## Troubleshooting

### Port Already in Use

```bash
# macOS/Linux - Kill process on port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process

# Or just use a different port:
uvicorn app.main:app --port 8001 --reload
```

### Docker Containers Won't Start

```bash
# Stop and remove old containers
docker-compose down --volumes

# Start fresh
make up
sleep 15  # Wait for databases to initialize
make migrate
```

### Celery Worker Hangs

Make sure you're using `--pool=solo` on Windows:

```bash
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

### Backend Can't Connect to Database

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check logs
docker logs staxx-postgres

# If it crashed, restart
docker-compose restart postgres
sleep 10
make migrate
```

### Frontend Shows "Demo Data" / API Unreachable

1. Check backend is running: http://localhost:8000/health
2. Check browser console for errors (F12)
3. Refresh page (Ctrl+Shift+R to clear cache)
4. Make sure you didn't skip Terminal 2 (backend API)

### "Permission denied" on `venv/bin/activate`

```bash
# macOS/Linux: Make script executable
chmod +x venv/bin/activate

# Then try again
source venv/bin/activate
```

---

## The Full Terminal Layout (Optimal Setup)

You should have **5 terminal windows** open:

```
┌─────────────────────────────────────────────────────┐
│ Terminal 1: Docker & Databases                      │
│ $ make up                                            │
│ $ make migrate                                       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Terminal 2: Backend API                             │
│ $ cd backend && python -m venv venv                 │
│ $ source venv/bin/activate                          │
│ $ pip install -r requirements.txt                   │
│ $ uvicorn app.main:app --reload                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Terminal 3: Celery Worker                           │
│ $ cd backend && source venv/bin/activate            │
│ $ celery -A app.workers.celery_app worker ...       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Terminal 4: Celery Beat (optional, for alerts)      │
│ $ cd backend && source venv/bin/activate            │
│ $ celery -A app.workers.celery_app beat --loglevel  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Terminal 5: Frontend                                │
│ $ cd frontend && npm install && npm run dev         │
└─────────────────────────────────────────────────────┘

Browser Tabs:
- http://localhost:3000       (Dashboard)
- http://localhost:8000/docs  (API Documentation)
```

---

## What You Can Do Now

Once everything is running:

1. **Visit Dashboard**: http://localhost:3000
2. **Sign up** with any email/password
3. **View mock data** on the dashboard
4. **Explore pages**:
   - `/` — Dashboard home (metrics, charts)
   - `/cost-topology` — Where your money goes
   - `/shadow-evals` — Shadow evaluation progress
   - `/recommendations` — Model swap suggestions
   - `/roi` — ROI projections & PDF export
   - `/alerts` — Quality drift & cost spike alerts
5. **API Testing**: http://localhost:8000/docs (try endpoints interactively)

---

## Stopping Everything

When you're done:

```bash
# In Terminal 1: Stop Docker
make down

# In Terminals 2-5: Press Ctrl+C
```

All data persists in Docker volumes, so next time you just:

```bash
make up
# (skip migrations - tables already exist)
```

---

## Next Steps

- **Read full README**: [README.md](./README.md)
- **Explore API**: http://localhost:8000/docs
- **Check status**: [IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md)
- **Learn architecture**: [staxx_v2_architecture_and_prompts.md](./staxx_v2_architecture_and_prompts.md)

---

## Help

If you get stuck:

1. **Check logs** in the terminal where the error happened
2. **Try the troubleshooting section** above
3. **Read the full README**: [README.md](./README.md)
4. **Check docker logs**: `docker logs staxx-postgres` (or other service)

---

## Quick Reference

| What | Where | How |
|------|-------|-----|
| **Dashboard** | Browser | http://localhost:3000 |
| **API Docs** | Browser | http://localhost:8000/docs |
| **Postgres** | Docker | `docker exec -it staxx-postgres psql -U staxx -d staxx` |
| **Redis** | Docker | `docker exec -it staxx-redis redis-cli` |
| **MinIO** | Browser | http://localhost:9001 |
| **Backend Status** | Curl | `curl http://localhost:8000/health` |
| **Stop Docker** | Terminal 1 | `make down` |
| **View Logs** | Docker | `docker logs staxx-<service>` |

---

**You're all set! Happy cost optimization! 🚀**
