from app.db import init_db
from app.main import app
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.stats_models import TeamGameStats
from app.models.player_stats_models import PlayerGameStats

def boot(c: TestClient):
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    c.post("/api/admin/season/init/2025?seed=123")

def test_player_logs_sum_to_team():
    init_db(drop_all=True)
    c = TestClient(app)
    boot(c)
    c.post("/api/admin/season/2025/advance")
    # pick a game id from week 1
    gid = c.get("/api/sim/games/2025/1").json()[0]["id"]
    # pull team rows
    tg = c.get(f"/api/stats/game/{gid}").json()["teams"]
    assert len(tg)==2
    # pull players
    pl = c.get(f"/api/stats/players/game/{gid}").json()
    # check sums per side
    for t in tg:
        side = [x for x in pl if x["team_id"]==t["team_id"]]
        # passing & rushing yards within small rounding error
        pass_sum = sum(x["pass_yds"] for x in side)
        rush_sum = sum(x["rush_yds"] for x in side)
        assert abs(pass_sum - t["pass_yards"]) <= 5
        assert abs(rush_sum - t["rush_yards"]) <= 5

def test_leaders_exist():
    init_db(drop_all=True)
    c = TestClient(app)
    boot(c)
    # play two weeks for some sample
    c.post("/api/admin/season/2025/advance")
    c.post("/api/admin/season/2025/advance")
    leaders = c.get("/api/stats/leaders/2025").json()
    assert "pass_yds" in leaders and isinstance(leaders["pass_yds"], list)

