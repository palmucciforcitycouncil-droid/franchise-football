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
        # One-time coach reputation re-tiering (GDD Appendix U.2, Brian's
        # 2026-09-20 playtest fix: "assistant coaches have 90 OVR ratings
        # while HC have 60"). `reputation_from_tier_percentile()`
        # (app/models/coach.py) fixed GENERATION going forward, but never
        # retroactively touched a coach already sitting in the DB with
        # the old shared-band reputation -- this block is that retroactive
        # pass, described in Appendix U.2 but never actually landed in
        # this file (dropped, in error, as "redundant" during the R16
        # merge -- confirmed live 2026-09-20: real HC reputations still
        # ranged 53-99, well below the documented 84-99 floor). Column-
        # existence guard, same idempotency pattern as
        # legacy_salary_rescaled above -- can only ever run once per DB
        # file. Deliberately excludes pool_tier candidates (R3d's Tier
        # 2/3 pool, `pool_tier IS NOT NULL`), which already draw from
        # their own independent bands (scripts/seed_coach_pool.py) and
        # were never subject to the old shared-band bug.
        if coach_cols and "reputation_retiered" not in coach_cols:
            conn.exec_driver_sql("ALTER TABLE coach ADD COLUMN reputation_retiered INTEGER NOT NULL DEFAULT 0")
            conn.commit()
            from app.models.coach import CoachRole, tier_key, reputation_from_tier_percentile
            rows = conn.exec_driver_sql(
                "SELECT coach_id, role, salary_aav, reputation, discipline, motivation_chemistry, "
                "red_zone_offense, red_zone_defense FROM coach WHERE pool_tier IS NULL"
            ).fetchall()
            tier_salaries: dict[str, list[int]] = {}
            for _cid, role, salary, *_rest in rows:
                tier_salaries.setdefault(tier_key(CoachRole(role)), []).append(salary)
            for coach_id, role, salary, reputation, discipline, motivation, rzo, rzd in rows:
                tier = tier_key(CoachRole(role))
                salaries = tier_salaries[tier]
                pct = sum(1 for s in salaries if s <= salary) / len(salaries)
                new_reputation = reputation_from_tier_percentile(pct, tier)
                delta = new_reputation - reputation
                conn.exec_driver_sql(
                    "UPDATE coach SET reputation = ?, discipline = ?, motivation_chemistry = ?, "
                    "red_zone_offense = ?, red_zone_defense = ?, reputation_retiered = 1 WHERE coach_id = ?",
                    (new_reputation,
                     max(0, min(99, discipline + delta)), max(0, min(99, motivation + delta)),
                     max(0, min(99, rzo + delta)), max(0, min(99, rzd + delta)),
                     coach_id),
                )
            conn.commit()
        # One-time backfill of the 8 granular position-group coaching
        # ratings (R16, docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md
        # Sec 1) for every coach that predates _COACH_COLUMNS_ADDED_
        # 2026_09_15 above -- that ALTER TABLE gives every existing row
        # the plain schema default of 50 with no backfill, which silently
        # makes app/engine/coaching.py's whole Focus Area this-game-boost
        # system a complete no-op for any coach imported before these
        # columns existed (confirmed live 2026-09-20: every coach in a
        # fresh checkout sat at exactly 50 on all 8). A coach with all 8
        # still exactly 50 is the idempotency signal -- a real gaussian
        # draw landing on that exact integer 8 times in a row is
        # vanishingly unlikely, so no separate marker column is needed,
        # and this naturally becomes a no-op once a coach has been
        # touched (by this block, by a fresh import, or by R3d's pool
        # seeding). Runs AFTER the reputation re-tiering block above so
        # it centers on the CORRECTED reputation, not the old one.
        # Reuses the real generation formula's shape (reputation-
        # anchored draw, off-specialty/off-side penalty) from
        # scripts/import_coaches.py's _rating_penalty_for()/_draw()
        # rather than inventing new logic, under this migration's own
        # seed namespace -- a disclosed, reasonable simplification, not a
        # byte-for-byte replay of each coach's original import-time RNG
        # sequence (which would also need that coach's now-unstored
        # intermediate draws to reproduce exactly).
        if coach_cols:
            stale_rows = conn.exec_driver_sql(
                "SELECT coach_id, role, specialty, reputation FROM coach WHERE "
                "qb_coaching = 50 AND rb_coaching = 50 AND wr_coaching = 50 AND ol_coaching = 50 "
                "AND dl_coaching = 50 AND lb_coaching = 50 AND secondary_coaching = 50 AND st_coaching = 50"
            ).fetchall()
            if stale_rows:
                from app.engine.rng import RNG, stable_seed
                from app.models.coach import CoachRole
                from app.config import get_league_seed
                from scripts.import_coaches import _rating_penalty_for, _ALL_GROUP_RATINGS, _draw
                league_seed = get_league_seed()
                for coach_id, role, specialty, reputation in stale_rows:
                    rng = RNG.with_seed(stable_seed("coach_group_ratings_backfill", league_seed, coach_id))
                    penalty = _rating_penalty_for(CoachRole(role), specialty)
                    values = [_draw(rng, reputation - penalty.get(attr, 0.0), 8, 20, 99) for attr in _ALL_GROUP_RATINGS]
                    conn.exec_driver_sql(
                        "UPDATE coach SET qb_coaching=?, rb_coaching=?, wr_coaching=?, ol_coaching=?, "
                        "dl_coaching=?, lb_coaching=?, secondary_coaching=?, st_coaching=? WHERE coach_id=?",
                        (*values, coach_id),
                    )
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
