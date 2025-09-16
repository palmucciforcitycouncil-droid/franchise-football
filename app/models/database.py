from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


def _default_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///franchise.db")


def get_engine(url: Optional[str] = None):
    url = url or _default_database_url()

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    return engine


class Base(DeclarativeBase):
    pass


_SessionLocal = None  # type: ignore[assignment]


def _ensure_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def create_db_and_tables(url: Optional[str] = None) -> None:
    engine = get_engine(url)
    from . import team, player, depth_chart, game_result, player_stats, user_profile  # noqa: F401
    Base.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    _ensure_session_factory()
    assert _SessionLocal is not None
    session: Session = _SessionLocal()  # type: ignore[call-arg]
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope(url: Optional[str] = None) -> Generator[Session, None, None]:
    engine = get_engine(url)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
