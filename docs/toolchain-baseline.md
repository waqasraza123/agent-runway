# Toolchain baseline

## Runtime and tooling

- Python 3.12
- uv
- Ruff
- mypy
- pytest
- FastAPI
- SQLAlchemy
- Alembic
- Go 1.22 for the hybrid control-plane service

## Standard commands

Bootstrap:

    uv sync --group dev

Quality gates:

    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src tests
    uv run pytest -q
    make migration-check
    make export-openapi
    make check

Hybrid commands:

    make agent-worker-dev
    make api-go-dev
    make hybrid-up

## Storage modes

Memory mode is the default local developer path.

SQL mode is enabled with:

    STORAGE_BACKEND=sql
    DATABASE_URL=sqlite:///./.workdir/multi_agent_platform.db
    make migrate

PostgreSQL uses the same migration path:

    STORAGE_BACKEND=sql
    DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
    make migrate

## Notes

The platform is backend-first and API-driven.
The current repo is suitable for continued backend expansion and later production hardening.
