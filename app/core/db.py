"""SQLite/SQLModel engine (GDD Part 1 Sec 1.2: SQLModel/SQLite for data persistence)."""
from __future__ import annotations
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

DB_PATH = Path("data/franchise_football.db")
_engine = None
_engine_path: Path | None = None


def get_engine():
    """Re-creates the cached engine if DB_PATH has changed since the
    last call -- lets tests that need to WRITE to the roster (e.g.
    Player Progression & Regression, GDD Sec 7.6) safely redirect
    DB_PATH to a throwaway copy first, same convention as
    save_service.DEFAULT_SAVE_PATH/gameplan_store.DEFAULT_PATH. Every
    read-only test in this codebase uses the real DB_PATH unchanged, so
    this has no effect on them."""
    global _engine, _engine_path
    if _engine is None or _engine_path != DB_PATH:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        _engine_path = DB_PATH
    return _engine


def init_db() -> None:
    # Import models here (not at module load) so this module doesn't force
    # every model module to exist before it's needed.
    from app.models import player  # noqa: F401
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Session:
    return Session(get_engine())
