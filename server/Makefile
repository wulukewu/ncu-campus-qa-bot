# Makefile for NCU Campus QA Bot

.PHONY: help dev prod build up down logs restart clean test shell

# Default target
help:
	@echo "🤖 NCU Campus QA Bot - Docker Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment (with hot reload)"
	@echo "  make dev-build    - Build and start development environment"
	@echo "  make dev-down     - Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start production environment"
	@echo "  make prod-build   - Build and start production environment"
	@echo "  make prod-down    - Stop production environment"
	@echo ""
	@echo "Common:"
	@echo "  make logs         - View logs (all services)"
	@echo "  make logs-rag     - View RAG server logs"
	@echo "  make logs-bot     - View LINE bot logs"
	@echo "  make restart      - Restart all services"
	@echo "  make restart-rag  - Restart RAG server only"
	@echo "  make restart-bot  - Restart LINE bot only"
	@echo "  make ps           - Show running containers"
	@echo ""
	@echo "Maintenance:"
	@echo "  make shell-rag    - Open shell in RAG server container"
	@echo "  make shell-bot    - Open shell in LINE bot container"
	@echo "  make setup-db     - Build vector database locally (before first run)"
	@echo "  make build-db     - Build vector database in container"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make test-health  - Test service health endpoints"

# Development commands
dev:
	docker-compose up

dev-build:
	docker-compose up --build

dev-down:
	docker-compose down

dev-logs:
	docker-compose logs -f

# Production commands
prod:
	docker-compose -f docker-compose.prod.yml up -d

prod-build:
	docker-compose -f docker-compose.prod.yml up --build -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

# Logs
logs:
	docker-compose logs -f

logs-rag:
	docker-compose logs -f rag-server

logs-bot:
	docker-compose logs -f linebot

# Restart services
restart:
	docker-compose restart

restart-rag:
	docker-compose restart rag-server

restart-bot:
	docker-compose restart linebot

# Container management
ps:
	docker-compose ps

stop:
	docker-compose stop

down:
	docker-compose down

clean:
	docker-compose down -v
	docker system prune -f

# Shell access
shell-rag:
	docker-compose exec rag-server /bin/bash

shell-bot:
	docker-compose exec linebot /bin/bash

# Database operations
build-db:
	docker-compose exec rag-server python DBHandler.py

build-db-local:
	./build_database.sh

setup-db:
	@echo "🏗️  Building vector database..."
	@./build_database.sh

# Health checks
test-health:
	@echo "Testing RAG Server health..."
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ RAG Server not responding"
	@echo ""
	@echo "Testing LINE Bot health..."
	@curl -s http://localhost:5000/ | python3 -m json.tool || echo "❌ LINE Bot not responding"

# Build specific services
build-rag:
	docker-compose build rag-server

build-bot:
	docker-compose build linebot

# Quick shortcuts
up: dev
down-all: dev-down prod-down
rebuild: clean dev-build
