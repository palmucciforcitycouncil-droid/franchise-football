"""
Tests for R8 (Awards Page): the weekly Awards Race snapshot store
(app/services/award_race_history.py) and the /awards route + template.
"""
import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient

from app.main import app
from app.services import season_state, save_service, gameplan_store, history_store, power_rank_history, award_race_history
from app.engine import awards

client = TestClient(app)

# Same real-save isolation convention as test_season.py -- these tests
# call season_state.reset_season()/simulate_current_week() directly, so
# none of this may ever touch the live app's real save/store files.
save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_awards_page_season.json")
gameplan_store.DEFAULT_PATH = Path("data/saves/_test_awards_page_gameplans.json")
history_store.DEFAULT_PATH = Path("data/saves/_test_awards_page_history.json")
power_rank_history.DEFAULT_PATH = Path("data/saves/_test_awards_page_power_ranks.json")
award_race_history.DEFAULT_PATH = Path("data/saves/_test_awards_page_award_race.json")


def setup_function(_):
    history_store.DEFAULT_PATH.unlink(missing_ok=True)
    award_race_history.DEFAULT_PATH.unlink(missing_ok=True)
    season_state.reset_season()
    gameplan_store.DEFAULT_PATH.unlink(missing_ok=True)
    power_rank_history.DEFAULT_PATH.unlink(missing_ok=True)


# --- app/services/award_race_history.py store -------------------------------

def test_get_week_awards_returns_none_for_an_unrecorded_week(tmp_path):
    path = tmp_path / "award_race.json"
    assert award_race_history.get_week_awards(0, 1, path=path) is None


def test_record_and_get_round_trips_plain_dicts(tmp_path):
    path = tmp_path / "award_race.json"
    snapshot = {"mvp": [{"name": "Test QB", "team_abbr": "KC", "score": 0.9}]}
    award_race_history.record_week_awards(0, 1, snapshot, path=path)
    assert award_race_history.get_week_awards(0, 1, path=path) == snapshot


def test_record_and_get_round_trips_real_award_dataclasses(tmp_path):
    """The real call site (season_state.py) hands this raw AwardCandidate/
    CoachAwardCandidate/ProBowlStarter dataclass instances, not
    pre-converted dicts -- confirms _to_plain's recursive dataclass ->
    dict conversion actually round-trips through real JSON, not just
    plain-dict input."""
    path = tmp_path / "award_race.json"
    candidate = awards.AwardCandidate(name="Test WR", team_abbr="BUF", position="WR/TE", stat_line="100 yds", score=0.75)
    coach_candidate = awards.CoachAwardCandidate(
        coach_id="c1", name="Test Coach", team_abbr="BUF", record="10-0",
        stat_line="10-0", score=0.5,
    )
    snapshot = {
        "mvp": [candidate],
        "coty": [coach_candidate],
        "pro_bowl": {"AFC": {"offense": [], "defense": [], "special": []}},
    }
    award_race_history.record_week_awards(2, 3, snapshot, path=path)

    stored = award_race_history.get_week_awards(2, 3, path=path)
    assert stored["mvp"][0]["name"] == "Test WR"
    assert stored["mvp"][0]["score"] == 0.75
    assert stored["coty"][0]["name"] == "Test Coach"
    assert stored["pro_bowl"]["AFC"]["offense"] == []


def test_different_weeks_and_seasons_dont_clobber_each_other(tmp_path):
    path = tmp_path / "award_race.json"
    award_race_history.record_week_awards(0, 1, {"mvp": []}, path=path)
    award_race_history.record_week_awards(0, 2, {"mvp": [{"name": "A"}]}, path=path)
    award_race_history.record_week_awards(1, 1, {"mvp": [{"name": "B"}]}, path=path)

    assert award_race_history.get_week_awards(0, 1, path=path) == {"mvp": []}
    assert award_race_history.get_week_awards(0, 2, path=path) == {"mvp": [{"name": "A"}]}
    assert award_race_history.get_week_awards(1, 1, path=path) == {"mvp": [{"name": "B"}]}


