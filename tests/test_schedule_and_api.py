from fastapi.testclient import TestClient
from app.main import app
from app.data.session import engine
from sqlmodel import SQLModel

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

def test_schedule_and_week():
    # fresh DB
    init_db(drop_all=True)
    client = TestClient(app)
    client.post("/api/sim/seed-teams")
    client.post("/api/sim/schedule/2025?seed=123")
    r = client.post("/api/sim/play-week/2025/1?seed=77")
    assert r.status_code == 200
    assert r.json()["ok"] is True
