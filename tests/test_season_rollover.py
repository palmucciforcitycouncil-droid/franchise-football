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
from app.services import (
    season_state, save_service, gameplan_store, history_store,
    power_rank_history, award_race_history, headlines_history,
    team_expectations, draft_store, undrafted_pool, owner_pressure_store,
    draft_class_store, draft_board_store, draft_progress_store,
)
from app.engine.schedule import N_WEEKS

REAL_DB_PATH = db_module.DB_PATH
REAL_HISTORY_PATH = history_store.DEFAULT_PATH
REAL_POWER_RANK_PATH = power_rank_history.DEFAULT_PATH
REAL_AWARD_RACE_PATH = award_race_history.DEFAULT_PATH
REAL_HEADLINES_PATH = headlines_history.DEFAULT_PATH
REAL_TEAM_EXPECTATIONS_PATH = team_expectations.DEFAULT_PATH
REAL_DRAFT_STORE_PATH = draft_store.DEFAULT_PATH
REAL_UNDRAFTED_POOL_PATH = undrafted_pool.DEFAULT_PATH
REAL_OWNER_PRESSURE_PATH = owner_pressure_store.DEFAULT_PATH
REAL_DRAFT_CLASS_PATH = draft_class_store.DEFAULT_PATH
REAL_DRAFT_BOARD_PATH = draft_board_store.DEFAULT_PATH
REAL_DRAFT_PROGRESS_PATH = draft_progress_store.DEFAULT_PATH
TEMP_DB_PATH = Path("data/_test_progression_roster.db")

pytestmark = pytest.mark.skipif(
    not REAL_DB_PATH.exists(), reason="data/franchise_football.db not built -- run scripts/import_players.py"
)


@pytest.fixture(autouse=True)
def _isolated_db_and_saves():
    """Redirects the DB to a throwaway copy and every JSON store this
    file's full-season/rollover helpers touch to throwaway paths, for
    every test in this file, restoring the real paths afterward
    regardless of test outcome -- see module docstring.

    This covers every store simulate_current_week()/simulate_playoff_
    round()/begin_offseason()/finish_offseason() write to: without ALL
    of these redirected (not just save_service/gameplan_store/
    history_store), a full simulated season + rollover here would write
    real weekly headlines/award-race snapshots/power-rank snapshots,
    real draft results, real team expectations, and real undrafted-pool/
    owner-pressure state into the live app's own real data/saves/*.json
    files, keyed by this file's always-season-0 test seasons -- silently
    clobbering a real franchise's own archived season 0, if it has one
    (a real, if inert -- nothing reads another season's own history from
    these stores at runtime -- instance of exactly this was found while
    building this feature's own test coverage)."""
    shutil.copyfile(REAL_DB_PATH, TEMP_DB_PATH)
    db_module.DB_PATH = TEMP_DB_PATH
    db_module._engine = None  # force get_engine() to rebuild against the new path
    save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_rollover_season.json")
    gameplan_store.DEFAULT_PATH = Path("data/saves/_test_rollover_gameplans.json")
    # start_new_season() calls history_store.archive_season() internally --
    # redirect this too, or every test here would archive real simulated
    # seasons into the live app's real data/saves/history.json.
    history_store.DEFAULT_PATH = Path("data/saves/_test_rollover_history.json")
    history_store.DEFAULT_PATH.unlink(missing_ok=True)  # clear any leftover from an interrupted prior run
    power_rank_history.DEFAULT_PATH = Path("data/saves/_test_rollover_power_ranks.json")
    award_race_history.DEFAULT_PATH = Path("data/saves/_test_rollover_award_race.json")
    headlines_history.DEFAULT_PATH = Path("data/saves/_test_rollover_headlines.json")
    team_expectations.DEFAULT_PATH = Path("data/saves/_test_rollover_team_expectations.json")
    team_expectations.clear_cache()  # in-memory cache keyed off the OLD path -- force a reload from the new one
    draft_store.DEFAULT_PATH = Path("data/saves/_test_rollover_draft_history.json")
    undrafted_pool.DEFAULT_PATH = Path("data/saves/_test_rollover_undrafted_pool.json")
    owner_pressure_store.DEFAULT_PATH = Path("data/saves/_test_rollover_owner_pressure.json")
    owner_pressure_store.clear_cache()
    # Brian's ask, 2026-09-13: _build_season() now also generates/
    # persists next season's real draft class every time it runs, and
    # the live pick-by-pick draft engine persists its own in-progress
    # state and the user's personal board -- same isolation reasoning as
    # every store above.
    draft_class_store.DEFAULT_PATH = Path("data/saves/_test_rollover_draft_classes.json")
    draft_board_store.DEFAULT_PATH = Path("data/saves/_test_rollover_draft_board.json")
    draft_progress_store.DEFAULT_PATH = Path("data/saves/_test_rollover_draft_progress.json")
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
        Path("data/saves/_test_rollover_history.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_power_ranks.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_award_race.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_headlines.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_team_expectations.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_draft_history.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_undrafted_pool.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_owner_pressure.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_draft_classes.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_draft_board.json").unlink(missing_ok=True)
        Path("data/saves/_test_rollover_draft_progress.json").unlink(missing_ok=True)
        history_store.DEFAULT_PATH = REAL_HISTORY_PATH
        power_rank_history.DEFAULT_PATH = REAL_POWER_RANK_PATH
        award_race_history.DEFAULT_PATH = REAL_AWARD_RACE_PATH
        headlines_history.DEFAULT_PATH = REAL_HEADLINES_PATH
        draft_store.DEFAULT_PATH = REAL_DRAFT_STORE_PATH
        undrafted_pool.DEFAULT_PATH = REAL_UNDRAFTED_POOL_PATH
        team_expectations.DEFAULT_PATH = REAL_TEAM_EXPECTATIONS_PATH
        team_expectations.clear_cache()
        owner_pressure_store.DEFAULT_PATH = REAL_OWNER_PRESSURE_PATH
        owner_pressure_store.clear_cache()
        draft_class_store.DEFAULT_PATH = REAL_DRAFT_CLASS_PATH
        draft_board_store.DEFAULT_PATH = REAL_DRAFT_BOARD_PATH
        draft_progress_store.DEFAULT_PATH = REAL_DRAFT_PROGRESS_PATH


