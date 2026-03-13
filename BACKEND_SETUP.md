# Staxx Intelligence — Backend Setup & Running Guide

**Complete instructions to run the FastAPI backend with all services.**

---

## 📋 Prerequisites

Before running the backend, ensure you have:

- **Python 3.10+** (check: `python --version`)
- **PostgreSQL 14+** (running locally or via Docker)
- **Redis 7+** (running locally or via Docker)
- **Docker & Docker Compose** (optional, recommended for local dev)

---

## 🚀 Quick Start (Recommended: Docker Compose)

The easiest way to get everything running is with Docker Compose, which spins up PostgreSQL, Redis, and the backend together.

### Step 1: Create `.env` file

In the root of the project, create `.env`:

```bash
# backend/app/config.py
POSTGRES_SERVER=postgres
POSTGRES_USER=staxx
POSTGRES_PASSWORD=staxx_dev_password
POSTGRES_DB=staxx
POSTGRES_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379

# platform/config.py
JWT_SECRET=your-super-secret-jwt-key-change-in-production
STRIPE_SECRET_KEY=sk_test_your_stripe_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_PRICE_STARTER=price_1234567890
STRIPE_PRICE_GROWTH=price_0987654321
STRIPE_PRICE_ENTERPRISE=price_custom_enterprise
APP_BASE_URL=http://localhost:3000
```

### Step 2: Create `docker-compose.yml` (if not exists)

Create this file in the **root of Staxx project**:

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    container_name: staxx-postgres
    environment:
      POSTGRES_USER: staxx
      POSTGRES_PASSWORD: staxx_dev_password
      POSTGRES_DB: staxx
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U staxx" ]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: staxx-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: [ "CMD", "redis-cli", "ping" ]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: staxx-backend
    ports:
      - "8000:8000"
    environment:
      POSTGRES_SERVER: postgres
      POSTGRES_USER: staxx
      POSTGRES_PASSWORD: staxx_dev_password
      POSTGRES_DB: staxx
      POSTGRES_PORT: 5432
      REDIS_HOST: redis
      REDIS_PORT: 6379
      JWT_SECRET: ${JWT_SECRET}
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

### Step 3: Start Everything

```bash
docker-compose up -d
```

Check logs:
```bash
docker-compose logs -f backend
```

The backend will be available at: **http://localhost:8000**

---

## 🛠️ Manual Setup (Without Docker)

If you prefer running services locally without Docker:

### Step 1: Install PostgreSQL & Redis

**On Windows (using Chocolatey):**
```bash
choco install postgresql redis
```

**On macOS (using Homebrew):**
```bash
brew install postgresql redis
```

**On Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql postgresql-contrib redis-server
```

### Step 2: Start Services

**PostgreSQL:**
```bash
# macOS / Linux
brew services start postgresql  # or sudo systemctl start postgresql

# Windows (via psql prompt)
psql -U postgres
```

**Redis:**
```bash
# macOS / Linux
brew services start redis  # or redis-server

# Windows (via WSL or Redis installer)
redis-server
```

### Step 3: Create Database & User

```bash
# Connect to PostgreSQL
psql -U postgres

# In psql shell:
CREATE USER staxx WITH PASSWORD 'staxx_dev_password';
CREATE DATABASE staxx OWNER staxx;
ALTER ROLE staxx WITH CREATEDB;
\q
```

### Step 4: Install Python Dependencies

```bash
cd backend
python -m venv venv

# Activate venv
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Set Up Environment Variables

Create `backend/.env`:

```
POSTGRES_SERVER=localhost
POSTGRES_USER=staxx
POSTGRES_PASSWORD=staxx_dev_password
POSTGRES_DB=staxx
POSTGRES_PORT=5432

REDIS_HOST=localhost
REDIS_PORT=6379

JWT_SECRET=your-super-secret-jwt-key-change-in-production
STRIPE_SECRET_KEY=sk_test_your_stripe_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_PRICE_STARTER=price_1234567890
STRIPE_PRICE_GROWTH=price_0987654321
STRIPE_PRICE_ENTERPRISE=price_custom_enterprise
APP_BASE_URL=http://localhost:3000
```

### Step 6: Run Database Migrations

```bash
cd backend
alembic upgrade head
```

### Step 7: Start Backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You'll see:
```
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## 📚 API Documentation

Once the backend is running, visit:

- **Interactive API Docs**: http://localhost:8000/api/v1/docs
- **Alternative Docs**: http://localhost:8000/api/v1/redoc
- **Health Check**: http://localhost:8000/health

---

## 🔑 Platform Layer Endpoints

The backend now includes the **platform layer** with multi-tenant auth, billing, and API key management.

### Auth Endpoints

```http
POST /api/v1/platform/auth/signup
POST /api/v1/platform/auth/login
POST /api/v1/platform/auth/refresh
GET  /api/v1/platform/auth/me
```

**Example: Sign Up**
```bash
curl -X POST http://localhost:8000/api/v1/platform/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "org_name": "Test Corp",
    "org_slug": "test-corp"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Organization Endpoints

```http
GET  /api/v1/platform/org
PATCH /api/v1/platform/org
GET  /api/v1/platform/org/members
POST /api/v1/platform/org/invite
POST /api/v1/platform/org/invite/accept
```

