from app.data.session import engine
from sqlmodel import SQLModel
from app.main import app
from fastapi.testclient import TestClient

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)

def setup_sim(client: TestClient):
    client.post("/api/sim/seed-teams")
    client.post("/api/admin/season/init/2025?seed=123")  # creates schedule

def test_box_score_and_team_totals():
    init_db(drop_all=True)
    c = TestClient(app)
    setup_sim(c)
    # play week 1
    c.post("/api/admin/season/2025/advance")
    # get a game id from week 1
    games = c.get("/api/sim/games/2025/1").json()
    assert games
    gid = games[0]["id"]
    # box score
    bs = c.get(f"/api/stats/game/{gid}")
    assert bs.status_code == 200
    body = bs.json()
    assert body["home_score"] is not None and body["away_score"] is not None
    assert len(body["teams"]) == 2
    # season aggregates
    totals = c.get("/api/stats/team/2025").json()
    assert isinstance(totals, list) and len(totals) > 0
    assert "yards" in totals[0]
