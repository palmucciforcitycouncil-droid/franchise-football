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
        # Every DB this process opens (the template, the legacy file, each
        # save's own franchise.db, test copies) is brought up to the
        # current schema here, once per engine -- the hand-maintained
        # per-file migration scripts kept missing save databases (see
        # HANDOFF 2026-09-14's focus_area incident).
        if DB_PATH.exists():
            _migrate_schema(_engine)
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
        if not existing:
            return  # empty DB -- create_all() builds the current schema
        if "guaranteed_money" not in existing:
            conn.exec_driver_sql("ALTER TABLE player ADD COLUMN guaranteed_money INTEGER DEFAULT 0")
            conn.commit()
        for column, ddl in _PLAYER_COLUMNS_ADDED_2026_09_14:
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE player ADD COLUMN {column} {ddl}")
                conn.commit()
        for column, ddl in _PLAYER_COLUMNS_ADDED_2026_09_15:
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE player ADD COLUMN {column} {ddl}")
                conn.commit()
        coach_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(coach)")}
        if coach_cols and "focus_area" not in coach_cols:
            conn.exec_driver_sql("ALTER TABLE coach ADD COLUMN focus_area TEXT NOT NULL DEFAULT 'Development'")
            conn.commit()
        # 2026-09-14 position unification: idempotent -- a no-op once no
        # legacy left/right codes remain. SQLModel stores the Enum NAME,
        # which equals the value for every Position member.
        from app.models.player import LEGACY_POSITION_MAP
        for old, new in LEGACY_POSITION_MAP.items():
            conn.exec_driver_sql("UPDATE player SET position = ? WHERE position = ?", (new, old))
        conn.commit()


# (column, SQL type/default) -- see app/models/player.py for each field.
_PLAYER_COLUMNS_ADDED_2026_09_14: list[tuple[str, str]] = [
    ("acquisition_type", "TEXT"),
    ("acquisition_season", "INTEGER"),
    ("acquisition_round", "INTEGER"),
    ("acquisition_pick", "INTEGER"),
    ("acquisition_team", "TEXT"),
]

# R16 (docs/R16_PRACTICE_SQUAD_ROSTER_IR_SPECIFICATION.md Sec 3.1) --
# every existing player defaults to ACTIVE, deliberately: every
# currently-oversized team (54-72 real players, nothing ever enforced
# the 53-man cap before this) hits the new over-53 gate on next load.
_PLAYER_COLUMNS_ADDED_2026_09_15: list[tuple[str, str]] = [
    ("roster_status", "TEXT NOT NULL DEFAULT 'ACTIVE'"),
    ("roster_lock_until_week", "INTEGER"),
    ("poached_from_team_abbr", "TEXT"),
    ("ps_protected", "INTEGER NOT NULL DEFAULT 0"),
    ("ir_placed_week", "INTEGER"),
]


def get_session() -> Session:
    return Session(get_engine())
