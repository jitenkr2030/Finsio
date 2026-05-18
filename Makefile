.PHONY: help setup dev dev-down test lint seed export-bc verify migrate shell logs clean build

help:
	@echo ""
	@echo "  Finsio — Financial Operations Platform"
	@echo "  ========================================"
	@echo ""
	@echo "  Development"
	@echo "    make setup         Full initial setup (env, deps, db, seed)"
	@echo "    make dev           Start development environment"
	@echo "    make dev-down      Stop all containers"
	@echo "    make logs          Tail all container logs"
	@echo "    make shell         Open Django management shell"
	@echo "    make php-shell     Open Fusio interactive shell"
	@echo ""
	@echo "  Database"
	@echo "    make migrate       Run Django migrations"
	@echo "    make makemigrations Create new Django migrations"
	@echo "    make fusio-migrate Run Fusio database migrations"
	@echo ""
	@echo "  Code Quality"
	@echo "    make test          Run full test suite with coverage"
	@echo "    make lint          Run ruff linter + mypy type checks"
	@echo "    make format        Auto-format code with ruff"
	@echo ""
	@echo "  Data"
	@echo "    make seed          Load sample development data"
	@echo "    make export-bc     Export transactions to beancount files"
	@echo "    make verify        Run integration health checks"
	@echo ""
	@echo "  Production"
	@echo "    make prod          Start production environment"
	@echo "    make prod-down     Stop production environment"
	@echo "    make build         Build all Docker images"
	@echo "    make clean         Remove all containers, volumes, and images"
	@echo ""

setup:
	@bash scripts/setup.sh

dev:
	docker compose up -d
	@echo ""
	@echo "  Gateway:     http://localhost:8080"
	@echo "  Backend:     http://localhost:8000"
	@echo "  Proxy:       http://localhost:80"
	@echo "  Django Admin http://localhost:8000/django-admin/"
	@echo ""

dev-down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec backend python manage.py shell_plus || docker compose exec backend python manage.py shell

php-shell:
	docker compose exec gateway php bin/fusio shell

migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

fusio-migrate:
	docker compose exec gateway php bin/fusio migration:execute

test:
	docker compose exec backend pytest --cov=apps --cov-report=term-missing --tb=short -v

lint:
	docker compose exec backend ruff check apps/ finsio/
	docker compose exec backend mypy apps/ --ignore-missing-imports

format:
	docker compose exec backend ruff format apps/ finsio/
	docker compose exec backend ruff check --fix apps/ finsio/

seed:
	docker compose exec backend python scripts/seed_data.py

export-bc:
	docker compose exec backend python scripts/export_beancount.py

verify:
	docker compose exec backend python scripts/verify_integration.py

prod:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

build:
	docker compose build --no-cache

clean:
	docker compose down -v --rmi local --remove-orphans
	docker compose -f docker-compose.prod.yml down -v --rmi local --remove-orphans 2>/dev/null || true

redis-cli:
	docker compose exec redis redis-cli

psql:
	docker compose exec postgres psql -U finsio -d finsio

backup-db:
	docker compose exec postgres pg_dump -U finsio -d finsio > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Database backup created."
