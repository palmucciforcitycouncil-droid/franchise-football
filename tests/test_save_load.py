from app.data.session import engine
from sqlmodel import SQLModel
from app.main import app
from fastapi.testclient import TestClient

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)

def test_save_then_load_parity():
    """Test that we can save and load the full league state."""
    init_db(drop_all=True)
    c = TestClient(app)
    
    # Boot up a league
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    c.post("/api/admin/season/init/2025?seed=123")
    
    # Play a few weeks
    for _ in range(4):
        c.post("/api/admin/season/2025/advance")
    
    # Save
    r = c.post("/api/save")
    assert r.status_code == 200
    snapshot = r.json()
    
    # Clear DB
    init_db(drop_all=True)
    
    # Load
    r2 = c.post("/api/load", json=snapshot)
    assert r2.status_code == 200 and r2.json()["ok"]
    
    # Verify we can query teams (using correct endpoint)
    from sqlmodel import Session
    from app.data.session import engine
    from app.models.sim_models import SimTeam
    with Session(engine) as session:
        teams = session.query(SimTeam).all()
        assert len(teams) == 32

