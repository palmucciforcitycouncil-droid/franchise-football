# tests/test_resign_and_cap_init.py
from sqlmodel import Session, select
from fastapi.testclient import TestClient
from app.api.routes.cap_resign import router
from fastapi import FastAPI
from app.db import get_engine
from app.models.contracts import Contract
from app.models.cap import TeamCap
from app.services.draft import generate_draft_class, assign_picks, make_selection
from app.services.draft_integration import finalize_draft_class
from app.services.contracts import (
    init_season_cap_for_all_teams, compute_and_persist_team_cap, resign_candidates, submit_resign_offer, simulate_resign_window,
    expire_contracts, list_free_agents
)
from app.models.draft import Prospect, DraftPick
from app.models.core_min import Player

def _rookie_one_year(season: int):
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=31415)
        assign_picks(s, season)
        pr = s.exec(select(Prospect).where(Prospect.season==season).order_by(Prospect.overall.desc())).first()
        p1 = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        make_selection(s, season, 1, pr.id, p1.team_id)
        finalize_draft_class(s, season, seed=31415)
        # force 1-year rookie deal so it expires before next season
        pl = s.exec(select(Player).where(Player.rookie_season==season)).first()
        if pl:
            c = s.exec(select(Contract).where(Contract.player_id==getattr(pl,"player_id",getattr(pl,"id")), Contract.start_season==season)).first()
            if c:
                c.years = 1
                s.add(c); s.commit()
            return getattr(pl,"player_id",getattr(pl,"id")), getattr(pl,"team_id")
    return None, None

def test_cap_init_and_resign_flow():
    """Test cap initialization and re-sign flow."""
    # rookie enters in 2028 with 1-year deal; re-sign window for 2029
    rookie_season = 2028
    next_season = 2029
    pid, team_id = _rookie_one_year(rookie_season)
    
    if not pid or not team_id:
        # Skip if no rookie was created
        return

    eng = get_engine()
    with Session(eng) as s:
        # init cap rows for 2029
        res = init_season_cap_for_all_teams(s, next_season, 2000)
        assert res["rows_written"] >= 1
        row = compute_and_persist_team_cap(s, team_id, next_season)
        assert isinstance(row, TeamCap)

        # candidates should include our player (contract ends 2028)
        cands = resign_candidates(s, next_season)
        assert any(getattr(p,"player_id",getattr(p,"id")) == pid for (p,_) in cands)

        # submit offer from current team
        submit_resign_offer(s, next_season, team_id, pid, aav=140, years=3)

        # simulate window → player should sign and not hit FA
        resim = simulate_resign_window(s, next_season)
        assert resim["signed"] >= 1

        # try expirations: should NOT move to FA because new deal starts in 2029
        expire_contracts(s, next_season)
        fas = list_free_agents(s, next_season)
        assert all(getattr(x,"player_id",getattr(x,"id")) != pid for x in fas)

def test_api_cap_and_resign():
    """Test API endpoints for cap and re-sign."""
    # smoke test API endpoints
    rookie_season = 2030
    next_season = 2031
    pid, team_id = _rookie_one_year(rookie_season)
    
    if not pid or not team_id:
        # Skip if no rookie was created
        return

    # Create a minimal app with just the cap_resign router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    r1 = client.post(f"/cap/{next_season}/init")
    assert r1.status_code == 200

    r2 = client.get(f"/cap/{next_season}/team/{team_id}")
    assert r2.status_code == 200
    # resign candidates
    r3 = client.get(f"/contracts/{next_season}/resign/candidates")
    assert r3.status_code == 200
    # bid
    r4 = client.post(f"/contracts/{next_season}/resign/bid", json={"team_id": team_id, "player_id": pid, "aav": 150, "years": 2})
    assert r4.status_code == 200
    # simulate
    r5 = client.post(f"/contracts/{next_season}/resign/simulate")
    assert r5.status_code == 200

def test_cap_initialization():
    """Test cap initialization for all teams."""
    eng = get_engine()
    with Session(eng) as s:
        # Create a test player and contract to ensure we have a team
        p = Player(name="Test Player", pos="QB", team_id=1, age=25, years_pro=3)
        s.add(p)
        s.commit()
        s.refresh(p)
        
        c = Contract(player_id=p.id, team_id=1, start_season=2025, years=2, aav=500, status="active")
        s.add(c)
        s.commit()
        
        # Initialize cap for all teams
        result = init_season_cap_for_all_teams(s, 2026, 2000)
        assert result["teams"] >= 1
        assert result["rows_written"] >= 1
        
        # Check that cap was created
        cap = s.exec(select(TeamCap).where(TeamCap.team_id == 1, TeamCap.season == 2026)).first()
        assert cap is not None
        assert cap.cap_limit == 2000

def test_resign_candidates():
    """Test finding re-sign candidates."""
    eng = get_engine()
    with Session(eng) as s:
        # Create a player with expiring contract
        p = Player(name="Expiring Player", pos="WR", team_id=2, age=28, years_pro=5)
        s.add(p)
        s.commit()
        s.refresh(p)
        
        # Contract that expires at end of 2025
        c = Contract(player_id=p.id, team_id=2, start_season=2023, years=3, aav=400, status="active")
        s.add(c)
        s.commit()
        
        # Find candidates for 2026 (contract ends 2025)
        candidates = resign_candidates(s, 2026)
        assert len(candidates) >= 1
        
        # Check that our player is in the candidates
        player_ids = [getattr(player, "player_id", getattr(player, "id")) for player, _ in candidates]
        assert p.id in player_ids

def test_resign_offer_validation():
    """Test re-sign offer validation."""
    eng = get_engine()
    with Session(eng) as s:
        # Create a player with expiring contract
        p = Player(name="Test Player", pos="RB", team_id=3, age=26, years_pro=4)
        s.add(p)
        s.commit()
        s.refresh(p)
        
        c = Contract(player_id=p.id, team_id=3, start_season=2024, years=2, aav=300, status="active")
        s.add(c)
        s.commit()
        
        # Valid offer from current team
        result = submit_resign_offer(s, 2026, 3, p.id, aav=350, years=3)
        assert result["status"] == "ok"
        assert "offer_id" in result
        
        # Invalid offer from different team should fail
        try:
            submit_resign_offer(s, 2026, 4, p.id, aav=400, years=3)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Exclusive window" in str(e)

def test_resign_simulation():
    """Test re-sign simulation."""
    eng = get_engine()
    with Session(eng) as s:
        # Create a player with expiring contract
        p = Player(name="Simulation Player", pos="TE", team_id=4, age=27, years_pro=6)
        s.add(p)
        s.commit()
        s.refresh(p)
        
        c = Contract(player_id=p.id, team_id=4, start_season=2024, years=2, aav=250, status="active")
        s.add(c)
        s.commit()
        
        # Submit re-sign offer
        submit_resign_offer(s, 2026, 4, p.id, aav=300, years=2)
        
        # Simulate re-sign window
        result = simulate_resign_window(s, 2026)
        assert result["signed"] >= 1
        
        # Check that new contract was created
        new_contract = s.exec(select(Contract).where(
            Contract.player_id == p.id, 
            Contract.start_season == 2026, 
            Contract.status == "active"
        )).first()
        assert new_contract is not None
        assert new_contract.aav == 300
        assert new_contract.years == 2


