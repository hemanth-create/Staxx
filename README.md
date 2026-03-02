# LLM Cost Efficiency Intelligence (The "LLM CFO")

> *"For each use case in your production system, which model gives equivalent quality at lower cost — and how confident are we?"*

This repository contains the MVP for an enterprise-grade LLM routing and intelligence platform. It acts as an intelligence layer that intercepts production traffic, calculates real-time API spend via a Time-Series Database, and asynchronously runs "Shadow Evaluations" against cheaper models (like Claude 3.5 Haiku) to mathematically prove cost-saving swap opportunities without risking production degradation.

## 🏗️ Architecture

1. **`sdk/` (Python Drop-in Client)**: Frictionless wrapper around standard `openai` and `anthropic` clients tracking latency and tokens silently.
2. **`backend/` (FastAPI + Celery)**: The execution core handling traffic ingestion, real-time cost calculation, and dispatching shadow evaluations.
3. **`frontend/` (React + Tailwind + Recharts)**: The "Cost Intelligence" dashboard visualizing the TimescaleDB aggregations.
4. **`infrastructure/`**: Docker configurations for TimescaleDB (Postgres), Redis (Queues & Caching), and MinIO (S3 output storage).

---

## 🚀 Getting Started Locally

Running the full stack requires Docker (for the databases) and two Python terminals.

### Prerequisites
* **Python 3.11+**
* **Node.js 18+**
* **Docker Desktop** (Must be running on your machine)

### 1. Start the Infrastructure (Databases)

First, spin up Postgres (TimescaleDB), Redis, and MinIO locally:

```powershell
cd infrastructure/docker
docker compose up -d
```
*(Verify they are running by opening Docker Desktop or running `docker ps`)*

---

### 2. Start the Backend API

Open a new terminal at the root of the project and set up the Python environment:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate

# Install requirements
pip install -r requirements.txt

# Run database migrations to create the tables and TimescaleDB hypertable
alembic upgrade head

# Start the FastAPI Server
uvicorn app.main:app
```
*The API is now running at `http://localhost:8000`*

---

### 3. Start the Celery Worker

The API is fast because it pushes all heavy lifting (token counting, cost calculation, shadow evals) to a background worker. Open **another** terminal:

```powershell
cd backend
.\venv\Scripts\Activate

# Start the Celery worker
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```
*(Note: `--pool=solo` is added for Windows compatibility with Celery)*

---

### 4. Start the Frontend Dashboard

Open a final terminal to run the UI:

```powershell
cd frontend
npm install
npm run dev
```

*The dashboard is now running at `http://localhost:3000`*

---

## 🧪 Testing the Pipeline (Simulating SDK Traffic)

Once all 4 components (Docker, API, Worker, Frontend) are running, you can simulate a production call intercept from the SDK to see the dashboard update in real-time.

Send a POST request to the local API:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/capture" -Method Post -ContentType "application/json" -Body '{
    "model": "gpt-4o-2024-08-06",
    "task_type": "extraction",
    "input_tokens": 1550,
    "output_tokens": 420,
    "latency_ms": 1120.5
}'
```

Watch the Celery terminal process the incoming metric, calculate the cost, and insert it into TimescaleDB. Then, refresh your `http://localhost:3000` dashboard to see the charts update with live data.

---

## 🛑 Troubleshooting

* **`connection refused` on backend startup:** Ensure Docker is running and the `llm_intel_db` and `llm_intel_redis` containers are up.
* **Celery hangs on Windows:** Celery's default prefork pool doesn't work natively on Windows. Always run the worker with the `--pool=solo` flag locally.
* **Frontend shows "Demonstration Data":** The React app falls back to stub data if it cannot reach `http://localhost:8000/api/v1/costs/breakdown`. Ensure the backend terminal is running.
