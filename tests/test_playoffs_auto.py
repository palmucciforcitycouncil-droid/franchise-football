from app.data.session import engine
from sqlmodel import SQLModel
from app.main import app
from fastapi.testclient import TestClient

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)

def boot(client: TestClient):
    client.post("/api/sim/seed-teams")
    client.post("/api/admin/season/init/2025?seed=123")
    # Play all 16 weeks to generate final standings
    for _ in range(16):
        client.post("/api/admin/season/2025/advance")

def test_build_and_run_playoffs():
    init_db(drop_all=True)
    c = TestClient(app)
    boot(c)

    r = c.post("/api/playoffs/build/2025"); assert r.json()["ok"]
    r = c.get("/api/playoffs/bracket/2025"); data = r.json()
    assert "rounds" in data and any(r["round_name"]=="WC" for r in data["rounds"])

    r = c.post("/api/playoffs/run/2025?seed=999")
    assert r.json()["ok"]

    data = c.get("/api/playoffs/bracket/2025").json()
    # Should have SB matchup after run
    sb_rounds = [r for r in data["rounds"] if r["round_name"]=="SB"]
    assert sb_rounds and len(sb_rounds[0]["matchups"]) >= 1
