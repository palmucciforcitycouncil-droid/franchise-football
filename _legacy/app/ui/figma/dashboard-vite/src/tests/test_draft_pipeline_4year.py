# tests/test_draft_pipeline_4year.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.models.draft import Prospect
from app.services.draft_pipeline import seed_four_year_pipeline, rollover_draft_pipeline, finalize_draft_year
from app.models.core_min import Player

def _counts(s, year):
    rows = s.exec(select(Prospect).where(Prospect.expected_draft_season==year)).all()
    return len(rows)

def test_seed_sizes_and_distribution():
    season = 2040
    eng = get_engine()
    with Session(eng) as s:
        res = seed_four_year_pipeline(s, season, master_seed=123)
        # should create classes only if missing
        # Check at least FR class exists
        total = 0
        for es in (season, season+1, season+2, season+3):
            total += _counts(s, es)
        assert total >= 4*300 - 20  # approximate (we set 304 per class)
        # distribution spot check
        frs = s.exec(select(Prospect).where(Prospect.expected_draft_season==season+3, Prospect.class_year=="FR")).all()
        assert frs and len([x for x in frs if x.pos=="QB"]) == 15

def test_rollover_growth_and_early_declare_cap():
    season = 2041
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, season-1, master_seed=999)
        # rollover into 2041 (creates new FR for 2044 and advances others)
        res = rollover_draft_pipeline(s, season, master_seed=999, max_early_declares=25)
        assert res["early_declared"] <= 25
        # JR should now mostly be SR or declared
        seniors = s.exec(select(Prospect).where(Prospect.class_year=="SR", Prospect.eligible_season==season)).all()
        assert len(seniors) > 0
        # Positive bias check: take some FR->SO upgrades and compare average OVR
        so_now = s.exec(select(Prospect).where(Prospect.class_year=="SO", Prospect.expected_draft_season==season+2)).all()
        assert so_now  # at least some
        # Can't easily compare to previous values, but average OVR should be >= 50-ish after uplift
        avg_ovr = sum(p.overall for p in so_now)/len(so_now)
        assert avg_ovr >= 48

def test_finalize_udfa_promotion():
    season = 2042
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, season, master_seed=1)
        rollover_draft_pipeline(s, season, master_seed=1)
        # Mark some SR as undrafted-eligible
        sr = s.exec(select(Prospect).where(Prospect.class_year=="SR", Prospect.eligible_season==season)).all()
        assert sr
        # no drafted_by_team_id set, finalize should promote them to Players
        res = finalize_draft_year(s, season)
        assert res["udfa_promoted"] >= 1
        # verify at least one Player exists with team_id None
        p = s.exec(select(Player).where(Player.team_id==None)).first()
        assert p is not None

def test_pipeline_api_endpoints():
    """Test the pipeline API endpoints."""
    from fastapi.testclient import TestClient
    from app.api.routes.draft_pipeline import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    season = 2043
    
    # Test seed endpoint
    resp = client.post(f"/draft/{season}/pipeline/seed?seed=123")
    assert resp.status_code == 200
    data = resp.json()
    assert "created" in data
    assert "classes" in data
    
    # Test pipeline overview
    resp = client.get(f"/draft/{season}/pipeline")
    assert resp.status_code == 200
    data = resp.json()
    assert "season" in data
    assert "counts" in data
    assert "by_pos" in data
    
    # Test class listing
    resp = client.get(f"/draft/{season}/class/FR")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    
    # Test watchlist functionality
    if data:  # if we have prospects
        prospect_ids = [p["id"] for p in data[:3]]
        resp = client.post(f"/draft/{season}/watchlist", json={"ids": prospect_ids})
        assert resp.status_code == 200
        
        resp = client.get(f"/draft/{season}/watchlist")
        assert resp.status_code == 200
        watchlist = resp.json()
        assert len(watchlist) >= 3

def test_early_declaration_logic():
    """Test early declaration probabilities and thresholds."""
    from app.services.draft_pipeline import _maybe_early_declare
    import random
    
    rng = random.Random(12345)
    
    # Test QB early declaration (should be likely at 70+)
    qb_declares = sum(_maybe_early_declare(rng, "QB", 75) for _ in range(100))
    assert qb_declares > 30  # Should be high probability
    
    # Test other positions (should be lower probability)
    rb_declares = sum(_maybe_early_declare(rng, "RB", 75) for _ in range(100))
    assert rb_declares < qb_declares  # QBs more likely to declare early
    
    # Test very low overall (should rarely declare)
    low_declares = sum(_maybe_early_declare(rng, "QB", 65) for _ in range(100))
    assert low_declares < 20  # Low probability for low overall

