from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

def test_standings():
    r = c.get("/api/v1/standings?conf=afc&div=east")
    j = r.json()
    assert "rows" in j and isinstance(j["rows"], list)

def test_power_rankings():
    r = c.get("/api/v1/power_rankings")
    j = r.json()
    assert "rows" in j and len(j["rows"]) == 32

def test_schedule():
    r = c.get("/api/v1/teams/NE/schedule?season=2025")
    j = r.json()
    assert j.get("team_id") == "NE" and "games" in j

def test_scouting():
    r = c.get("/api/v1/scouting/next?team_id=NE")
    j = r.json()
    assert "tendencies" in j and "leaders" in j

def test_boxscore():
    r = c.get("/api/v1/boxscore/2025-W01-NE-BUF")
    j = r.json()
    assert "quarters" in j and "totals" in j
