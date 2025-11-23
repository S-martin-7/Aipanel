# AIPanel - Development Makefile
# Usage: make [target]

.PHONY: help setup run dev services stop migrate test lint clean

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help: ## Show this help message
	@echo "$(BLUE)AIPanel - Available commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================================
# Setup
# ============================================================

setup: ## Install all dependencies
	@echo "$(YELLOW)Setting up backend...$(NC)"
	cd backend && python3 -m venv venv && \
		. venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r requirements.txt -r requirements-dev.txt
	@echo "$(GREEN)✓ Setup complete$(NC)"

install: setup ## Alias for setup

# ============================================================
# Services (Docker)
# ============================================================

services: ## Start PostgreSQL and Redis with Docker
	@echo "$(YELLOW)Starting services...$(NC)"
	docker-compose up -d postgres redis
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"

services-all: ## Start all services including admin tools
	docker-compose --profile tools up -d

stop: ## Stop all Docker services
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

logs: ## Show Docker service logs
	docker-compose logs -f

# ============================================================
# Database
# ============================================================

migrate: ## Run database migrations
	cd backend && . venv/bin/activate && alembic upgrade head

migrate-new: ## Create new migration (usage: make migrate-new msg="description")
	cd backend && . venv/bin/activate && alembic revision --autogenerate -m "$(msg)"

migrate-down: ## Rollback last migration
	cd backend && . venv/bin/activate && alembic downgrade -1

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(YELLOW)Resetting database...$(NC)"
	docker-compose exec postgres psql -U aipanel -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) migrate
	@echo "$(GREEN)✓ Database reset$(NC)"

# ============================================================
# Development
# ============================================================

run: ## Start backend development server
	cd backend && . venv/bin/activate && \
		uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev: services run ## Start services and backend server

backend: run ## Alias for run

# ============================================================
# Testing & Linting
# ============================================================

test: ## Run tests
	cd backend && . venv/bin/activate && pytest tests/ -v

test-cov: ## Run tests with coverage
	cd backend && . venv/bin/activate && pytest tests/ -v --cov=app --cov-report=html

lint: ## Run linters
	cd backend && . venv/bin/activate && ruff check app/ --fix

format: ## Format code
	cd backend && . venv/bin/activate && ruff format app/

check: lint test ## Run linters and tests

# ============================================================
# Utilities
# ============================================================

shell: ## Open Python shell with app context
	cd backend && . venv/bin/activate && python3 -i -c "from app.models import *; print('Models loaded')"

clean: ## Clean cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cache cleaned$(NC)"

# ============================================================
# Production
# ============================================================

build: ## Build Docker image for production
	docker build -t aipanel-backend:latest ./backend

prod: ## Run in production mode
	cd backend && . venv/bin/activate && \
		gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
