# SerenityAI - Makefile for common development tasks
# Makes Docker operations easier

.PHONY: help build up down logs shell db-shell redis-shell test clean

# Default target
help:
	@echo "SerenityAI - Development Commands"
	@echo ""
	@echo "Docker Operations:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all services"
	@echo "  make up-dev      - Start services in development mode (hot-reload)"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs from all services"
	@echo "  make logs-app    - View app logs only"
	@echo ""
	@echo "Shell Access:"
	@echo "  make shell       - Open shell in app container"
	@echo "  make db-shell    - Open PostgreSQL shell"
	@echo "  make redis-shell - Open Redis CLI"
	@echo ""
	@echo "Database:"
	@echo "  make db-init     - Initialize database with schema"
	@echo "  make db-reset    - Reset database (WARNING: deletes all data)"
	@echo "  make db-backup   - Backup database to ./backups/"
	@echo ""
	@echo "Development Tools:"
	@echo "  make tools       - Start with pgAdmin and Redis Commander"
	@echo "  make test        - Run tests in Docker"
	@echo "  make clean       - Remove containers and volumes"
	@echo "  make clean-all   - Remove everything including images"
	@echo ""
	@echo "Health Checks:"
	@echo "  make health      - Check service health"
	@echo "  make metrics     - View service metrics"

# Build Docker images
build:
	docker-compose build

# Start services (production mode)
up:
	docker-compose up -d

# Start services (development mode with hot-reload)
up-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Start with development tools (pgAdmin, Redis Commander)
tools:
	docker-compose --profile tools up -d
	@echo "pgAdmin: http://localhost:5050 (admin@serenityai.local / admin)"
	@echo "Redis Commander: http://localhost:8081"

# Stop all services
down:
	docker-compose down

# Restart services
restart:
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

# View app logs only
logs-app:
	docker-compose logs -f app

# Open shell in app container
shell:
	docker-compose exec app /bin/bash

# Open PostgreSQL shell
db-shell:
	docker-compose exec postgres psql -U postgres -d serenityai

# Open Redis CLI
redis-shell:
	docker-compose exec redis redis-cli -a serenity_redis_password

# Initialize database
db-init:
	docker-compose exec postgres psql -U postgres -d serenityai -f /docker-entrypoint-initdb.d/init-db.sql

# Reset database (WARNING: deletes all data)
db-reset:
	@echo "WARNING: This will delete all database data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS serenityai;"; \
		docker-compose exec postgres psql -U postgres -c "CREATE DATABASE serenityai;"; \
		make db-init; \
		echo "Database reset complete!"; \
	fi

# Backup database
db-backup:
	@mkdir -p backups
	@echo "Backing up database..."
	docker-compose exec -T postgres pg_dump -U postgres serenityai > backups/serenity_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup complete! Check backups/ directory"

# Run tests
test:
	docker-compose exec app pytest -v

# Health check
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | python3 -m json.tool
	@echo ""
	@curl -s http://localhost:8000/health/detailed | python3 -m json.tool

# View metrics
metrics:
	@curl -s http://localhost:8000/metrics | python3 -m json.tool

# Clean up containers and volumes
clean:
	docker-compose down -v
	@echo "Containers and volumes removed!"

# Clean everything including images
clean-all:
	docker-compose down -v --rmi all
	@echo "Everything removed!"

# Install local dependencies (for IDE support)
install:
	pip install -r requirements.txt

# Format code
format:
	black .
	isort .

# Lint code
lint:
	flake8 .
	mypy .
