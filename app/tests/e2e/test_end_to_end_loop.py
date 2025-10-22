from app.db import init_db
from app.main import app
from fastapi.testclient import TestClient

def test_full_loop_and_invariants():
    init_db(drop_all=True)
    c = TestClient(app)

    # 1) Seed league & rosters (fake)
    assert c.post("/api/sim/seed-teams").status_code == 200
    assert c.post("/api/roster/seed").status_code == 200

    # 2) Init season + schedule
    r = c.post("/api/admin/season/init/2025?seed=123")
    assert r.status_code == 200 and r.json()["ok"]

    # 3) Play full regular season (16 weeks per MVP)
    for _ in range(16):
        r = c.post("/api/admin/season/2025/advance")
        assert r.status_code == 200 and r.json()["ok"]

    # 4) Build + run playoffs → SB
    assert c.post("/api/playoffs/build/2025").json()["ok"]
    assert c.post("/api/playoffs/run/2025?seed=999").json()["ok"]

    # 5) Read bracket DTO and check expected rounds present
    dto = c.get("/api/playoffs/bracket/2025").json()
    rnames = [r["round_name"] for r in dto["rounds"]]
    for name in ("WC","DIV","CONF","SB"):
        assert name in rnames

    # 6) Offseason run + advance to next preseason
    assert c.post("/api/offseason/run/2025?seed=777").json()["ok"]
    assert c.post("/api/offseason/advance-to-preseason/2026?seed=2026").json()["ok"]

    # 7) Health ping
    h = c.get("/api/health").json()
    assert h["ok"] and h["db_ok"] and h["teams"] >= 1

