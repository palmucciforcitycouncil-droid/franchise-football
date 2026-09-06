"""
Smoke test for the vertical slice: pick two teams, simulate one game,
end to end through the real running app (not just the engine in isolation).

This exists because the engine audit found real, plausible-looking code
throughout the old app tree that had never actually been executed --
imports that didn't resolve, parameters that didn't exist, signature
mismatches masked by tests that only exercised fallback paths. The bug
this project fixed today (drive_sim.py referencing tuning parameters
that didn't exist in tuning.py) was exactly that pattern. This test's
only job is to make sure that mistake can't happen silently here.
"""
import os

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient

from app.main import app
from app.data.teams import TEAMS

client = TestClient(app)


def test_index_lists_all_32_teams():
    resp = client.get("/")
    assert resp.status_code == 200
    for team in TEAMS:
        assert team.location in resp.text


def test_simulate_one_game_end_to_end():
    resp = client.post("/simulate", data={"home_abbr": "BUF", "away_abbr": "MIA"})
    assert resp.status_code == 200
    assert "Buffalo" in resp.text
    assert "Miami" in resp.text
    assert "Team Totals" in resp.text
    assert "Drive-by-Drive" in resp.text


def test_simulation_is_deterministic():
    resp1 = client.post("/simulate", data={"home_abbr": "BUF", "away_abbr": "MIA"})
    resp2 = client.post("/simulate", data={"home_abbr": "BUF", "away_abbr": "MIA"})
    assert resp1.text == resp2.text


def test_different_matchup_gives_different_result():
    resp1 = client.post("/simulate", data={"home_abbr": "BUF", "away_abbr": "MIA"})
    resp2 = client.post("/simulate", data={"home_abbr": "KC", "away_abbr": "SF"})
    assert resp1.text != resp2.text
