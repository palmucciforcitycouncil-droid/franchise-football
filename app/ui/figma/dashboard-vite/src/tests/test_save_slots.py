# tests/test_save_slots.py
from pathlib import Path
from sqlmodel import Session
from app.db import get_engine
from app.services.save_load import export_league_to_json, import_league_from_json, list_saves, rename_save, delete_save
from app.models.core_min import Player, Team
from app.models.season_stats import TeamSeasonStats

def _bootstrap():
    """Create minimal test data."""
    engine = get_engine()
    with Session(engine) as session:
        # Create team
        team = Team(abbrev="TEST", name="Test Team")
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

def test_save_list_rename_delete():
    """Test save slot management functionality."""
    _bootstrap()
    engine = get_engine()
    
    with Session(engine) as session:
        # Export compressed save
        res = export_league_to_json(session, "slotA", season=2025, out_dir=Path("data/saves"), compress=True)
        assert Path(res["path"]).exists()
        assert res["compressed"] == True
        
        # Import compressed save
        import_res = import_league_from_json(session, Path(res["path"]), strategy="replace")
        assert "sha256" in import_res
        assert import_res["sha256"] == res["sha256"]  # Checksum should match
        
        # List saves
        items = list_saves(Path("data/saves"))
        assert any(i["name"] == "slotA" for i in items)
        slot_a = next(i for i in items if i["name"] == "slotA")
        assert slot_a["compressed"] == True
        assert slot_a["bytes"] > 0
        
        # Rename save
        rename_res = rename_save(session, "slotA", "slotB", out_dir=Path("data/saves"))
        assert rename_res["old"] == "slotA"
        assert rename_res["new"] == "slotB"
        assert "slotB" in rename_res["path"]
        
        # Verify rename worked
        items_after_rename = list_saves(Path("data/saves"))
        assert not any(i["name"] == "slotA" for i in items_after_rename)
        assert any(i["name"] == "slotB" for i in items_after_rename)
        
        # Delete save
        delete_res = delete_save(session, "slotB", out_dir=Path("data/saves"))
        assert delete_res["deleted"] == "slotB"
        assert "slotB" in delete_res["path"]
        
        # Verify delete worked
        items_after_delete = list_saves(Path("data/saves"))
        assert not any(i["name"] == "slotB" for i in items_after_delete)

def test_compressed_roundtrip():
    """Test compressed save/load roundtrip."""
    _bootstrap()
    engine = get_engine()
    
    with Session(engine) as session:
        # Export uncompressed
        res1 = export_league_to_json(session, "uncompressed", season=2025, out_dir=Path("data/saves"), compress=False)
        assert res1["compressed"] == False
        assert Path(res1["path"]).exists()
        
        # Export compressed
        res2 = export_league_to_json(session, "compressed", season=2025, out_dir=Path("data/saves"), compress=True)
        assert res2["compressed"] == True
        assert Path(res2["path"]).exists()
        
        # Verify compressed file is smaller
        uncompressed_size = Path(res1["path"]).stat().st_size
        compressed_size = Path(res2["path"]).stat().st_size
        assert compressed_size < uncompressed_size
        
        # Test loading both
        import1 = import_league_from_json(session, Path(res1["path"]), strategy="replace")
        import2 = import_league_from_json(session, Path(res2["path"]), strategy="replace")
        
        # Both should have same checksum (same data)
        assert import1["sha256"] == import2["sha256"]
        assert import1["counts"] == import2["counts"]

def test_list_saves_structure():
    """Test that list_saves returns correct structure."""
    _bootstrap()
    engine = get_engine()
    
    with Session(engine) as session:
        # Create both compressed and uncompressed saves
        export_league_to_json(session, "test1", season=2025, out_dir=Path("data/saves"), compress=False)
        export_league_to_json(session, "test2", season=2025, out_dir=Path("data/saves"), compress=True)
        
        items = list_saves(Path("data/saves"))
        
        # Should have at least 2 items
        assert len(items) >= 2
        
        # Check structure
        for item in items:
            assert "name" in item
            assert "path" in item
            assert "compressed" in item
            assert "bytes" in item
            assert isinstance(item["name"], str)
            assert isinstance(item["path"], str)
            assert isinstance(item["compressed"], bool)
            assert isinstance(item["bytes"], int)
            assert item["bytes"] > 0

def test_error_handling():
    """Test error handling for invalid operations."""
    engine = get_engine()
    
    with Session(engine) as session:
        # Test rename non-existent save
        try:
            rename_save(session, "nonexistent", "new_name", out_dir=Path("data/saves"))
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "nonexistent" in str(e)
        
        # Test delete non-existent save
        try:
            delete_save(session, "nonexistent", out_dir=Path("data/saves"))
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "nonexistent" in str(e)
