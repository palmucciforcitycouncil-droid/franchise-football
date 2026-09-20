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
        if coach_cols and "reputation_retiered" not in coach_cols:
            # One-time real-dollar reputation re-tiering (Brian's ask,
            # 2026-09-20 playtest: "assistant coaches have 90 OVR ratings
            # while HC have 60... 24 yo assistants with no coaching
            # experience will end up hired as HCs"). Root cause: the
            # ORIGINAL reputation_from_salary() (scripts/import_coaches.py)
            # mapped each role tier's salary percentile onto the SAME
            # shared 40-99 band independently, so the highest-paid
            # assistant landed at the same ~99 reputation as the
            # highest-paid head coach despite an assistant's real $800K
            # salary ceiling being a fraction of a head coach's real $4M
            # floor. Fixed going forward by app/models/coach.py's
            # REPUTATION_TIER_BAND + reputation_from_tier_percentile()
            # (real, tier-specific bands derived from GDD Appendix S.2's
            # 2026 salary ranges) -- this block re-scores every coach
            # ALREADY imported before that fix existed, using the exact
            # same formula, same idempotency pattern as
            # legacy_salary_rescaled above: guarded by this column's own
            # existence, so a second app boot against an already-migrated
            # file sees the column present and skips straight past --
            # reputations can never be silently re-tiered twice.
            #
            # Deliberately NOT a random re-roll (see legacy_salary_rescaled
            # above for the same principle applied to player salaries): a
            # specific real coach's six 0-99 performance ratings
            # (player_dev_offense/defense, discipline, motivation_
            # chemistry, red_zone_offense/defense) are SHIFTED by the same
            # delta their reputation moves by, not redrawn from a fresh
            # RNG -- so a coach who was, say, a strong developer with weak
            # discipline keeps that same relative shape, just correctly
            # leveled for their real tier, instead of becoming an
            # unrecognizable new coach. Clamped to the model's documented
            # 0-99 performance range (app/models/coach.py) after the shift.
            #
            # Scope: only real-seeded coaches (pool_tier IS NULL) are
            # touched -- R3d's Tier 3 candidate pool
            # (scripts/seed_coach_pool.py) already draws reputation from
            # its OWN real, already-tiered per-role bands independent of
            # salary_aav (which is 0 for every pool candidate; including
            # them here would corrupt the real coaches' own percentile
            # population with a cluster of zeros). Every real-seeded
            # coach is touched regardless of current team_abbr (a
            # since-fired coach who's now a free agent still carries their
            # real last salary_aav, the same real anchor a currently
            # employed peer has -- excluding them would leave stale,
            # mis-tiered ratings on exactly the free-agent pool a fired
            # HC's replacement search draws from).
            conn.exec_driver_sql(
                "ALTER TABLE coach ADD COLUMN reputation_retiered INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            from app.models.coach import CoachRole, tier_key, reputation_from_tier_percentile

            rows = conn.exec_driver_sql(
                "SELECT coach_id, role, salary_aav, reputation, player_dev_offense, "
                "player_dev_defense, discipline, motivation_chemistry, red_zone_offense, "
                "red_zone_defense FROM coach WHERE pool_tier IS NULL"
            ).fetchall()

            tier_salaries: dict[str, list[int]] = {}
            for row in rows:
                tier = tier_key(CoachRole(row[1]))
                tier_salaries.setdefault(tier, []).append(row[2])

            # perf order matches the SELECT above: player_dev_offense,
            # player_dev_defense, discipline, motivation_chemistry,
            # red_zone_offense, red_zone_defense.
            for coach_id, role, salary, old_reputation, *perf in rows:
                tier = tier_key(CoachRole(role))
                salaries = tier_salaries[tier]
                pct = sum(1 for s in salaries if s <= salary) / len(salaries)
                new_reputation = reputation_from_tier_percentile(pct, tier)
                delta = new_reputation - old_reputation
                new_perf = [max(0, min(99, v + delta)) for v in perf]
                conn.exec_driver_sql(
                    "UPDATE coach SET reputation = ?, "
                    "player_dev_offense = ?, player_dev_defense = ?, discipline = ?, "
                    "motivation_chemistry = ?, red_zone_offense = ?, red_zone_defense = ?, "
                    "reputation_retiered = 1 WHERE coach_id = ?",
                    (new_reputation, *new_perf, coach_id),
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


def get_session() -> Session:
    return Session(get_engine())
