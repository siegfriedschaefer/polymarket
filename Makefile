.PHONY: help install dev-install test lint format clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install       - Install production dependencies"
	@echo "  make dev-install   - Install development dependencies"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linting checks"
	@echo "  make format        - Format code with black and ruff"
	@echo "  make clean         - Remove cache and build files"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-up     - Start Docker services"
	@echo "  make docker-down   - Stop Docker services"

install:
	pip install -r requirements.txt

dev-install:
	pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov/ build/ dist/

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

run:
	python -m polymarket_bot.main

celery-worker:
	celery -A polymarket_bot.tasks.celery_app worker --loglevel=info

celery-beat:
	celery -A polymarket_bot.tasks.celery_app beat --loglevel=info

flower:
	celery -A polymarket_bot.tasks.celery_app flower --port=5555
