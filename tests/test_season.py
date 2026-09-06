import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient

from app.main import app
from app.services import season_state, save_service
from app.engine.schedule import generate_season_schedule, N_WEEKS
from app.data.teams import TEAMS

client = TestClient(app)

# Tests must never touch the live app's real save file (data/saves/current_season.json)
# -- that would clobber whatever a real browser session has in progress. Redirect to a
# throwaway path for the duration of this test module.
save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_season.json")


def setup_function(_):
    # Each test gets a fresh season so they don't interact via shared module state.
    season_state.reset_season()


def test_schedule_shape():
    schedule = generate_season_schedule(2025)
    assert len(schedule) == N_WEEKS
    for week in schedule:
        assert len(week) == 16  # 32 teams / 2
        teams_this_week = [t for pair in week for t in pair]
        assert len(teams_this_week) == len(set(teams_this_week)), "team double-booked in one week"
    # every team plays exactly N_WEEKS games, each against a distinct opponent
    from collections import defaultdict
    opponents = defaultdict(set)
    games_played = defaultdict(int)
    for week in schedule:
        for home, away in week:
            games_played[home] += 1
            games_played[away] += 1
            opponents[home].add(away)
            opponents[away].add(home)
    for t in TEAMS:
        assert games_played[t.abbr] == N_WEEKS
        assert len(opponents[t.abbr]) == N_WEEKS, "team played the same opponent twice"


def test_season_page_loads():
    resp = client.get("/season")
    assert resp.status_code == 200
    assert "Week 1" in resp.text


def test_simulate_week_advances_and_updates_standings():
    resp = client.post("/season/simulate-week", follow_redirects=True)
    assert resp.status_code == 200
    assert "Week 2" in resp.text
    season = season_state.get_season()
    total_wins = sum(r.wins for r in season.records.values())
    total_losses = sum(r.losses for r in season.records.values())
    assert total_wins == 16  # one winner per game, 16 games in week 1
    assert total_wins == total_losses


def test_full_season_completes():
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season = season_state.get_season()
    assert season.is_complete
    total_games = sum(r.wins + r.losses for r in season.records.values())
    assert total_games == len(TEAMS) * N_WEEKS


def test_reset_clears_results():
    season_state.simulate_current_week()
    season_state.reset_season()
    season = season_state.get_season()
    assert season.current_week == 1
    assert all(r.wins == 0 and r.losses == 0 for r in season.records.values())


def test_save_load_round_trip_preserves_results_and_events():
    season_state.simulate_current_week()
    season_state.simulate_current_week()
    original = season_state.get_season()

    save_service.save_season(original)
    reloaded = save_service.load_season()

    assert reloaded.league_seed == original.league_seed
    assert reloaded.current_week == original.current_week
    for abbr in original.records:
        assert reloaded.records[abbr] == original.records[abbr]

    orig_game = original.schedule[0][0]
    reloaded_game = reloaded.schedule[0][0]
    assert reloaded_game.home_abbr == orig_game.home_abbr
    assert reloaded_game.result.home_score == orig_game.result.home_score
    assert reloaded_game.result.away_score == orig_game.result.away_score
    assert len(reloaded_game.result.events) == len(orig_game.result.events)
    assert reloaded_game.result.events[0].desc == orig_game.result.events[0].desc


def test_season_survives_a_simulated_restart():
    """Simulates a server restart: clear the in-memory season, then confirm
    get_season() loads the persisted one instead of silently generating a
    brand new (different) season."""
    season_state.simulate_current_week()
    before = season_state.get_season()
    before_week = before.current_week
    before_standings = [(r.abbr, r.wins, r.losses) for r in before.standings()]

    season_state._season = None  # simulate process restart losing in-memory state

    after = season_state.get_season()
    assert after.current_week == before_week
    after_standings = [(r.abbr, r.wins, r.losses) for r in after.standings()]
    assert after_standings == before_standings