### API Keys

```http
GET    /api/v1/platform/org/keys
POST   /api/v1/platform/org/keys
DELETE /api/v1/platform/org/keys/{key_id}
```

**Example: Create API Key**
```bash
curl -X POST http://localhost:8000/api/v1/platform/org/keys \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Proxy Integration"
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "key": "stx_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "key_prefix": "a1b2c3d4",
  "label": "Proxy Integration",
  "created_at": "2025-03-05T10:30:00Z"
}
```

### Billing Endpoints

```http
GET  /api/v1/platform/billing/usage
POST /api/v1/platform/billing/upgrade
GET  /api/v1/platform/billing/portal
POST /api/v1/platform/webhooks/stripe
```

---

## 🗄️ Database Migrations

### Create New Migration

```bash
cd backend
alembic revision --autogenerate -m "description of changes"
```

This generates a new migration file in `alembic/versions/`.

### Apply Migrations

```bash
cd backend
alembic upgrade head        # Apply all pending migrations
alembic downgrade -1        # Revert last migration
```

### Check Migration Status

```bash
alembic current             # Show current revision
alembic history             # Show migration history
```

---

## 🧪 Running Tests

```bash
cd backend
pytest                      # Run all tests
pytest tests/ -v           # Verbose output
pytest tests/test_auth.py  # Run specific test file
```

---

## 📊 Monitoring & Logs

### Check Backend Logs (Docker)

```bash
docker-compose logs -f backend
```

### Check PostgreSQL Logs (Docker)

```bash
docker-compose logs -f postgres
```

### Connect to PostgreSQL Directly

```bash
psql -h localhost -U staxx -d staxx
```

Then query:
```sql
SELECT * FROM organizations;
SELECT * FROM users;
SELECT * FROM api_keys;
```

---

## 🔧 Common Issues & Fixes

### PostgreSQL Connection Error

**Error**: `psycopg.OperationalError: connection failed`

**Fix**:
- Ensure PostgreSQL is running: `pg_isready`
- Check `.env` credentials match your PostgreSQL setup
- Try: `psql -h localhost -U staxx -d staxx` to test connection

### Redis Connection Error

**Error**: `redis.exceptions.ConnectionError`

**Fix**:
- Ensure Redis is running: `redis-cli ping` (should return `PONG`)
- Check Redis host/port in `.env`

### Port Already in Use

**Error**: `Address already in use`

**Fix**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### Alembic Migration Issues

**Error**: `Target database is not up to date`

**Fix**:
```bash
cd backend
alembic current                    # Check current state
alembic upgrade head               # Apply all migrations
```

---

## 🚀 Running Celery Workers (Optional)

For async tasks (shadow evaluations, usage reporting), run Celery:

```bash
cd backend
celery -A app.workers worker --loglevel=info
```

---

## 📝 Environment Variables Reference

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `POSTGRES_SERVER` | — | ✅ | PostgreSQL hostname |
| `POSTGRES_USER` | — | ✅ | PostgreSQL user |
| `POSTGRES_PASSWORD` | — | ✅ | PostgreSQL password |
| `POSTGRES_DB` | — | ✅ | Database name |
| `POSTGRES_PORT` | 5432 | | PostgreSQL port |
| `REDIS_HOST` | — | ✅ | Redis hostname |
| `REDIS_PORT` | 6379 | | Redis port |
| `JWT_SECRET` | `change-me-in-production` | ✅ | JWT signing key (use production-grade secret) |
| `STRIPE_SECRET_KEY` | — | | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | — | | Stripe webhook signing secret |
| `STRIPE_PRICE_STARTER` | — | | Stripe price ID for Starter plan |
| `STRIPE_PRICE_GROWTH` | — | | Stripe price ID for Growth plan |
| `STRIPE_PRICE_ENTERPRISE` | — | | Stripe price ID for Enterprise plan |
| `APP_BASE_URL` | `http://localhost:3000` | | Frontend URL (for invite links) |

---

## 🔗 Connecting Frontend to Backend

The frontend (React) is configured to proxy API requests to the backend.

In `frontend/vite.config.js`:
```javascript
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  }
}
```

**To test the connection:**

1. Start backend: `cd backend && uvicorn app.main:app --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:3000/api/v1/docs — should show API docs
4. Try signing up via the dashboard UI

---

## ✅ Verification Checklist

After starting the backend, verify everything works:

- [ ] Backend running on http://localhost:8000
- [ ] API docs accessible at http://localhost:8000/api/v1/docs
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] PostgreSQL connected and migrations applied
- [ ] Redis connected and accessible
- [ ] Platform auth endpoints responding
- [ ] Frontend can reach backend API

---

## 🎯 Next Steps

1. **Create an organization & user** via `/auth/signup` endpoint
2. **Generate an API key** for programmatic access
3. **Connect the proxy** to start capturing LLM traffic
4. **Run shadow evaluations** to find cost-saving swaps
5. **Monitor ROI** via the dashboard

---

**For production deployment, see the Infrastructure & Deployment section in `staxx_v2_architecture_and_prompts.md`.**
