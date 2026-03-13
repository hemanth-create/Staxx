.PHONY: help up down build restart logs seed migrate test clean shell-db shell-be

help:
	@echo "Staxx Intelligence - Local Development"
	@echo ""
	@echo "Usage:"
	@echo "  make up              Start all services"
	@echo "  make down            Stop all services"
	@echo "  make build           Rebuild all images"
	@echo "  make restart         Restart all services"
	@echo "  make logs            Tail logs from all services"
	@echo "  make seed            Load development seed data"
	@echo "  make migrate         Run Alembic database migrations"
	@echo "  make test            Run backend tests"
	@echo "  make clean           Remove containers and volumes (data loss!)"
	@echo "  make shell-db        Open PostgreSQL shell"
	@echo "  make shell-be        Open backend bash shell"

up:
	@echo "🚀 Starting Staxx Intelligence stack..."
	docker compose up -d
	@echo ""
	@echo "✨ Services starting:"
	@echo "   🐘 PostgreSQL    → localhost:5432"
	@echo "   📦 Redis         → localhost:6379"
	@echo "   🪣 MinIO         → localhost:9000 (console: localhost:9001)"
	@echo "   ⚡ Backend       → localhost:8000"
	@echo "   🔄 Proxy         → localhost:8080"
	@echo "   ⚙️ Frontend      → localhost:3000"
	@echo ""
	@echo "   Run 'make migrate' to set up the database"
	@echo "   Run 'make seed' to load development data"

down:
	@echo "⏹️  Stopping services..."
	docker compose down

build:
	@echo "🔨 Rebuilding all images..."
	docker compose build --no-cache

restart: down up

logs:
	@echo "📋 Tailing logs (Ctrl+C to exit)..."
	docker compose logs -f

seed:
	@echo "🌱 Seeding development data..."
	docker compose exec backend python scripts/seed-data.py

migrate:
	@echo "🔄 Running Alembic migrations..."
	docker compose exec backend alembic upgrade head
	@echo "✓ Migrations complete"

test:
	@echo "🧪 Running backend tests..."
	docker compose exec backend pytest tests/ -v --tb=short

clean:
	@echo "⚠️  WARNING: This will delete all containers and volumes (including database data)"
	@read -p "Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker compose down -v; \
		echo "✓ Cleaned up"; \
	fi

shell-db:
	@echo "🐘 Opening PostgreSQL shell (user: staxx)..."
	docker compose exec postgres psql -U staxx -d staxx

shell-be:
	@echo "🐍 Opening backend bash shell..."
	docker compose exec backend bash

.DEFAULT_GOAL := help
