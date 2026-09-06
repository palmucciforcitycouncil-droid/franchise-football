import pytest
from sqlmodel import select
from app.models.core_min import Team, Game, TeamGame, Player
from scripts.micro_seed import ensure_tables, seed_min
from sqlmodel import create_engine, Session

def test_seed_creates_rows_and_scoring_fields_exist():
    """Test that micro seed creates all necessary rows and fields."""
    eng = create_engine("sqlite:///franchise.db", future=True)
    ensure_tables(eng)
    seed_min(eng)
    
    with Session(eng) as s:
        # Check that all tables have data
        assert s.exec(select(Team)).first() is not None
        g = s.exec(select(Game)).all()
        assert g
        tg = s.exec(select(TeamGame)).all()
        assert tg
        p = s.exec(select(Player)).all()
        assert p
        
        # Check that scoring fields exist
        t0 = tg[0]
        _ = t0.points
        _ = t0.fga
        _ = t0.punts
        _ = t0.yards_total
        _ = t0.sacks_def
        
        # Check that kicker fields exist
        kicker = s.exec(select(Player).where(Player.pos == "K")).first()
        assert kicker is not None
        _ = kicker.kicker_power
        _ = kicker.kicker_base_40_49
