from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def _prepare_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        database_path = database_url.removeprefix("sqlite:///")
        if database_path not in {":memory:", ""}:
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    return database_url


@lru_cache
def get_engine(database_url: str) -> Engine:
    import multi_agent_platform.storage.db.models as models_module

    _ = models_module
    normalized_database_url = _prepare_database_url(database_url)
    connect_args = (
        {"check_same_thread": False} if normalized_database_url.startswith("sqlite") else {}
    )
    return create_engine(
        normalized_database_url,
        future=True,
        connect_args=connect_args,
    )


@lru_cache
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = get_engine(database_url)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
