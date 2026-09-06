# tests/test_contracts_fa_mvp.py
from sqlmodel import Session, select
from fastapi.testclient import TestClient
from app.api.routes.contracts_fa import router
from fastapi import FastAPI
from app.db import get_engine
from app.models.contracts import Contract
from app.services.draft import generate_draft_class, assign_picks, make_selection
from app.services.draft_integration import finalize_draft_class
from app.services.contracts import expire_contracts, list_free_agents, submit_bid, simulate_free_agency, team_cap_used
from app.models.draft import Prospect, DraftPick
from app.models.core_min import Player

def _rookie_on_roster(season: int = 2027):
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=999)
        assign_picks(s, season)
        pr = s.exec(select(Prospect).where(Prospect.season==season).order_by(Prospect.overall.desc())).first()
        p1 = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        make_selection(s, season, 1, pr.id, p1.team_id)
        finalize_draft_class(s, season, seed=999)
        # return created player + team
        pl = s.exec(select(Player).where(Player.rookie_season==season)).first()
        return getattr(pl,"player_id",getattr(pl,"id")), getattr(pl,"team_id")

def test_expire_to_fa_and_bidding_and_simulation():
    """Test contract expiration, free agency, and bidding simulation."""
    eng = get_engine()
    with Session(eng) as s:
        # Create a test player with a contract
        p = Player(name="Test Player", pos="QB", team_id=1, age=25, years_pro=3)
        s.add(p)
        s.commit()
        s.refresh(p)
        pid = p.id
        
        # Create a 1-year contract
        c = Contract(player_id=pid, team_id=1, start_season=2035, years=1, aav=500, status="active")
        s.add(c)
        s.commit()
        
        # Expire contracts into 2036
        stats = expire_contracts(s, season=2036)
        assert stats["expired"] >= 1
        
        # Player should be FA
        p = s.get(Player, pid)
        assert p.team_id is None

        fas = list_free_agents(s, 2036)
        assert any(getattr(x,"player_id",getattr(x,"id")) == pid for x in fas)

        # Two teams bid; team 2 should win on higher AAV
        submit_bid(s, 2036, 1, pid, aav=120, years=2)
        submit_bid(s, 2036, 2, pid, aav=180, years=2)
        res = simulate_free_agency(s, 2036, seed=2025)
        assert res["signings"] >= 1

        p2 = s.get(Player, pid)
        assert p2.team_id == 2
        used = team_cap_used(s, 2, 2036)
        assert used >= 180

def test_api_smoke():
    """Test API endpoints smoke test."""
    # Create a minimal app with just the contracts router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    r1 = client.get("/contracts/2025/team/1")
    assert r1.status_code == 200
    # expire next season
    r2 = client.post("/contracts/2026/expire")
    assert r2.status_code == 200
    # list FA
    r3 = client.get("/free_agency/2026/players")
    assert r3.status_code == 200

def test_contract_end_season_property():
    """Test that contract end_season property works correctly."""
    c = Contract(start_season=2025, years=3)
    assert c.end_season == 2027  # 2025 + 3 - 1
    
    c2 = Contract(start_season=2025, years=1)
    assert c2.end_season == 2025  # 2025 + 1 - 1

def test_cap_space_calculation():
    """Test cap space calculations."""
    eng = get_engine()
    with Session(eng) as s:
        # Create a test player and contract
        p = Player(name="Test Player", pos="QB", team_id=1, age=25, years_pro=3)
        s.add(p)
        s.commit()
        s.refresh(p)
        
        # Create a contract
        c = Contract(player_id=p.id, team_id=1, start_season=2025, years=2, aav=500, status="active")
        s.add(c)
        s.commit()
        
        from app.services.contracts import team_cap_used, team_cap_space
        
        # Test cap calculations
        used = team_cap_used(s, 1, 2025)
        assert used == 500
        
        space = team_cap_space(s, 1, 2025)
        assert space == 1500  # 2000 - 500

def test_free_agency_deterministic():
    """Test that free agency simulation is deterministic with same seed."""
    eng = get_engine()
    with Session(eng) as s:
        # Create a test player
        p = Player(name="Test FA Player", pos="QB", team_id=None, age=25, years_pro=3)
        s.add(p)
        s.commit()
        s.refresh(p)
        pid = p.id
        
        # Run simulation twice with same seed
        submit_bid(s, 2040, 1, pid, aav=200, years=2)
        submit_bid(s, 2040, 2, pid, aav=250, years=2)
        
        res1 = simulate_free_agency(s, 2040, seed=1234)
        
        # Reset player to FA and remove contract
        p.team_id = None
        s.add(p)
        # Remove the contract that was created
        from sqlmodel import delete
        s.exec(delete(Contract).where(Contract.player_id == pid, Contract.start_season == 2040))
        s.commit()
        
        res2 = simulate_free_agency(s, 2040, seed=1234)
        
        # Results should be identical
        assert res1["signings"] == res2["signings"]
        assert res1["skipped_no_cap"] == res2["skipped_no_cap"]
        assert res1["skipped_already_signed"] == res2["skipped_already_signed"]
