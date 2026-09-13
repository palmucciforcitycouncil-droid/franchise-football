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
    from app.models import coach  # noqa: F401
    from app.models import injury  # noqa: F401
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _migrate_schema(engine)


def _migrate_schema(engine) -> None:
    """No formal migration tool (Alembic) in this project yet -- create_all()
    only creates tables that don't exist, it never ALTERs an existing one, so
    a column added to a model after the table's first creation (e.g.
    Player.guaranteed_money, added 2026-09-13) needs a manual, idempotent
    ALTER TABLE here or every pre-existing DB file silently keeps the old
    schema and every insert referencing the new column fails."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(player)")}
        if "guaranteed_money" not in existing:
            conn.exec_driver_sql("ALTER TABLE player ADD COLUMN guaranteed_money INTEGER DEFAULT 0")
            conn.commit()


def get_session() -> Session:
    return Session(get_engine())