def _play_full_season_and_playoffs(user_team_abbr: str | None = None):
    season_state.reset_season()
    if user_team_abbr:
        season_state.set_user_team(user_team_abbr)
    # Real play order (Brian's ask, 2026-09-13): preseason before Week 1 --
    # cleared here too so a season this helper produces looks like one a
    # real Sim Week walkthrough would reach, not one that skipped straight
    # to the regular season.
    season_state.simulate_preseason()
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


def test_a_fresh_franchise_bootstraps_season_number_after_whatever_is_already_archived():
    """A brand-new franchise's first season should continue chronologically
    AFTER whatever's already permanently archived in history_store.py --
    real-NFL-seeded seasons (scripts/import_nfl_history.py) or a previous
    franchise's own simulated seasons -- rather than always restarting at
    0. See season_state._bootstrap_season_number()'s own docstring."""
    from app.services.history_store import SeasonRecord, TeamSeasonResult, _record_to_dict, _save
    from app.engine.awards import AwardsRace

    fake_real_seasons = [
        _record_to_dict(SeasonRecord(
            season_number=i, team_results=[], champion_abbr=None, afc_seeds=None, nfc_seeds=None,
            awards=AwardsRace(mvp=[], opoy=[], dpoy=[], roy=[]),
            passing_leaders=[], rushing_leaders=[], receiving_leaders=[], defensive_leaders=[],
        ))
        for i in range(5)
    ]
    _save(fake_real_seasons, history_store.DEFAULT_PATH)

    season = season_state.reset_season()
    assert season.season_number == 5


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

    # Brian's ask (2026-09-13): apply_progression_to_roster() no longer
    # releases expired contracts or emergency-fills roster gaps itself --
    # that moved to finish_offseason(), AFTER the real offseason
    # re-signing window (see that function's own docstring). So calling
    # ONLY apply_progression_to_roster() never changes who's rostered --
    # `after.keys()` is exactly `before.keys()`.
    assert before.keys() == after.keys()
    still_rostered = before.keys()
    assert still_rostered  # sanity: this is a real, non-empty roster
    # Every player still rostered ages by exactly 1.
    assert all(after[pid][0] == before[pid][0] + 1 for pid in still_rostered)
    # At least some players' overall_rating actually changed (not every
    # single one has to, given noise + peak-window stability, but a
    # uniform no-op across ~2000 players would mean the write silently
    # failed).
    changed = sum(1 for pid in still_rostered if after[pid][1] != before[pid][1])
    assert changed > 0


