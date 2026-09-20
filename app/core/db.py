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
        if "legacy_salary_rescaled" not in existing:
            # One-time real-dollar cap rescale (Brian's ask, 2026-09-19) --
            # see app/engine/contracts.py's SALARY_CAP_2026 comment for the
            # full why. Guarded by column existence, same idempotency
            # pattern as guaranteed_money above: this whole block (the
            # ALTER + the data UPDATE) can only ever run once per DB file,
            # ever, because the column it adds is what the guard checks
            # for -- a second app boot against an already-migrated file
            # sees the column already present and skips straight past,
            # so salaries can never be silently halved twice. Deliberately
            # placed AFTER the acquisition_type loop just above: that
            # column must exist before this block's UPDATE can reference
            # it (a DB file old enough to predate acquisition_type entirely
            # would otherwise fail here with "no such column").
            #
            # `legacy_salary_rescaled` is not read anywhere else in the
            # app -- it exists purely as this migration's own historical
            # marker (0 = never touched by this pass, either because the
            # row didn't need it or didn't exist yet; 1 = this row's
            # salary/guaranteed_money WAS scaled down by this pass).
            #
            # Which rows count as "legacy" (still on the old, ~1.25x-
            # inflated scale) vs. "real" (already on the real $301.2M
            # scale expected_market_value()/rookie_scale_aav() target):
            # acquisition_type IS NULL (the original imported roster,
            # never touched by a real transaction) OR acquisition_type =
            # 'Trade'. Trade is included deliberately, NOT treated as
            # already-real: app/engine/trades.py's execute_trade() only
            # ever rewrites team_abbr/acquisition_*, it never rewrites
            # salary -- a traded player's salary is exactly whatever it
            # was pre-trade, so acquisition_type='Trade' says nothing
            # about scale. 'Free Agent'/'Undrafted FA' (free_agency.py's
            # mark_free_agent_acquisition) and 'Draft' (draft.py's
            # rookie-scale contracts) ARE excluded -- both those paths
            # compute salary from the real-scale formulas directly.
            #
            # Known, disclosed gap: a re-signed player (main.py's
            # gm_desk_offer ACCEPT) gets a real-scale salary written but
            # acquisition_type is deliberately left unchanged (it still
            # records the player's ORIGINAL acquisition, by design -- see
            # free_agency.mark_free_agent_acquisition's own docstring).
            # A legacy player who was re-signed before this migration
            # ever ran would still show acquisition_type IS NULL and get
            # rescaled here even though their current salary is already
            # real -- a one-time ~20% haircut on that handful of players,
            # not a repeat/compounding error (this block never runs
            # again for this row). Real production data checked
            # 2026-09-19 shows this population is tiny to begin with (a
            # handful of Free Agent/Trade rows per save, out of ~2000
            # players) and GM Desk re-signs are a deliberate user action
            # on their own roster, so the realistic blast radius is small;
            # flagged here rather than silently assumed away.
            conn.exec_driver_sql(
                "ALTER TABLE player ADD COLUMN legacy_salary_rescaled INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            from app.engine.contracts import LEGACY_SALARY_RESCALE_FACTOR
            conn.exec_driver_sql(
                "UPDATE player SET "
                "salary = CAST(ROUND(salary * ?) AS INTEGER), "
                "guaranteed_money = CAST(ROUND(guaranteed_money * ?) AS INTEGER), "
                "legacy_salary_rescaled = 1 "
                "WHERE acquisition_type IS NULL OR acquisition_type = 'Trade'",
                (LEGACY_SALARY_RESCALE_FACTOR, LEGACY_SALARY_RESCALE_FACTOR),
            )
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


def get_session() -> Session:
    return Session(get_engine())
