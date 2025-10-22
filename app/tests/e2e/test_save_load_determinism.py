from app.db import init_db
from app.main import app
from fastapi.testclient import TestClient

def boot(c: TestClient):
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    c.post("/api/admin/season/init/2025?seed=123")

def test_save_load_replays_identically():
    init_db(drop_all=True)
    c = TestClient(app)
    boot(c)

    # Play first two weeks
    c.post("/api/admin/season/2025/advance")
    c.post("/api/admin/season/2025/advance")

    # Snapshot A
    snapA = c.post("/api/save").json()

    # Drop & load
    init_db(drop_all=True)
    c2 = TestClient(app)
    r = c2.post("/api/load", json=snapA)
    assert r.status_code == 200

    # Snapshot B immediately after load must match table counts & week number
    snapB = c2.post("/api/save").json()
    assert snapB["tables"]["season"][0]["current_week"] == snapA["tables"]["season"][0]["current_week"]
    for key in ("team","game","player","playercontract","depthchart"):
        assert len(snapB["tables"][key]) == len(snapA["tables"][key])