def test_get_all_weeks_returns_every_recorded_week_for_a_season(tmp_path):
    path = tmp_path / "award_race.json"
    award_race_history.record_week_awards(0, 1, {"mvp": []}, path=path)
    award_race_history.record_week_awards(0, 2, {"mvp": []}, path=path)
    award_race_history.record_week_awards(1, 1, {"mvp": []}, path=path)

    all_weeks = award_race_history.get_all_weeks(0, path=path)
    assert set(all_weeks.keys()) == {"1", "2"}


# --- /awards route + season_state wiring ------------------------------------

def test_awards_page_loads_with_empty_arrays_before_any_week_is_simulated():
    resp = client.get("/awards")
    assert resp.status_code == 200
    assert "Awards" in resp.text
    assert "No weeks simulated yet" in resp.text  # Weekly Race Archive tab, empty


def test_simulate_current_week_records_a_real_award_race_snapshot():
    season_state.simulate_current_week()
    season = season_state.get_season()
    snapshot = award_race_history.get_week_awards(season.season_number, 1)
    assert snapshot is not None
    for key in ("mvp", "opoy", "dpoy", "oroy", "droy", "coty", "pro_bowl"):
        assert key in snapshot


def test_awards_page_populates_the_archive_after_a_week_is_simulated():
    season_state.simulate_current_week()
    resp = client.get("/awards?tab=archive")
    assert resp.status_code == 200
    assert "No weeks simulated yet" not in resp.text
    assert 'data-panel="archive"' in resp.text


def test_awards_page_season_tab_shows_all_six_categories():
    season_state.simulate_current_week()
    resp = client.get("/awards")
    assert resp.status_code == 200
    for label in ("MVP", "OPOY", "DPOY", "OROY", "DROY", "Coach of the Year"):
        assert label in resp.text


def test_awards_page_pro_bowl_tab_renders_afc_and_nfc():
    resp = client.get("/awards?tab=pro-bowl")
    assert resp.status_code == 200
    assert 'data-panel="pro-bowl"' in resp.text
    assert "AFC" in resp.text and "NFC" in resp.text


def test_pro_bowl_starters_returns_real_players_split_by_conference():
    season = season_state.get_season()
    afc = awards.pro_bowl_starters(season, "AFC")
    nfc = awards.pro_bowl_starters(season, "NFC")

    assert set(afc.keys()) == {"offense", "defense", "special"}
    afc_teams = {p.team_abbr for side in afc.values() for p in side}
    nfc_teams = {p.team_abbr for side in nfc.values() for p in side}
    assert afc_teams, "expected at least one real AFC Pro Bowl starter"
    assert nfc_teams, "expected at least one real NFC Pro Bowl starter"
    assert afc_teams.isdisjoint(nfc_teams)

    from app.data.teams import TEAMS_BY_ABBR
    assert all(TEAMS_BY_ABBR[abbr].conference == "AFC" for abbr in afc_teams)
    assert all(TEAMS_BY_ABBR[abbr].conference == "NFC" for abbr in nfc_teams)


def test_offensive_and_defensive_rookie_of_the_year_split_roy():
    """OROY/DROY are ROY's own offensive/defensive halves, not a new
    formula -- every ROY candidate must appear in exactly one of them."""
    season_state.simulate_current_week()
    season = season_state.get_season()

    roy = {c.name for c in awards.rookie_of_the_year(season, top_n=1000)}
    oroy = {c.name for c in awards.offensive_rookie_of_the_year(season, top_n=1000)}
    droy = {c.name for c in awards.defensive_rookie_of_the_year(season, top_n=1000)}

    assert oroy.isdisjoint(droy)
    assert roy <= (oroy | droy)  # every ROY name traces back to one of the two halves
