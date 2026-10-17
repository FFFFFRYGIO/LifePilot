# Recipes are plain commands so they work from Git Bash, PowerShell and cmd alike.
PY := uv run python
PORT ?= 8000

.DEFAULT_GOAL := help
.PHONY: help install hooks db db-stop migrate css css-watch superuser run dev \
        test lint fmt typecheck check docker-up docker-down

help:
	@echo "make install     - install dependencies (uv sync) and git hooks"
	@echo "make dev         - start db, migrate, build CSS and run the dev server on PORT=$(PORT)"
	@echo "make run         - run the dev server only"
	@echo "make db          - start PostgreSQL (docker compose, localhost:55433)"
	@echo "make db-stop     - stop PostgreSQL"
	@echo "make migrate     - apply database migrations"
	@echo "make css         - build Tailwind CSS   (css-watch: rebuild on change)"
	@echo "make superuser   - create a login for the web UI"
	@echo "make test        - run the test suite (needs make db)"
	@echo "make lint        - ruff lint + format check"
	@echo "make fmt         - ruff autofix + format"
	@echo "make typecheck   - mypy"
	@echo "make check       - all pre-commit hooks on all files"
	@echo "make docker-up   - build and run db + web in Docker"

install:
	uv sync
	uv run pre-commit install

hooks:
	uv run pre-commit install

db:
	docker compose up -d --wait db

db-stop:
	docker compose stop db

migrate:
	$(PY) manage.py migrate

css:
	$(PY) manage.py tailwind build

css-watch:
	$(PY) manage.py tailwind watch

superuser:
	$(PY) manage.py createsuperuser

run:
	$(PY) manage.py runserver $(PORT)

dev: db migrate css run

test:
	$(PY) -m pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	$(PY) -m mypy .

check:
	uv run pre-commit run --all-files

docker-up:
	docker compose --profile app up --build

docker-down:
	docker compose --profile app down
