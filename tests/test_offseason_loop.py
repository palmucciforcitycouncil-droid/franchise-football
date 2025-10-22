from app.data.session import engine
from sqlmodel import SQLModel
from app.main import app
from fastapi.testclient import TestClient

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)

def boot_full(client: TestClient):
    client.post("/api/sim/seed-teams")
    client.post("/api/roster/seed")
    client.post("/api/admin/season/init/2025?seed=123")
    # play out 16 weeks
    for _ in range(16):
        client.post("/api/admin/season/2025/advance")

def test_offseason_run_and_preseason():
    init_db(drop_all=True)
    c = TestClient(app)
    boot_full(c)
    r = c.post("/api/offseason/run/2025?seed=777")
    assert r.status_code == 200 and r.json()["ok"]
    body = r.json()
    assert body["drafted"] >= 150  # most of 224 drafted
    # start next preseason
    r2 = c.post("/api/offseason/advance-to-preseason/2026?seed=2026")
    assert r2.json()["ok"] and r2.json()["phase"] == "preseason"
