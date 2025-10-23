# tests/test_save_load_roundtrip.py
from pathlib import Path
import json
from sqlmodel import Session, select
from app.db import get_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season
from app.services.awards import compute_and_persist_awards
from app.services.progression import apply_progression_for_season
from app.services.save_load import export_league_to_json, import_league_from_json
from app.models.core_min import Player
from app.models.awards import AwardResult
from app.models.season_stats import TeamSeasonStats, PlayerSeasonStats
from app.models.progression import PlayerProgression
from app.models.rollover import RolloverAudit

def _bootstrap(season: int):
    with memory_db() as session:
        run_mini_season(session, weeks=2)
        session.commit()
    with memory_db() as session:
        aggregate_team_season(session, season)
        aggregate_player_season(session, season)
        compute_and_persist_awards(session, season)
        apply_progression_for_season(session, season=season, seed=2025, force=True)

def _counts(s: Session):
    return {
        "players": s.exec(select(Player)).count(),
        "tss": s.exec(select(TeamSeasonStats)).count(),
        "pss": s.exec(select(PlayerSeasonStats)).count(),
        "aw": s.exec(select(AwardResult)).count(),
        "prog": s.exec(select(PlayerProgression)).count(),
        "roll": s.exec(select(RolloverAudit)).count(),
    }

def test_save_then_load_roundtrip():
    """Test complete save/load roundtrip with data integrity."""
    season = 2025
    _bootstrap(season)
    
    with memory_db() as session:
        # Export
        res = export_league_to_json(session, "league_test", season=season, out_dir=Path("data/saves"))
        assert "sha256" in res and res["bytes"] > 100
        assert Path(res["path"]).exists()
        
        before_counts = _counts(session)
    
    # Destructive load: truncate/replace and reinsert from file
    with memory_db() as session:
        # Wipe everything first to ensure it's a true import
        from app.services.save_load import _truncate_tables
        _truncate_tables(session, [AwardResult, PlayerProgression, PlayerSeasonStats, TeamSeasonStats, RolloverAudit, Player])
        
        res2 = import_league_from_json(session, Path("data/saves/league_test.json"), strategy="replace")
        after_counts = _counts(session)
        
        assert before_counts == after_counts, f"Counts mismatch: {before_counts} != {after_counts}"
        assert "sha256" in res2

def test_schema_version_and_checksum_stable():
    """Test that schema version and checksum are stable."""
    season = 2025
    _bootstrap(season)
    
    with memory_db() as session:
        res = export_league_to_json(session, "chk", season=season, out_dir=Path("data/saves"))
        path = Path(res["path"])
        raw = path.read_bytes()
        import hashlib
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == res["sha256"], "Checksum mismatch"

def test_export_structure():
    """Test that exported JSON has the expected structure."""
    season = 2025
    _bootstrap(season)
    
    with memory_db() as session:
        res = export_league_to_json(session, "structure_test", season=season, out_dir=Path("data/saves"))
        path = Path(res["path"])
        
        # Load and verify structure
        data = json.loads(path.read_text(encoding="utf-8"))
        
        # Check required top-level fields
        assert "schema_version" in data
        assert "season" in data
        assert "generated_at" in data
        assert data["schema_version"] == "FF-SAVE-v1"
        assert data["season"] == season
        
        # Check data tables
        assert "players" in data
        assert "team_season_stats" in data
        assert "player_season_stats" in data
        assert "awards" in data
        assert "player_progression" in data
        assert "rollover_audit" in data
        
        # Verify all are lists
        for key in ["players", "team_season_stats", "player_season_stats", "awards", "player_progression", "rollover_audit"]:
            assert isinstance(data[key], list)

def test_import_strategy_replace():
    """Test import with replace strategy."""
    season = 2025
    _bootstrap(season)
    
    with memory_db() as session:
        # Export
        export_league_to_json(session, "strategy_test", season=season, out_dir=Path("data/saves"))
        
        # Import with replace strategy
        res = import_league_from_json(session, Path("data/saves/strategy_test.json"), strategy="replace")
        
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

def test_import_schema_version_check():
    """Test that import validates schema version."""
    season = 2025
    _bootstrap(season)
    
    with memory_db() as session:
        # Export
        export_league_to_json(session, "schema_test", season=season, out_dir=Path("data/saves"))
        
        # Modify the schema version in the file
        path = Path("data/saves/schema_test.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["schema_version"] = "INVALID-VERSION"
        path.write_text(json.dumps(data), encoding="utf-8")
        
        # Try to import - should fail
        try:
            import_league_from_json(session, path, strategy="replace")
            assert False, "Should have raised ValueError for schema mismatch"
        except ValueError as e:
            assert "Schema mismatch" in str(e)
