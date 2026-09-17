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
        for column in _COACH_COLUMNS_ADDED_2026_09_15:
            if coach_cols and column not in coach_cols:
                conn.exec_driver_sql(f"ALTER TABLE coach ADD COLUMN {column} INTEGER DEFAULT 50")
                conn.commit()
        # R16 ST role removal (docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md
        # Sec 9): every existing 'ST' row becomes an AC with a "Special
        # Teams" specialty -- a real org-chart demotion, not a firing, so
        # their salary/contract/tenure are all left untouched. Idempotent
        # (a no-op once no ST rows remain); CoachRole itself no longer HAS
        # an ST member, so leaving a stale row unmigrated isn't just
        # cosmetic -- SQLAlchemy raises a LookupError deserializing ANY
        # query that touches it. This can leave a team at 5 ACs (one over
        # MAX_ASSISTANTS) right after migration -- same "grandfathered
        # over the new cap until it naturally resolves" precedent as the
        # 53-man roster cap's own migration (nothing forces a fire here).
        if coach_cols:
            conn.exec_driver_sql(
                "UPDATE coach SET role = 'AC', specialty = 'Special Teams' WHERE role = 'ST'")
            conn.commit()
        # R16 renamed 3 of the R13-era focus_area string values (the
        # taxonomy redesign kept the underlying concept but not always
        # the label) -- an existing coach's stored value otherwise keeps
        # the pre-R16 string forever, which is invisible in the UI (it's
        # just displayed as-is) but breaks anything that compares against
        # the current FOCUS_* constants by value, e.g. "is this HC
        # currently on their fixed role default." Idempotent, same
        # LEGACY_POSITION_MAP-style UPDATE pattern as position
        # unification below.
        if coach_cols:
            for old, new in _LEGACY_FOCUS_AREA_MAP.items():
                conn.exec_driver_sql("UPDATE coach SET focus_area = ? WHERE focus_area = ?", (new, old))
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

# R16 Coaching Overhaul (docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md
# Sec 1) -- the 8 granular position-group coaching ratings replacing the
# old flat player_dev_offense/defense split (now computed properties, not
# stored columns -- see app/models/coach.py). Every existing coach
# defaults to a neutral 50, same convention as every other rating here.
# This was missing from the original commit that introduced these
# columns (ceea89b5), which only ever ran against a freshly created
# table -- any pre-existing coach table silently kept the old schema and
# every Coach query failed with "no such column," caught by coach_store's
# own OperationalError-tolerant has_coaches()/all_coaches() and
# misreported as "no coaches imported."
_COACH_COLUMNS_ADDED_2026_09_15: list[str] = [
    "qb_coaching", "rb_coaching", "wr_coaching", "ol_coaching",
    "dl_coaching", "lb_coaching", "secondary_coaching", "st_coaching",
]

# R16's Focus Area taxonomy redesign renamed these 3 string values (see
# app/models/coach.py's FOCUS_* constants); everything else kept its
# R13-era label unchanged.
_LEGACY_FOCUS_AREA_MAP: dict[str, str] = {
    "OF Gameplan": "Offensive Gameplan",
    "DF Gameplan": "Defensive Gameplan",
    "Special Teams Work": "Special Teams",
    "Training": "Strength & Conditioning",
}


def get_session() -> Session:
    return Session(get_engine())
