# ===========================================
# Horizon Sync Backend - Makefile
# ===========================================

.PHONY: help install up down restart logs build test lint seed clean

# Default target
help:
	@echo "Horizon Sync Backend - Available Commands"
	@echo "=========================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install         - Install dev dependencies & pre-commit hooks"
	@echo ""
	@echo "Docker:"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make logs            - View logs (all services)"
	@echo "  make logs-identity   - View Identity Service logs"
	@echo "  make logs-core       - View Core Service logs"
	@echo "  make build           - Rebuild all services"
	@echo "  make clean           - Stop services and remove volumes"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests (in Docker)"
	@echo "  make test-local      - Run all tests (local Python)"
	@echo "  make test-identity   - Run Identity Service tests"
	@echo "  make test-core       - Run Core Service tests"
	@echo "  make test-cov        - Run tests with coverage"
	@echo ""
	@echo "Linting:"
	@echo "  make lint            - Run linters on all services"
	@echo "  make lint-fix        - Run linters and auto-fix"
	@echo "  make format          - Format all Python code"
	@echo ""
	@echo "Database:"
	@echo "  make seed            - Re-seed all databases"
	@echo "  make migrate         - Run all migrations"
	@echo ""
	@echo "Shell Access:"
	@echo "  make shell-identity  - Shell into Identity Service"
	@echo "  make shell-core      - Shell into Core Service"
	@echo "  make db-shell        - Shell into PostgreSQL"
	@echo ""

# ===========================================
# Setup & Installation
# ===========================================

install:
	@echo "Installing development dependencies..."
	pip install -r requirements-dev.txt
	@echo "Installing pre-commit hooks..."
	pre-commit install
	pre-commit install --hook-type pre-push
	@echo "Done! Run 'make up' to start services."

# ===========================================
# Docker Compose Commands
# ===========================================

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

logs-identity:
	docker compose logs -f identity-service

logs-core:
	docker compose logs -f core-service

logs-db:
	docker compose logs -f postgres

build:
	docker compose build --no-cache

clean:
	docker compose down -v --remove-orphans

# ===========================================
# Service-specific commands
# ===========================================

up-identity:
	docker compose up -d postgres identity-service

up-core:
	docker compose up -d postgres identity-service core-service

# ===========================================
# Testing (Docker)
# ===========================================

test:
	@echo "Running Identity Service tests..."
	docker compose exec identity-service pytest -v
	@echo ""
	@echo "Running Core Service tests..."
	docker compose exec core-service pytest -v

test-identity:
	docker compose exec identity-service pytest -v

test-core:
	docker compose exec core-service pytest -v

test-cov:
	@echo "Running tests with coverage..."
	docker compose exec identity-service pytest --cov=app --cov-report=term-missing --cov-report=html
	docker compose exec core-service pytest --cov=app --cov-report=term-missing --cov-report=html

# ===========================================
# Testing (Local - for pre-commit)
# ===========================================

test-local:
	@echo "Running all tests locally..."
	cd identity-service && python -m pytest tests/ -v --tb=short
	cd core-service && python -m pytest tests/ -v --tb=short

test-local-identity:
	cd identity-service && python -m pytest tests/ -v

test-local-core:
	cd core-service && python -m pytest tests/ -v

# ===========================================
# Linting & Formatting
# ===========================================

lint:
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files

lint-fix:
	@echo "Running ruff with auto-fix..."
	ruff check --fix identity-service/ core-service/
	ruff format identity-service/ core-service/

format:
	@echo "Formatting all Python code..."
	ruff format identity-service/app/ identity-service/tests/
	ruff format core-service/app/ core-service/tests/

check:
	@echo "Running ruff check (no fix)..."
	ruff check identity-service/ core-service/

# ===========================================
# Database
# ===========================================

seed:
	docker compose exec identity-service python scripts/seed_data.py
	docker compose exec core-service python scripts/seed_data.py

migrate:
	docker compose exec identity-service python -m alembic upgrade head
	docker compose exec core-service python -m alembic upgrade head

migrate-identity:
	docker compose exec identity-service python -m alembic upgrade head

migrate-core:
	docker compose exec core-service python -m alembic upgrade head

# ===========================================
# Shell Access
# ===========================================

shell-identity:
	docker compose exec identity-service bash

shell-core:
	docker compose exec core-service bash

db-shell:
	docker compose exec postgres psql -U horizon_user -d horizon_db

# ===========================================
# Development Helpers
# ===========================================

status:
	docker compose ps

health:
	@echo "Identity Service:"
	@curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "Core Service:"
	@curl -s http://localhost:8001/health | python -m json.tool 2>/dev/null || echo "  Not running"

# ===========================================
# Pre-commit helpers
# ===========================================

pre-commit-install:
	pre-commit install
	pre-commit install --hook-type pre-push

pre-commit-update:
	pre-commit autoupdate

pre-commit-run:
	pre-commit run --all-files
