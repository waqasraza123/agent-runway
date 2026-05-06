from pathlib import Path

import pytest
from sqlalchemy import inspect

from multi_agent_platform.storage.db.migrations import (
    DatabaseSchemaNotCurrentError,
    assert_database_schema_current,
    migrate_database_schema,
)
from multi_agent_platform.storage.db.session import get_engine


def test_migration_creates_current_schema(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"

    migrate_database_schema(database_url)

    engine = get_engine(database_url)
    with engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())

    assert_database_schema_current(database_url)
    assert {
        "alembic_version",
        "run_approvals",
        "run_events",
        "run_llm_calls",
        "run_outputs",
        "run_plans",
        "run_states",
        "run_tool_calls",
        "run_turns",
        "run_verifications",
    }.issubset(table_names)


def test_schema_validation_rejects_unmigrated_database(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'unmigrated.db'}"

    with pytest.raises(DatabaseSchemaNotCurrentError):
        assert_database_schema_current(database_url)
