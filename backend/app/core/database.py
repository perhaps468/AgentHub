from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    return {
        "pool_pre_ping": True,
    }


engine = create_engine(get_settings().database_url, **_engine_kwargs(get_settings().database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def configure_database(database_url: str, *, create_schema: bool = False) -> None:
    global engine, SessionLocal

    engine = create_engine(database_url, **_engine_kwargs(database_url))
    SessionLocal.configure(bind=engine)
    if create_schema:
        from app.models import agent, message, orchestration, pending_change, session, session_member, workspace  # noqa: F401

        Base.metadata.create_all(bind=engine)

        # 预置内置 Agent
        from app.agents.seed import seed_builtin_agents
        with SessionLocal() as db:
            seed_builtin_agents(db)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
