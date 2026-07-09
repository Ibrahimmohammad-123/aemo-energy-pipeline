.PHONY: install install-dev test lint format ingest dbt-deps dbt-run dbt-test dbt-build metabase-up metabase-down

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,dbt]"
	pre-commit install

test:
	pytest -v

lint:
	ruff check .
	black --check .
	isort --check-only .

format:
	black .
	isort .
	ruff check --fix .

ingest:
	python -m ingestion.run

dbt-deps:
	cd dbt_project && dbt deps

dbt-run:
	cd dbt_project && dbt run --target duckdb

dbt-test:
	cd dbt_project && dbt test --target duckdb

dbt-build:
	cd dbt_project && dbt build --target duckdb

metabase-up:
	docker compose up -d

metabase-down:
	docker compose down
