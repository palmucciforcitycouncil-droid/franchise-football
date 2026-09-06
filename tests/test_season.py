import os

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient

from app.main import app
from app.services import season_state
from app.engine.schedule import generate_season_schedule, N_WEEKS
from app.data.teams import TEAMS

client = TestClient(app)


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
