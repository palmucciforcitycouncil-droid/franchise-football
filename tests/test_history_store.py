"""
Tests for League History (app/services/history_store.py). Most tests
build a small synthetic Season by hand (real dataclasses, no DB needed
for archive_season() itself -- aggregate_season_stats/season_awards
only touch the DB when there's a real rookie/box-score lookup to make,
which an empty schedule never triggers).
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.services.season_state import Season, WeekGame, TeamRecord
from app.engine.game_state import GameResult
from app.engine.playoffs import PlayoffBracket, PlayoffMatchup
from app.data.teams import TEAMS
from app.services import history_store


def _season(schedule=None, season_number=0, playoffs=None):
    records = {t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS}
    return Season(league_seed=1, schedule=schedule or [], records=records,
                  season_number=season_number, playoffs=playoffs)


def test_archive_season_round_trips_through_json(tmp_path):
    path = tmp_path / "history.json"
    season = _season(season_number=0)
    season.records["KC"].wins = 12
    season.records["KC"].losses = 5

    archived = history_store.archive_season(season, path=path)
    assert archived.season_number == 0

    history = history_store.get_history(path=path)
    assert len(history) == 1
    assert history[0].season_number == 0
    kc = next(t for t in history[0].team_results if t.abbr == "KC")
    assert kc.wins == 12
    assert kc.losses == 5


def test_archive_season_captures_champion_and_seeds_when_playoffs_exist():
    def _run(tmp_path):
        path = tmp_path / "history.json"
        sb = PlayoffMatchup(
            round_name="SB", conference=None, home_abbr="KC", away_abbr="PHI",
            home_seed=1, away_seed=2,
            result=GameResult(home_score=30, away_score=20, winner="home", events=[], plays=[]),
        )
        bracket = PlayoffBracket(afc_seeds=["KC"] + ["BUF"] * 6, nfc_seeds=["PHI"] + ["DAL"] * 6, rounds=[[sb]])
        season = _season(season_number=2, playoffs=bracket)

        record = history_store.archive_season(season, path=path)
        assert record.champion_abbr == "KC"
        assert record.afc_seeds[0] == "KC"
        assert record.nfc_seeds[0] == "PHI"

    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        _run(Path(d))


def test_archive_season_without_playoffs_has_no_champion():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "history.json"
        season = _season(season_number=0, playoffs=None)
        record = history_store.archive_season(season, path=path)
        assert record.champion_abbr is None
        assert record.afc_seeds is None


def test_get_history_is_empty_when_nothing_archived_yet(tmp_path):
    path = tmp_path / "history.json"
    assert history_store.get_history(path=path) == []


def test_multiple_seasons_archive_in_order(tmp_path):
    path = tmp_path / "history.json"
    history_store.archive_season(_season(season_number=0), path=path)
    history_store.archive_season(_season(season_number=1), path=path)
    history_store.archive_season(_season(season_number=2), path=path)

    history = history_store.get_history(path=path)
    assert [r.season_number for r in history] == [0, 1, 2]


# --- DB-backed integration: real end-to-end archival via a full rollover ---

from app.core.db import DB_PATH

DB_EXISTS = DB_PATH.exists()


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_start_new_season_archives_the_completed_season_for_real():
    """Integration test through the real season_state.start_new_season()
    -- uses the SAME DB-isolation pattern as test_season_rollover.py so
    it never touches the live roster DB."""
    import shutil
    from pathlib import Path
    from app.core import db as db_module
    from app.services import season_state, save_service, gameplan_store
    from app.engine.schedule import N_WEEKS

    real_db_path = db_module.DB_PATH
    real_history_path = history_store.DEFAULT_PATH
    temp_db_path = Path("data/_test_history_roster.db")
    shutil.copyfile(real_db_path, temp_db_path)
    db_module.DB_PATH = temp_db_path
    db_module._engine = None
    save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_history_season.json")
    gameplan_store.DEFAULT_PATH = Path("data/saves/_test_history_gameplans.json")
    history_store.DEFAULT_PATH = Path("data/saves/_test_history.json")
    history_store.DEFAULT_PATH.unlink(missing_ok=True)  # clear any leftover from an interrupted prior run

    try:
        season_state.reset_season()
        for _ in range(N_WEEKS):
            season_state.simulate_current_week()
        for _ in range(4):
            season_state.simulate_playoff_round()

        completed = season_state.get_season()
        assert completed.playoffs.is_complete

        season_state.start_new_season()

        history = history_store.get_history()
        assert len(history) == 1
        assert history[0].season_number == 0
        assert history[0].champion_abbr == completed.playoffs.champion_abbr
        assert len(history[0].passing_leaders) > 0
    finally:
        if db_module._engine is not None:
            db_module._engine.dispose()
        db_module.DB_PATH = real_db_path
        db_module._engine = None
        temp_db_path.unlink(missing_ok=True)
        Path("data/saves/_test_history_season.json").unlink(missing_ok=True)
        Path("data/saves/_test_history_gameplans.json").unlink(missing_ok=True)
        Path("data/saves/_test_history.json").unlink(missing_ok=True)
        history_store.DEFAULT_PATH = real_history_path


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_history_route_renders_empty_and_populated_states():
    import shutil
    from pathlib import Path
    from app.core import db as db_module
    from app.services import season_state, save_service, gameplan_store
    from app.engine.schedule import N_WEEKS
    from fastapi.testclient import TestClient
    from app.main import app

    real_db_path = db_module.DB_PATH
    real_history_path = history_store.DEFAULT_PATH
    temp_db_path = Path("data/_test_history_route_roster.db")
    shutil.copyfile(real_db_path, temp_db_path)
    db_module.DB_PATH = temp_db_path
    db_module._engine = None
    save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_history_route_season.json")
    gameplan_store.DEFAULT_PATH = Path("data/saves/_test_history_route_gameplans.json")
    history_store.DEFAULT_PATH = Path("data/saves/_test_history_route.json")
    history_store.DEFAULT_PATH.unlink(missing_ok=True)  # clear any leftover from an interrupted prior run

    try:
        client = TestClient(app)
        season_state.reset_season()

        resp = client.get("/history")
        assert resp.status_code == 200
        assert "No seasons completed yet" in resp.text

        for _ in range(N_WEEKS):
            season_state.simulate_current_week()
        for _ in range(4):
            season_state.simulate_playoff_round()
        season_state.start_new_season()

        resp = client.get("/history")
        assert resp.status_code == 200
        assert "Season 1" in resp.text
    finally:
        if db_module._engine is not None:
            db_module._engine.dispose()
        db_module.DB_PATH = real_db_path
        db_module._engine = None
        temp_db_path.unlink(missing_ok=True)
        Path("data/saves/_test_history_route_season.json").unlink(missing_ok=True)
        Path("data/saves/_test_history_route_gameplans.json").unlink(missing_ok=True)
        Path("data/saves/_test_history_route.json").unlink(missing_ok=True)
        history_store.DEFAULT_PATH = real_history_path
