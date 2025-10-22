from app.data.session import engine
from sqlmodel import SQLModel
from app.main import app
from fastapi.testclient import TestClient
from pathlib import Path

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

def write_csvs(tmpdir: Path):
    (tmpdir/"app/data").mkdir(parents=True, exist_ok=True)
    (tmpdir/"app/data/players.csv").write_text(
        "team_abbr,first,last,pos,ovr,age,potential\n"
        "T01,A,Alpha,QB,78,27,80\n"
        "T01,B,Bravo,WR,85,25,88\n"
        "T01,C,Charlie,OL,82,26,83\n"
        "T02,D,Delta,QB,75,26,79\n", encoding="utf-8"
    )
    (tmpdir/"app/data/coaches.csv").write_text(
        "team_abbr,head_coach,run_bias,aggression,pace\n"
        "T01,Coach One,0.6,0.55,0.6\n"
        "T02,Coach Two,0.45,0.65,0.55\n", encoding="utf-8"
    )

def test_season_init_and_advance(tmp_path, monkeypatch):
    init_db(drop_all=True)
    c = TestClient(app)
    # Seed teams from previous sprint route
    c.post("/api/sim/seed-teams")
    # mock CSVs in repo path
    write_csvs(Path("."))

    # Import CSVs
    r = c.post("/api/admin/import/players"); assert r.json()["ok"]
    r = c.post("/api/admin/import/coaches"); assert r.json()["ok"]

    # init season + schedule
    r = c.post("/api/admin/season/init/2025?seed=123")
    assert r.json()["ok"]

    # Advance one week
    r = c.post("/api/admin/season/2025/advance")
    assert r.json()["ok"]
