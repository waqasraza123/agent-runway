import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from multi_agent_platform.storage.db import models as models_module
from multi_agent_platform.storage.db.base import Base

_ = models_module

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    return (
        config.attributes.get("database_url")
        or os.getenv("DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
        or "sqlite:///./.workdir/multi_agent_platform.db"
    )


def prepare_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        database_path = database_url.removeprefix("sqlite:///")
        if database_path not in {":memory:", ""}:
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    return database_url


def run_migrations_offline() -> None:
    url = prepare_database_url(get_database_url())
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = prepare_database_url(get_database_url())
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
