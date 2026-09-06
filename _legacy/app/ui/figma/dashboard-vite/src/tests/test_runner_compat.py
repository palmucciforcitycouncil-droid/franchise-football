import pytest
from sqlmodel import select
from scripts.micro_seed import ensure_tables, seed_min
from sqlmodel import create_engine, Session

def test_runner_uses_core_models_and_writes_teamgames():
    """Test that runner uses core models and can write scoring to TeamGame."""
    eng = create_engine("sqlite:///franchise.db", future=True)
    ensure_tables(eng)
    seed_min(eng)
    
    with Session(eng) as s:
        # Import via core_min to ensure table shape is as expected
        from app.models.core_min import Team, Game, TeamGame, Player
        
        # Tables exist
        assert s.exec(select(Team)).first() is not None
        assert s.exec(select(Game)).first() is not None
        assert s.exec(select(Player)).first() is not None
        
        # Test Player compatibility aliases
        player = s.exec(select(Player)).first()
        assert player.pos == player.position  # alias works
        assert player.name == player.full_name  # alias works
        
        # Test setting via aliases
        player.position = "QB"
        assert player.pos == "QB"
        player.full_name = "Test Player"
        assert player.name == "Test Player"
        
        # Simulate a trivial scoring write (acts like a TD)
        from app.engine.scoring import apply_touchdown
        g = s.exec(select(Game)).first()
        home_team_id = g.home_team_id
        apply_touchdown(s, game_id=g.id, off_team_id=home_team_id)
        
        tg = s.exec(select(TeamGame).where(TeamGame.game_id==g.id, TeamGame.team_id==home_team_id)).first()
        assert tg is not None
        assert (getattr(tg, "points", 0) or 0) >= 6
