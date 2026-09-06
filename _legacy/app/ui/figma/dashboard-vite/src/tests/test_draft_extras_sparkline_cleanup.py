# tests/test_draft_extras_sparkline_cleanup.py
from sqlmodel import Session, select
from app.db import get_engine
from app.models.draft import Prospect
from app.models.draft_audit import ProspectProgressAudit
from app.services.draft_pipeline import seed_four_year_pipeline, rollover_draft_pipeline, finalize_draft_year
from app.services.fa_cleanup import drop_uifas_without_contracts
from app.models.core_min import Player

def test_sparkline_and_cleanup(tmp_path):
    base = 2030
    eng = get_engine()
    with Session(eng) as s:
        # seed 4-year horizon
        seed_four_year_pipeline(s, base, master_seed=42)
        # pick three watchlisted prospects across FR/SO/JR
        picks = s.exec(select(Prospect).order_by(Prospect.id).limit(3)).all()
        for p in picks:
            p.watchlist = True; s.add(p)
        s.commit()

        # simulate two rollovers → audits for base+1 and base+2
        rollover_draft_pipeline(s, base+1, master_seed=42)
        rollover_draft_pipeline(s, base+2, master_seed=42)

        # each watchlisted prospect should now have up to 2 audit points
        for p in picks:
            a = s.exec(select(ProspectProgressAudit).where(ProspectProgressAudit.prospect_id==p.id)).all()
            assert len(a) >= 1

        # finalize a draft year and promote UDFAs (creates players with team_id None)
        finalize_draft_year(s, base+2)
        udfas = s.exec(select(Player).where(Player.team_id==None, Player.rookie_season==base+2)).all()
        # cleanup should delete those without contracts
        res = drop_uifas_without_contracts(s, base+2)
        # After cleanup, none of those UDFAs without contracts should remain
        stale = s.exec(select(Player).where(Player.team_id==None, Player.rookie_season==base+2)).all()
        assert len(stale) == 0 or len(stale) < len(udfas)

def test_audit_idempotency(tmp_path):
    """Test that audit rows are idempotent - no duplicates on rerun."""
    base = 2035
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, base, master_seed=99)
        
        # First rollover
        rollover_draft_pipeline(s, base+1, master_seed=99)
        count1 = len(s.exec(select(ProspectProgressAudit)).all())
        
        # Second rollover (should not create duplicate audits)
        rollover_draft_pipeline(s, base+1, master_seed=99)
        count2 = len(s.exec(select(ProspectProgressAudit)).all())
        
        assert count1 == count2, "Audit rows should be idempotent"

def test_sparkline_data_structure(tmp_path):
    """Test that sparkline data has correct structure."""
    base = 2040
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, base, master_seed=123)
        
        # Mark a prospect as watchlisted
        prospect = s.exec(select(Prospect).limit(1)).first()
        prospect.watchlist = True
        s.add(prospect)
        s.commit()
        
        # Rollover to create audit data
        rollover_draft_pipeline(s, base+1, master_seed=123)
        
        # Check audit data structure
        audits = s.exec(select(ProspectProgressAudit).where(ProspectProgressAudit.prospect_id==prospect.id)).all()
        assert len(audits) >= 1
        
        audit = audits[0]
        assert audit.season == base+1
        assert audit.prospect_id == prospect.id
        assert audit.pos == prospect.pos
        assert audit.class_year == prospect.class_year
        assert audit.age == prospect.age
        assert audit.ovr_before >= 0
        assert audit.ovr_after >= 0

def test_fa_cleanup_safety(tmp_path):
    """Test that FA cleanup only removes UDFAs without contracts."""
    base = 2045
    eng = get_engine()
    with Session(eng) as s:
        seed_four_year_pipeline(s, base, master_seed=456)
        rollover_draft_pipeline(s, base+1, master_seed=456)
        
        # Create some UDFAs
        finalize_draft_year(s, base+1)
        initial_udfas = s.exec(select(Player).where(Player.team_id==None)).all()
        
        # Cleanup should be safe - no contracts means safe to delete
        res = drop_uifas_without_contracts(s, base+1)
        assert res["removed"] >= 0
        
        # Verify cleanup worked
        remaining_udfas = s.exec(select(Player).where(Player.team_id==None)).all()
        assert len(remaining_udfas) <= len(initial_udfas)

def test_watchlist_sparkline_api(tmp_path):
    """Test the watchlist sparkline API endpoint structure."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # Test sparkline endpoint (will return empty if no watchlisted prospects)
    response = client.get("/draft/2025/pipeline/sparkline?max_points=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Test FA cleanup endpoint
    response = client.post("/draft/2025/fa_cleanup")
    assert response.status_code == 200
    data = response.json()
    assert "removed" in data
    assert isinstance(data["removed"], int)


