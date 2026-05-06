from pathlib import Path
from tempfile import TemporaryDirectory

from multi_agent_platform.storage.db.migrations import (
    check_migration_script_current,
    migrate_database_schema,
)


def main() -> None:
    with TemporaryDirectory() as temporary_directory:
        database_url = f"sqlite:///{Path(temporary_directory) / 'migration_check.db'}"
        migrate_database_schema(database_url)
        check_migration_script_current(database_url)


if __name__ == "__main__":
    main()
