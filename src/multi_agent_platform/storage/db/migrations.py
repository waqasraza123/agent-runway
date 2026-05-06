from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from multi_agent_platform.storage.db.session import _prepare_database_url, get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATABASE_URL = "sqlite:///./.workdir/multi_agent_platform.db"


class DatabaseSchemaNotCurrentError(RuntimeError):
    pass


def build_alembic_config(database_url: str = DEFAULT_DATABASE_URL) -> Config:
    normalized_database_url = _prepare_database_url(database_url)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", normalized_database_url)
    config.attributes["database_url"] = normalized_database_url
    return config


def migrate_database_schema(database_url: str = DEFAULT_DATABASE_URL) -> None:
    command.upgrade(build_alembic_config(database_url), "head")


def check_migration_script_current(database_url: str = DEFAULT_DATABASE_URL) -> None:
    command.check(build_alembic_config(database_url))


def assert_database_schema_current(database_url: str = DEFAULT_DATABASE_URL) -> None:
    config = build_alembic_config(database_url)
    engine = get_engine(database_url)
    script_directory = ScriptDirectory.from_config(config)
    expected_revision = script_directory.get_current_head()

    with engine.connect() as connection:
        table_names = inspect(connection).get_table_names()
        if "alembic_version" not in table_names:
            raise DatabaseSchemaNotCurrentError(
                "Database schema is not migrated. Run `make migrate` before using SQL storage."
            )

        current_revision = MigrationContext.configure(connection).get_current_revision()

    if current_revision != expected_revision:
        raise DatabaseSchemaNotCurrentError(
            "Database schema revision is "
            f"{current_revision or 'unset'}, expected {expected_revision}. Run `make migrate`."
        )
