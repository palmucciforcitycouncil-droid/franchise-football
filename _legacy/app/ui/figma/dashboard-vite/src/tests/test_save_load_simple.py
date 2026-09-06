# tests/test_save_load_simple.py
from pathlib import Path
import json
from sqlmodel import Session, select
from app.db import get_engine
from app.services.save_load import export_league_to_json, import_league_from_json
from app.models.core_min import Player, Team
from app.models.awards import AwardResult
from app.models.season_stats import TeamSeasonStats

def test_save_load_basic_functionality():
    """Test basic save/load functionality with minimal data."""
    engine = get_engine()
    
    # Create test data
    with Session(engine) as session:
        # Create team
        team = Team(abbrev="KC", name="Kansas City Chiefs")
        session.add(team)
        session.commit()
        
        # Create player
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
        
        # Create season stats
        stats = TeamSeasonStats(
            team_id=team.id,
            season=2025,
            games=17,
            points_for=300,
            points_against=250,
            wins=10,
            losses=7
        )
        session.add(stats)
        session.commit()
        
        # Export
        res = export_league_to_json(session, "test_basic", season=2025, out_dir=Path("data/saves"))
        assert "sha256" in res
        assert res["bytes"] > 100
        assert Path(res["path"]).exists()
        
        # Count before
        before_players = len(session.exec(select(Player)).all())
        before_teams = len(session.exec(select(Team)).all())
        before_stats = len(session.exec(select(TeamSeasonStats)).all())
    
    # Import
    with Session(engine) as session:
        res2 = import_league_from_json(session, Path("data/saves/test_basic.json"), strategy="replace")
        assert "sha256" in res2
        assert res2["sha256"] == res["sha256"]  # Checksum should match
        
        # Count after
        after_players = len(session.exec(select(Player)).all())
        after_teams = len(session.exec(select(Team)).all())
        after_stats = len(session.exec(select(TeamSeasonStats)).all())
        
        # Verify counts match
        assert before_players == after_players
        assert before_teams == after_teams
        assert before_stats == after_stats

def test_json_structure():
    """Test that exported JSON has correct structure."""
    engine = get_engine()
    
    with Session(engine) as session:
        # Create minimal data
        team = Team(abbrev="TEST", name="Test Team")
        session.add(team)
        session.commit()
        
        # Export
        res = export_league_to_json(session, "structure_test", season=2025, out_dir=Path("data/saves"))
        path = Path(res["path"])
        
        # Load and verify structure
        data = json.loads(path.read_text(encoding="utf-8"))
        
        # Check required fields
        assert "schema_version" in data
        assert "season" in data
        assert "generated_at" in data
        assert data["schema_version"] == "FF-SAVE-v1"
        assert data["season"] == 2025
        
        # Check data tables
        required_tables = ["players", "team_season_stats", "player_season_stats", "awards", "player_progression", "rollover_audit"]
        for table in required_tables:
            assert table in data
            assert isinstance(data[table], list)

def test_checksum_verification():
    """Test that checksum verification works."""
    engine = get_engine()
    
    with Session(engine) as session:
        # Create minimal data
        team = Team(abbrev="CHECK", name="Check Team")
        session.add(team)
        session.commit()
        
        # Export
        res = export_league_to_json(session, "checksum_test", season=2025, out_dir=Path("data/saves"))
        path = Path(res["path"])
        
        # Verify checksum
        raw = path.read_bytes()
        import hashlib
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == res["sha256"], "Checksum mismatch"

def test_import_strategy_replace():
    """Test import with replace strategy."""
    engine = get_engine()
    
    with Session(engine) as session:
        # Create initial data
        team = Team(abbrev="REPLACE", name="Replace Team")
        session.add(team)
        session.commit()
        
        # Export
        export_league_to_json(session, "replace_test", season=2025, out_dir=Path("data/saves"))
        
        # Import with replace strategy
        res = import_league_from_json(session, Path("data/saves/replace_test.json"), strategy="replace")
        
        assert "sha256" in res
        assert "counts" in res
        assert isinstance(res["counts"], dict)
        
        # Verify counts are reasonable
        counts = res["counts"]
        assert counts["players"] >= 0
        assert counts["team_season"] >= 0
        assert counts["player_season"] >= 0
        assert counts["awards"] >= 0
        assert counts["progression"] >= 0
        assert counts["rollover"] >= 0
