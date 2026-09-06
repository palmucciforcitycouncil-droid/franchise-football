from app.data.session import engine
from sqlmodel import SQLModel
from app.main import app
from fastapi.testclient import TestClient

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)

def test_save_then_load_parity():
    init_db(drop_all=True)
    c = TestClient(app)
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    c.post("/api/admin/season/init/2025?seed=123")
    # play two weeks
    c.post("/api/admin/season/2025/advance")
    c.post("/api/admin/season/2025/advance")
    # save snapshot
    snap = c.post("/api/save").json()
    assert "tables" in snap and "sim_team" in snap["tables"]
    team_count = len(snap["tables"]["sim_team"])
    # drop DB and load snapshot
    init_db(drop_all=True)
    c2 = TestClient(app)
    r = c2.post("/api/load", json=snap); assert r.status_code == 200
    # verify a few invariants restored
    snap2 = c2.post("/api/save").json()
    assert len(snap2["tables"]["sim_team"]) == team_count
    assert len(snap2["tables"]["sim_game"]) == len(snap["tables"]["sim_game"])
    assert snap2["tables"]["season"][0]["current_week"] == snap["tables"]["season"][0]["current_week"]
