import pytest
from sqlmodel import SQLModel

def test_players_table_defined_once():
    """Test that the 'players' table is defined exactly once in SQLModel metadata."""
    # Import both models to ensure they're registered
    from app.models.core_min import Player as CorePlayer
    from app.models.player_models import Player as LegacyPlayer
    
    # SQLModel metadata keeps tables by name.
    # There should be exactly one "players" table registered.
    names = list(SQLModel.metadata.tables.keys())
    assert names.count("players") == 1, f"players defined {names.count('players')} times: {names}"

def test_legacy_player_is_dto_only():
    """Test that legacy Player model is DTO-only and doesn't register a table."""
    from app.models.player_models import Player as LegacyPlayer
    
    # Legacy Player should not register a table
    assert LegacyPlayer.__table__ is None, "Legacy Player should not have a table"
    
    # Legacy Player should be DTO-only (no table registration)
    # This is verified by the fact that we can import both models without conflict

def test_core_player_owns_table():
    """Test that core Player model owns the 'players' table."""
    from app.models.core_min import Player as CorePlayer
    
    # Core Player should be registered as a table
    assert CorePlayer.__tablename__ == "players"
    assert CorePlayer.__table__ is not None