def test_apply_progression_to_roster_skips_free_agents():
    """Players who were ALREADY free agents before this rollover get no
    PROGRESSION MATH applied to them (no snap this season to progress
    against), and apply_progression_to_roster() alone never signs anyone
    onto a team either (that's finish_offseason()'s job now, AFTER the
    re-signing window -- see this module's test_finish_offseason_*
    tests for that behavior) -- so every pre-existing free agent is
    still a free agent, at the exact same age, after this call."""
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

    assert fa_before.keys() == fa_after.keys()
    assert all(fa_after[pid] == age for pid, age in fa_before.items())


def test_begin_offseason_pauses_at_staff_then_resign_then_draft_then_finish_completes_it():
    """The offseason's staged split (Brian's ask, 2026-09-13):
    begin_offseason() settles coach signing + player aging and then
    PAUSES at "staff"; advance_offseason_stage() moves it to "resign";
    finish_offseason() resolves free agency and opens the live draft
    ("draft" stage); advance_draft_pick(), driven to the end, is what
    actually completes it (complete_draft_and_advance_season(), called
    automatically once the last slot resolves)."""
    _play_full_season_and_playoffs()
    old_season = season_state.get_season()
    assert old_season.season_number == 0

    with pytest.raises(ValueError):
        season_state.finish_offseason()  # can't finish an offseason that hasn't begun
    with pytest.raises(ValueError):
        season_state.advance_offseason_stage()  # can't advance one that hasn't begun either

    paused = season_state.begin_offseason()
    assert paused.offseason_stage == "staff"
    assert paused.season_number == 0  # still the just-finished season -- no new Season yet
    assert paused is season_state.get_season()

    # Idempotent: calling it again mid-pause changes nothing and doesn't error.
    again = season_state.begin_offseason()
    assert again is paused

    with pytest.raises(ValueError):
        season_state.finish_offseason()  # not at "resign" yet

    resigning = season_state.advance_offseason_stage()
    assert resigning.offseason_stage == "resign"

    with pytest.raises(ValueError):
        season_state.advance_offseason_stage()  # already past "staff"

    drafting = season_state.finish_offseason()
    assert drafting.offseason_stage == "draft"
    assert drafting.season_number == 0  # still the just-finished season -- the live draft hasn't resolved yet

    with pytest.raises(ValueError):
        season_state.complete_draft_and_advance_season()  # not fully resolved yet

    while season_state.current_draft_slot() is not None:
        season_state.advance_draft_pick()

    new_season = season_state.get_season()
    assert new_season.season_number == 1
    assert new_season.offseason_stage is None
    assert new_season.playoffs is None
    assert all(r.wins == 0 and r.losses == 0 for r in new_season.records.values())


def test_start_new_season_route_dispatches_correctly():
    """/season/simulate-week now dispatches all the way from Super Bowl
    into the offseason automatically, landing on /staff (Staff
    Decisions), then /gm-desk (Free Agent Decisions), then /draft (the
    live draft) as each stage opens; POST /offseason/advance-to-resign
    and /offseason/continue move between them, and the Draft page's own
    End control finishes it (replacing the old, separate
    /season/new-season button)."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    season_state.reset_season()

    resp = client.post("/offseason/advance-to-resign")
    assert resp.status_code == 404  # no offseason in progress yet
    resp = client.post("/offseason/continue")
    assert resp.status_code == 404

    _play_full_season_and_playoffs()
    assert season_state.get_season().playoffs.is_complete

    # First post-Super-Bowl Sim Week click begins the offseason and lands on /staff.
    resp = client.post("/season/simulate-week", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/staff"
    assert season_state.get_season().offseason_stage == "staff"

    # A second click while at "staff" is just a no-op reminder, still /staff.
    resp = client.post("/season/simulate-week", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/staff"
    assert season_state.get_season().season_number == 0  # still hasn't advanced

    resp = client.post("/offseason/advance-to-resign", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/gm-desk"
    assert season_state.get_season().offseason_stage == "resign"

    # Sim Week now lands on /gm-desk instead, while at "resign".
    resp = client.post("/season/simulate-week", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/gm-desk"

    resp = client.post("/offseason/continue", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/draft"
    assert season_state.get_season().offseason_stage == "draft"

    # Sim Week now lands on /draft instead, while the live draft is open.
    resp = client.post("/season/simulate-week", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/draft"

    resp = client.post("/draft/end", follow_redirects=False)
    assert resp.status_code == 303
    # Brian's ask, 2026-09-13: End (or any control that resolves the
    # draft's real last slot) now lands on the Offseason Recap, not the
    # Draft page's own "just completed" banner.
    assert resp.headers["location"] == "/offseason/recap"
    assert season_state.get_season().season_number == 1
    assert season_state.get_season().offseason_stage is None
