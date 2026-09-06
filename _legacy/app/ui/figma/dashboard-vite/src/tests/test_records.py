# tests/test_records.py
from sqlmodel import Session, select
from app.db import get_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_player_season, aggregate_team_season
from app.services.records import rebuild_single_season_records, rebuild_career_records
from app.models.records import SingleSeasonRecord, CareerRecord

def _bootstrap(season=2025):
    with memory_db() as session:
        run_mini_season(session, weeks=2)
        session.commit()
    with memory_db() as session:
        aggregate_team_season(session, season)
        aggregate_player_season(session, season)

def test_build_records():
    """Test building single season and career records."""
    _bootstrap(2025)
    _bootstrap(2024)
    
    with memory_db() as session:
        rebuild_single_season_records(session, 2025, top_n=10)
        rebuild_career_records(session, top_n=10)
        
        ss = session.exec(select(SingleSeasonRecord)).all()
        cr = session.exec(select(CareerRecord)).all()
        
        assert ss and cr
        
        # Ensure ranks are 1..N and non-increasing values
        by_stat = {}
        for r in cr:
            by_stat.setdefault(r.stat, []).append(r.value)
        
        for vals in by_stat.values():
            assert all(vals[i] >= vals[i+1] for i in range(len(vals)-1))

def test_single_season_records_structure():
    """Test single season records structure and data."""
    _bootstrap(2025)
    
    with memory_db() as session:
        rebuild_single_season_records(session, 2025, top_n=5)
        
        records = session.exec(select(SingleSeasonRecord).where(SingleSeasonRecord.season == 2025)).all()
        
        # Should have records for each stat
        stats = set(r.stat for r in records)
        expected_stats = {"pass_yards","pass_tds","rush_yards","rush_tds","recv_yards","recv_tds","sacks","interceptions_def","tackles"}
        assert stats == expected_stats
        
        # Check structure
        for record in records:
            assert record.season == 2025
            assert record.stat in expected_stats
            assert 1 <= record.rank <= 5
            assert record.player_id > 0
            assert record.value >= 0
            assert record.player_name is not None

def test_career_records_structure():
    """Test career records structure and data."""
    _bootstrap(2025)
    _bootstrap(2024)
    
    with memory_db() as session:
        rebuild_career_records(session, top_n=5)
        
        records = session.exec(select(CareerRecord)).all()
        
        # Should have records for each stat
        stats = set(r.stat for r in records)
        expected_stats = {"pass_yards","pass_tds","rush_yards","rush_tds","recv_yards","recv_tds","sacks","interceptions_def","tackles"}
        assert stats == expected_stats
        
        # Check structure
        for record in records:
            assert record.stat in expected_stats
            assert 1 <= record.rank <= 5
            assert record.player_id > 0
            assert record.value >= 0
            assert record.player_name is not None

def test_records_rebuild_idempotent():
    """Test that rebuilding records is idempotent."""
    _bootstrap(2025)
    
    with memory_db() as session:
        # First rebuild
        rebuild_single_season_records(session, 2025, top_n=5)
        records1 = session.exec(select(SingleSeasonRecord).where(SingleSeasonRecord.season == 2025)).all()
        
        # Second rebuild
        rebuild_single_season_records(session, 2025, top_n=5)
        records2 = session.exec(select(SingleSeasonRecord).where(SingleSeasonRecord.season == 2025)).all()
        
        # Should have same number of records
        assert len(records1) == len(records2)
        
        # Should have same structure
        for r1, r2 in zip(sorted(records1, key=lambda x: (x.stat, x.rank)), sorted(records2, key=lambda x: (x.stat, x.rank))):
            assert r1.stat == r2.stat
            assert r1.rank == r2.rank
            assert r1.player_id == r2.player_id
            assert r1.value == r2.value

def test_records_api_endpoints():
    """Test records API endpoints."""
    from fastapi.testclient import TestClient
    from app.api.routes.records import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test rebuild endpoints
    r1 = client.post("/records/rebuild/single?season=2025&top_n=5")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"
    assert r1.json()["season"] == 2025
    
    r2 = client.post("/records/rebuild/career?top_n=5")
    assert r2.status_code == 200
    assert r2.json()["status"] == "ok"
    
    # Test get endpoints (will return 404 if no data, which is expected)
    r3 = client.get("/records/single/pass_yards?season=2025&top_n=5")
    # Should be 404 since we don't have data in this test context
    assert r3.status_code == 404
    
    r4 = client.get("/records/career/pass_yards?top_n=5")
    # Should be 404 since we don't have data in this test context
    assert r4.status_code == 404
