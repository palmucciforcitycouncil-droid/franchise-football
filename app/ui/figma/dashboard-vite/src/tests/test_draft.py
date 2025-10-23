# tests/test_draft.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks
from app.models.draft import Prospect, DraftPick
from app.models.core_min import Team
from app.models.season_stats import TeamSeasonStats

client = TestClient(app)

def test_generate_order_and_pick():
    """Test generating draft class, order, and making picks."""
    season = 2026
    eng = get_engine()
    with Session(eng) as s:
        count = generate_draft_class(s, season, seed=1337)
        assert count == 280  # POS_DISTRIBUTION sums to 280
        picks = assign_picks(s, season)
        assert picks == 32*7  # 7 rounds * 32 teams = 224 picks
        
        # Grab best WR
        wr = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="WR").order_by(Prospect.overall.desc())).first()
        pick1 = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        
        from app.services.draft import make_selection
        res = make_selection(s, season, 1, wr.id, pick1.team_id)
        assert res["overall_pick"] == 1
        assert res["prospect_id"] == wr.id
        assert res["team_id"] == pick1.team_id
        
        # Verify the pick was recorded
        updated_pick = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        assert updated_pick.prospect_id == wr.id
        
        # Verify the prospect was marked as drafted
        updated_prospect = s.exec(select(Prospect).where(Prospect.id == wr.id)).first()
        assert updated_prospect.drafted_by_team_id == pick1.team_id
        assert updated_prospect.drafted_overall_pick == 1
        
        # double-picking should fail
        import pytest
        with pytest.raises(ValueError):
            make_selection(s, season, 1, wr.id, pick1.team_id)

def test_api_endpoints():
    """Test draft API endpoints."""
    season = 2027
    
    # Generate draft class
    r = client.post(f"/draft/{season}/generate?seed=2025")
    assert r.status_code == 200
    data = r.json()
    assert data["season"] == season
    assert data["prospects"] == 280
    assert data["picks"] == 224
    
    # Get draft class
    r2 = client.get(f"/draft/{season}/class")
    assert r2.status_code == 200
    cls = r2.json()
    assert len(cls) == 280
    
    # Get draft order
    r3 = client.get(f"/draft/{season}/order")
    assert r3.status_code == 200
    order = r3.json()
    assert len(order) == 224
    
    # Make a pick via API
    wr = next(p for p in cls if p["pos"]=="WR")
    payload = {"overall_pick": 1, "prospect_id": wr["id"], "team_id": order[0]["team_id"]}
    rp = client.post(f"/draft/{season}/pick", json=payload)
    assert rp.status_code == 200
    
    # Verify the pick was made
    pick_result = rp.json()
    assert pick_result["overall_pick"] == 1
    assert pick_result["prospect_id"] == wr["id"]
    assert pick_result["team_id"] == order[0]["team_id"]

def test_draft_determinism():
    """Test that draft generation is deterministic with same seed."""
    season1 = 2028
    season2 = 2029
    
    eng = get_engine()
    with Session(eng) as s:
        # Generate two draft classes with same seed
        count1 = generate_draft_class(s, season1, seed=1234)
        count2 = generate_draft_class(s, season2, seed=1234)
        
        assert count1 == count2 == 280
        
        # Get prospects from both seasons
        prospects1 = s.exec(select(Prospect).where(Prospect.season==season1).order_by(Prospect.id)).all()
        prospects2 = s.exec(select(Prospect).where(Prospect.season==season2).order_by(Prospect.id)).all()
        
        # Should have same names and attributes (deterministic)
        for p1, p2 in zip(prospects1, prospects2):
            assert p1.name == p2.name
            assert p1.pos == p2.pos
            assert p1.overall == p2.overall
            assert p1.speed == p2.speed
            assert p1.strength == p2.strength
            assert p1.agility == p2.agility
            assert p1.awareness == p2.awareness
            assert p1.potential == p2.potential

def test_draft_order_from_standings():
    """Test draft order generation from standings."""
    season = 2030
    eng = get_engine()
    
    with Session(eng) as s:
        # Create test teams with different records
        teams = []
        for i in range(1, 5):  # Create 4 teams for testing
            team = Team(abbrev=f"T{i}", name=f"Team {i}")
            session.add(team)
            teams.append(team)
        s.commit()
        
        # Create season stats with different win totals
        stats = [
            TeamSeasonStats(team_id=teams[0].id, season=season, wins=2, losses=15, ties=0),  # Worst record
            TeamSeasonStats(team_id=teams[1].id, season=season, wins=5, losses=12, ties=0),
            TeamSeasonStats(team_id=teams[2].id, season=season, wins=8, losses=9, ties=0),
            TeamSeasonStats(team_id=teams[3].id, season=season, wins=12, losses=5, ties=0),  # Best record
        ]
        for stat in stats:
            s.add(stat)
        s.commit()
        
        from app.services.draft import draft_order_from_standings
        order = draft_order_from_standings(s, season)
        
        # Should be ordered worst to best
        assert order[0] == teams[0].id  # Worst team first
        assert order[1] == teams[1].id
        assert order[2] == teams[2].id
        assert order[3] == teams[3].id  # Best team last

def test_position_distribution():
    """Test that draft class has correct position distribution."""
    season = 2031
    eng = get_engine()
    
    with Session(eng) as s:
        count = generate_draft_class(s, season, seed=2025)
        assert count == 280
        
        # Count prospects by position
        prospects = s.exec(select(Prospect).where(Prospect.season==season)).all()
        pos_counts = {}
        for p in prospects:
            pos_counts[p.pos] = pos_counts.get(p.pos, 0) + 1
        
        # Verify distribution matches POS_DISTRIBUTION
        from app.services.draft import POS_DISTRIBUTION
        for pos, expected_count in POS_DISTRIBUTION.items():
            assert pos_counts[pos] == expected_count, f"Position {pos}: expected {expected_count}, got {pos_counts[pos]}"
