# Staxx Intelligence — Complete Quick Start Guide

**Get the full Staxx system running in minutes.**

---

## 🎯 Overview

The Staxx project consists of:

1. **Backend** (`/backend`) — FastAPI server with multi-tenant platform layer
2. **Frontend** (`/frontend`) — React dashboard with glassmorphic UI
3. **Platform** (`/platform`) — Auth, billing, API key management (integrated into backend)

---

## ⚡ Option 1: Docker Compose (Recommended — 30 seconds)

**Fastest way to get everything running.**

### Prerequisites
- Docker & Docker Compose installed
- 5+ GB disk space for containers

### Step 1: Create `.env` in project root

```bash
cat > .env << 'EOF'
JWT_SECRET=your-super-secret-jwt-key-1234567890abcdef
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
APP_BASE_URL=http://localhost:3000
EOF
```

### Step 2: Start All Services

```bash
docker-compose up -d
```

### Step 3: Verify Everything

```bash
# Check logs
docker-compose logs -f backend

# Test backend
curl http://localhost:8000/health

# Open in browser
# Backend API: http://localhost:8000/api/v1/docs
# Frontend: http://localhost:3000 (after starting)
```

**That's it!** The backend is running. Now start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

---

## 🛠️ Option 2: Manual Local Setup

**For development without Docker.**

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+

### Step 1A: Start PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql
brew services start postgresql
psql -U postgres -c "CREATE USER staxx WITH PASSWORD 'staxx_dev_password';"
psql -U postgres -c "CREATE DATABASE staxx OWNER staxx;"
```

**Windows (WSL/Git Bash):**
```bash
# Assume PostgreSQL is already installed. Then:
psql -U postgres
# In psql:
CREATE USER staxx WITH PASSWORD 'staxx_dev_password';
CREATE DATABASE staxx OWNER staxx;
\q
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE USER staxx WITH PASSWORD 'staxx_dev_password';"
sudo -u postgres psql -c "CREATE DATABASE staxx OWNER staxx;"
sudo systemctl start postgresql
```

### Step 1B: Start Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows (using WSL):**
```bash
wsl
sudo apt-get install redis-server
redis-server
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# OR
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
POSTGRES_SERVER=localhost
POSTGRES_USER=staxx
POSTGRES_PASSWORD=staxx_dev_password
POSTGRES_DB=staxx
POSTGRES_PORT=5432

REDIS_HOST=localhost
REDIS_PORT=6379

JWT_SECRET=your-super-secret-jwt-key-1234567890abcdef
STRIPE_SECRET_KEY=sk_test_
STRIPE_WEBHOOK_SECRET=whsec_
APP_BASE_URL=http://localhost:3000
EOF

# Run database migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Backend is now running at:** http://localhost:8000

### Step 3: Frontend Setup

In a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

**Frontend is now running at:** http://localhost:3000

---

## 🔍 Verify Everything Works

### Backend Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### API Documentation

- Interactive Docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Test Sign Up (via curl)

```bash
curl -X POST http://localhost:8000/api/v1/platform/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "org_name": "Test Company",
    "org_slug": "test-company"
  }'
```

Expected response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Test Frontend

1. Open http://localhost:3000
2. You should see the premium glassmorphic dashboard
3. Charts and animations should be smooth

---

## 🗂️ Project Structure

```
Staxx/
├── backend/                         # FastAPI backend
│   ├── app/
│   │   ├── main.py                  # Entry point
│   │   ├── config.py                # Environment config
│   │   ├── api/                     # API routes
│   │   └── core/                    # DB, storage, etc.
│   ├── platform/                    # Multi-tenant layer
│   │   ├── auth/                    # JWT, API keys, password
│   │   ├── billing/                 # Stripe integration
│   │   ├── api/                     # Platform endpoints
│   │   ├── db/                      # Models, queries
│   │   └── middleware/              # Tenant isolation
│   ├── alembic/                     # Database migrations
│   ├── requirements.txt             # Python dependencies
│   └── Dockerfile                   # Docker image definition
│
├── frontend/                        # React dashboard
│   ├── src/
│   │   ├── components/              # Reusable UI components
│   │   ├── pages/                   # Page components
│   │   ├── layouts/                 # Layout wrappers
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── theme/                   # Chart theming
│   │   └── utils/                   # Mock data, helpers
│   ├── index.html                   # HTML entry point
│   ├── package.json                 # Node dependencies
│   └── vite.config.js               # Vite config
│
├── platform/                        # Shared multi-tenant logic
│   ├── auth/                        # Auth dependencies
│   ├── billing/                     # Billing logic
│   ├── api/                         # API schemas
│   ├── db/                          # Database models
│   └── middleware/                  # Middleware
│
├── docker-compose.yml               # All services definition
├── BACKEND_SETUP.md                 # Detailed backend guide
├── FRONTEND_SETUP.md                # Detailed frontend guide
└── QUICKSTART.md                    # This file
```

---

## 📝 Key Environment Variables

### Backend (Required)

| Variable | Example | Purpose |
|----------|---------|---------|
| `POSTGRES_SERVER` | `localhost` | PostgreSQL host |
| `POSTGRES_USER` | `staxx` | DB user |
| `POSTGRES_PASSWORD` | `staxx_dev_password` | DB password |
| `POSTGRES_DB` | `staxx` | Database name |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `JWT_SECRET` | `your-secret-key` | JWT signing secret |
| `APP_BASE_URL` | `http://localhost:3000` | Frontend URL for invites |

### Optional (Billing)

