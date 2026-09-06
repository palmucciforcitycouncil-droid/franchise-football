"""SQLite/SQLModel engine (GDD Part 1 Sec 1.2: SQLModel/SQLite for data persistence)."""
from __future__ import annotations
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

DB_PATH = Path("data/franchise_football.db")
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    return _engine


def init_db() -> None:
    # Import models here (not at module load) so this module doesn't force
    # every model module to exist before it's needed.
    from app.models import player  # noqa: F401
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Session:
    return Session(get_engine())
