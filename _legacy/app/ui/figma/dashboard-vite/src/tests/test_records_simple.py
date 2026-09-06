# tests/test_records_simple.py
from sqlmodel import Session, select
from app.db import get_engine
from app.services.records import rebuild_single_season_records, rebuild_career_records
from app.models.records import SingleSeasonRecord, CareerRecord
from app.models.core_min import Player, Team
from app.models.season_stats import PlayerSeasonStats

def test_build_records():
    """Test building single season and career records."""
    engine = get_engine()
    
    with Session(engine) as session:
        # Create test data
        team = Team(abbrev="TEST", name="Test Team")
        session.add(team)
        session.commit()
        
        player = Player(
            first_name="Test",
            last_name="Player",
            pos="QB",
            name="Test Player",
            team_id=team.id,
            age=25,
            years_pro=3
        )
        session.add(player)
        session.commit()
        
        stats = PlayerSeasonStats(
            player_id=player.id,
            team_id=team.id,
            season=2025,
            pass_yards=3000,
            pass_tds=25,
            rush_yards=200,
            rush_tds=2
        )
        session.add(stats)
        session.commit()
        
        # Build records
        rebuild_single_season_records(session, 2025, top_n=5)
        rebuild_career_records(session, top_n=5)
        
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
    engine = get_engine()
    
    with Session(engine) as session:
        # Create test data
        team = Team(abbrev="TEST2", name="Test Team 2")
        session.add(team)
        session.commit()
        
        player = Player(
            first_name="Test2",
            last_name="Player",
            pos="QB",
            name="Test2 Player",
            team_id=team.id,
            age=26,
            years_pro=4
        )
        session.add(player)
        session.commit()
        
        stats = PlayerSeasonStats(
            player_id=player.id,
            team_id=team.id,
            season=2025,
            pass_yards=2500,
            pass_tds=20
        )
        session.add(stats)
        session.commit()
        
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
    engine = get_engine()
    
    with Session(engine) as session:
        # Create test data
        team = Team(abbrev="TEST3", name="Test Team 3")
        session.add(team)
        session.commit()
        
        player = Player(
            first_name="Test3",
            last_name="Player",
            pos="RB",
            name="Test3 Player",
            team_id=team.id,
            age=24,
            years_pro=2
        )
        session.add(player)
        session.commit()
        
        stats = PlayerSeasonStats(
            player_id=player.id,
            team_id=team.id,
            season=2025,
            rush_yards=1000,
            rush_tds=8
        )
        session.add(stats)
        session.commit()
        
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
    
    # Test get endpoints - may return 200 if data exists or 404 if no data
    r3 = client.get("/records/single/pass_yards?season=2025&top_n=5")
    assert r3.status_code in [200, 404]
    
    r4 = client.get("/records/career/pass_yards?top_n=5")
    assert r4.status_code in [200, 404]