def test_ovr_recalculation():
    """Test OVR recalculation after attribute changes."""
    from app.services.draft_pipeline import _ovr_from_attrs
    
    # Test QB OVR calculation
    qb_attrs = {"speed": 80, "agility": 75, "strength": 70, "awareness": 85, "potential": 90}
    qb_ovr = _ovr_from_attrs("QB", qb_attrs)
    assert 30 <= qb_ovr <= 99
    
    # Test that higher attributes lead to higher OVR
    better_qb_attrs = {"speed": 85, "agility": 80, "strength": 75, "awareness": 90, "potential": 95}
    better_qb_ovr = _ovr_from_attrs("QB", better_qb_attrs)
    assert better_qb_ovr >= qb_ovr

def test_position_distribution():
    """Test that position distribution is correct."""
    season = 2044
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, season, master_seed=456)
        
        # Check FR class distribution
        frs = s.exec(select(Prospect).where(Prospect.class_year=="FR", Prospect.expected_draft_season==season+3)).all()
        
        pos_counts = {}
        for p in frs:
            pos_counts[p.pos] = pos_counts.get(p.pos, 0) + 1
        
        # Verify expected counts
        expected_counts = {
            "QB": 15, "RB": 26, "WR": 39, "TE": 16, "OL": 48,
            "DL": 51, "LB": 42, "DB": 61, "K": 3, "P": 3,
        }
        
        for pos, expected in expected_counts.items():
            assert pos_counts.get(pos, 0) == expected, f"Position {pos} count mismatch: {pos_counts.get(pos, 0)} vs {expected}"

def test_age_progression():
    """Test that ages progress correctly through the pipeline."""
    season = 2045
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, season, master_seed=789)
        
        # Check initial ages
        frs = s.exec(select(Prospect).where(Prospect.class_year=="FR")).all()
        for p in frs:
            assert 18 <= p.age <= 19
        
        # Rollover and check age progression
        rollover_draft_pipeline(s, season+1, master_seed=789)
        
        # Check that FR became SO and aged up
        sos = s.exec(select(Prospect).where(Prospect.class_year=="SO")).all()
        for p in sos:
            assert 19 <= p.age <= 20

def test_idempotency():
    """Test that operations are idempotent."""
    season = 2046
    eng = get_engine()
    with Session(eng) as s:
        # First seed
        res1 = seed_four_year_pipeline(s, season, master_seed=111)
        created1 = res1["created"]
        
        # Second seed (should be idempotent)
        res2 = seed_four_year_pipeline(s, season, master_seed=111)
        created2 = res2["created"]
        
        # Should not create duplicates
        assert created2 == 0
        
        # Test rollover idempotency
        res3 = rollover_draft_pipeline(s, season+1, master_seed=111)
        res4 = rollover_draft_pipeline(s, season+1, master_seed=111)
        
        assert res4["status"] == "noop"

def test_watchlist_functionality():
    """Test watchlist add/remove functionality."""
    season = 2047
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, season, master_seed=222)
        
        # Get some prospects
        prospects = s.exec(select(Prospect).limit(5)).all()
        assert len(prospects) >= 3
        
        # Add to watchlist
        for p in prospects[:3]:
            p.watchlist = True
            s.add(p)
        s.commit()
        
        # Check watchlist
        watchlist = s.exec(select(Prospect).where(Prospect.watchlist==True)).all()
        assert len(watchlist) >= 3
        
        # Remove from watchlist
        for p in prospects[:2]:
            p.watchlist = False
            s.add(p)
        s.commit()
        
        # Check watchlist again
        watchlist = s.exec(select(Prospect).where(Prospect.watchlist==True)).all()
        assert len(watchlist) >= 1

def test_class_filtering():
    """Test class filtering by year and position."""
    season = 2048
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, season, master_seed=333)
        
        # Test FR class filtering
        fr_qbs = s.exec(select(Prospect).where(
            Prospect.class_year=="FR",
            Prospect.pos=="QB"
        )).all()
        assert len(fr_qbs) == 15
        
        # Test SR class filtering (after rollover)
        rollover_draft_pipeline(s, season+1, master_seed=333)
        
        sr_eligible = s.exec(select(Prospect).where(
            Prospect.class_year=="SR",
            Prospect.eligible_season==season+1
        )).all()
        assert len(sr_eligible) > 0


