"""
Tests for season rollover (GDD Sec 4's Offseason step + Sec 7.6 Player
Progression & Regression), app/services/season_state.py's
apply_progression_to_roster()/start_new_season().

These tests actually WRITE to the roster DB (ages/develops real
players) -- something no other test in this codebase does. To never
touch the live app's real data/franchise_football.db, every test here
copies it to a throwaway file first and redirects app.core.db.DB_PATH
to that copy (app.core.db.get_engine() was extended to support this,
same convention as save_service.DEFAULT_SAVE_PATH), restoring the real
path afterward no matter what.
"""
import os
import shutil
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.core import db as db_module
from app.services import season_state, save_service, gameplan_store
from app.engine.schedule import N_WEEKS

REAL_DB_PATH = db_module.DB_PATH
TEMP_DB_PATH = Path("data/_test_progression_roster.db")

pytestmark = pytest.mark.skipif(
    not REAL_DB_PATH.exists(), reason="data/franchise_football.db not built -- run scripts/import_players.py"
)


@pytest.fixture(autouse=True)
def _isolated_db_and_saves():
    """Redirects the DB to a throwaway copy and season/gameplan saves to
    throwaway paths for every test in this file, restoring the real
    DB_PATH afterward regardless of test outcome -- see module docstring."""
    shutil.copyfile(REAL_DB_PATH, TEMP_DB_PATH)
    db_module.DB_PATH = TEMP_DB_PATH
    db_module._engine = None  # force get_engine() to rebuild against the new path
    save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_rollover_season.json")
    gameplan_store.DEFAULT_PATH = Path("data/saves/_test_rollover_gameplans.json")
    try:
        yield
    finally:
        if db_module._engine is not None:
            db_module._engine.dispose()  # release the SQLite file handle -- Windows can't unlink an open file
        db_module.DB_PATH = REAL_DB_PATH
        db_module._engine = None  # force get_engine() to rebuild against the REAL path again
        TEMP_DB_PATH.unlink(missing_ok=True)
        Path("data/saves/_test_rollover_season.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_gameplans.json").unlink(missing_ok=True)


def _play_full_season_and_playoffs(user_team_abbr: str | None = None):
    season_state.reset_season()
    if user_team_abbr:
        season_state.set_user_team(user_team_abbr)
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    for _ in range(4):
        season_state.simulate_playoff_round()


def test_start_new_season_raises_before_playoffs_are_decided():
    season_state.reset_season()
    with pytest.raises(ValueError):
        season_state.start_new_season()

    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season_state.simulate_playoff_round()  # Wild Card only -- playoffs exist but aren't finished
    with pytest.raises(ValueError):
        season_state.start_new_season()


def test_start_new_season_increments_season_number_and_resets_per_season_state():
    _play_full_season_and_playoffs()
    old_season = season_state.get_season()
    assert old_season.season_number == 0
    assert old_season.playoffs.is_complete

    new_season = season_state.start_new_season()
    assert new_season.season_number == 1
    assert new_season.current_week == 1
    assert new_season.playoffs is None
    assert all(r.wins == 0 and r.losses == 0 for r in new_season.records.values())
    assert len(new_season.schedule) == N_WEEKS


def test_start_new_season_preserves_user_team_and_sfs_state():
    _play_full_season_and_playoffs(user_team_abbr="KC")
    old_sfs = season_state.get_season().sfs

    new_season = season_state.start_new_season()
    assert new_season.user_team_abbr == "KC"
    assert new_season.sfs is old_sfs or new_season.sfs.scoring_feedback_multiplier == old_sfs.scoring_feedback_multiplier


def test_start_new_season_uses_real_prior_standings_not_the_bootstrap_order():
    """The new schedule's standings-based games should reflect the real
    just-finished season's division rankings, not schedule.py's
    season-0-only bootstrap (teams.py's listed order) -- confirmed
    indirectly: final_division_standings for season 0 should already
    differ from the bootstrap order in at least one division, since a
    full simulated season essentially never ends in the exact original
    listed order."""
    from app.engine import playoffs as playoffs_module
    from app.engine.schedule import _bootstrap_prior_standings

    _play_full_season_and_playoffs()
    season = season_state.get_season()
    real_standings = playoffs_module.final_division_standings(season)
    bootstrap = _bootstrap_prior_standings()
    assert real_standings != bootstrap


def test_apply_progression_to_roster_actually_mutates_the_db():
    """The core claim of item 26: this isn't a no-op or an in-memory-only
    computation -- real Player rows in the (throwaway-copy) DB change."""
    from sqlmodel import select
    from app.models.player import Player
    from app.core.db import get_session

    _play_full_season_and_playoffs()
    season = season_state.get_season()

    with get_session() as s:
        before = {p.player_id: (p.age, p.overall_rating) for p in s.exec(select(Player).where(Player.team_abbr != None)).all()}  # noqa: E711

    season_state.apply_progression_to_roster(season)

    with get_session() as s:
        after = {p.player_id: (p.age, p.overall_rating) for p in s.exec(select(Player).where(Player.team_abbr != None)).all()}  # noqa: E711

    assert before.keys() == after.keys()
    # Every rostered player ages by exactly 1.
    assert all(after[pid][0] == before[pid][0] + 1 for pid in before)
    # At least some players' overall_rating actually changed (not every
    # single one has to, given noise + peak-window stability, but a
    # uniform no-op across ~2000 players would mean the write silently
    # failed).
    changed = sum(1 for pid in before if after[pid][1] != before[pid][1])
    assert changed > 0


def test_apply_progression_to_roster_skips_free_agents():
    from sqlmodel import select
    from app.models.player import Player
    from app.core.db import get_session

    _play_full_season_and_playoffs()
    season = season_state.get_season()

    with get_session() as s:
        fa_before = {p.player_id: p.age for p in s.exec(select(Player).where(Player.team_abbr == None)).all()}  # noqa: E711

    season_state.apply_progression_to_roster(season)

    with get_session() as s:
        fa_after = {p.player_id: p.age for p in s.exec(select(Player).where(Player.team_abbr == None)).all()}  # noqa: E711

    assert fa_before == fa_after  # untouched -- didn't play a snap this season


def test_start_new_season_route_dispatches_correctly():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    season_state.reset_season()

    resp = client.post("/season/new-season")
    assert resp.status_code == 404  # playoffs not even started yet

    _play_full_season_and_playoffs()
    resp = client.post("/season/new-season", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"
    assert season_state.get_season().season_number == 1