| Variable | Purpose |
|----------|---------|
| `STRIPE_SECRET_KEY` | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing |
| `STRIPE_PRICE_STARTER` | Stripe price ID for $99/mo plan |
| `STRIPE_PRICE_GROWTH` | Stripe price ID for $499/mo plan |

---

## 🚀 Common Commands

### Backend

```bash
# Start backend
cd backend && uvicorn app.main:app --port 8000 --reload

# Run migrations
cd backend && alembic upgrade head

# Create migration
cd backend && alembic revision --autogenerate -m "description"

# Run tests
cd backend && pytest

# Start Celery worker (for async tasks)
cd backend && celery -A app.workers worker --loglevel=info
```

### Frontend

```bash
# Start dev server
cd frontend && npm run dev

# Build for production
cd frontend && npm run build

# Preview production build
cd frontend && npm run preview
```

### Docker

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend

# Rebuild images
docker-compose build --no-cache

# Restart a service
docker-compose restart backend
```

### Database

```bash
# Connect to PostgreSQL
psql -h localhost -U staxx -d staxx

# View tables
\dt

# View users
SELECT * FROM users;

# View organizations
SELECT * FROM organizations;

# Exit
\q
```

---

## 🐛 Troubleshooting

### "Address already in use"

```bash
# Kill process on port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or use different port
uvicorn app.main:app --port 8001
```

### "PostgreSQL connection refused"

```bash
# Check if PostgreSQL is running
pg_isready

# Verify credentials
psql -h localhost -U staxx -d staxx -c "SELECT 1;"

# Check .env file has correct credentials
```

### "Redis connection failed"

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Start Redis
redis-server  # or brew services start redis
```

### "ModuleNotFoundError: No module named 'platform'"

This means you're importing the `platform` package from the wrong location. Ensure:

```bash
cd backend
# NOT cd /backend/platform
```

The `platform/` directory should be at the **project root**, not inside `backend/`.

### Frontend can't reach API

- Ensure backend is running on port 8000
- Check `vite.config.js` proxy config
- Try: `curl http://localhost:8000/health`

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         React Dashboard (localhost:3000)         │
│      Glassmorphic UI + Framer Motion            │
└──────────────────┬──────────────────────────────┘
                   │ HTTP/REST
                   ▼
┌─────────────────────────────────────────────────┐
│    FastAPI Backend (localhost:8000)             │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ Platform Layer (Multi-Tenant)             │  │
│  │ ├─ Auth (JWT + API Keys)                  │  │
│  │ ├─ Billing (Stripe integration)           │  │
│  │ ├─ Organizations & Users                  │  │
│  │ └─ Usage Tracking                         │  │
│  └───────────────────────────────────────────┘  │
│                   │                              │
├───┬──────────────┼──────────────┬────────────┤
│   │              │              │            │
▼   ▼              ▼              ▼            ▼
DB  Cache         Async          S3/MinIO    APIs
PG  Redis         Tasks          Storage     (Claude,
    (Celery)      (Queues)                   OpenAI,
                                             etc.)
```

---

## ✅ Checklist: Everything Working?

- [ ] Docker Compose started: `docker-compose up -d`
- [ ] Backend running: `curl http://localhost:8000/health` ✓
- [ ] API docs: http://localhost:8000/api/v1/docs ✓
- [ ] PostgreSQL accessible with correct credentials
- [ ] Redis accessible
- [ ] Frontend npm dependencies installed: `npm install` ✓
- [ ] Frontend running: `npm run dev` ✓
- [ ] Dashboard visible at http://localhost:3000 ✓
- [ ] Can sign up via signup endpoint
- [ ] Dashboard shows mock data (metrics, charts)

---

## 🎯 Next Steps

1. **Explore the API**: Visit http://localhost:8000/api/v1/docs
2. **Sign up via UI**: Open http://localhost:3000 and sign up
3. **Create an API key**: Use the dashboard to generate a key
4. **Connect the proxy**: Point your LLM calls to the proxy gateway
5. **Run shadow evaluations**: Start capturing real production traffic
6. **View recommendations**: See cost-saving swap opportunities
7. **Monitor alerts**: Check `/alerts` page for quality drift and cost spikes (automatic detection)
8. **Export reports**: Download PDF executive summaries from `/roi` page
9. **Set up Log Connector**: Integrate CloudWatch or Datadog logs (optional, enterprise)

---

## 🆕 New Features (Recently Added)

| Feature | Route | Purpose |
|---------|-------|---------|
| **Alerts** | `/alerts` | Real-time monitoring for quality drift, cost spikes, new opportunities |
| **WebSocket Feed** | `WS /ws/cost-feed` | Live cost updates pushed to dashboard (no polling) |
| **PDF Export** | `/api/v1/export/*` | Download executive summary or cost analysis as PDF |
| **Log Connector** | N/A (backend) | CloudWatch/Datadog integration for enterprise log ingestion |
| **Onboarding DB** | `/onboarding` | Database-backed signup (production-ready, no in-memory state) |

---

## 📚 Full Documentation

- **Main README**: [README.md](./README.md) — **START HERE** for complete setup
- **Backend Setup**: [BACKEND_SETUP.md](./BACKEND_SETUP.md)
- **Frontend Setup**: [frontend/FRONTEND_SETUP.md](./frontend/FRONTEND_SETUP.md)
- **Architecture**: [staxx_v2_architecture_and_prompts.md](./staxx_v2_architecture_and_prompts.md)
- **Implementation Status**: [IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md)

---

**You're all set! 🚀**

If you hit any issues, check the troubleshooting section or refer to the detailed guides.
