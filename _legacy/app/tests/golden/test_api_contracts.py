from app.db import init_db
from app.main import app
from fastapi.testclient import TestClient

def test_api_shapes_exist():
    init_db(drop_all=True)
    c = TestClient(app)
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    c.post("/api/admin/season/init/2025?seed=123")
    r = c.get("/api/stats/team/2025").json()
    assert isinstance(r, list) and {"team_id","points_for","yards"}.issubset(r[0].keys())

