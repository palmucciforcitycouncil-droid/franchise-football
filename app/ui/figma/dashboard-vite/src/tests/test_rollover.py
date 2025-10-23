# tests/test_rollover.py
from sqlmodel import Session, select
from app.db import get_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season
from app.services.awards import compute_and_persist_awards
from app.services.progression import apply_progression_for_season
from app.services.rollover import apply_season_rollover
from app.models.rollover import RolloverAudit

def _bootstrap(season:int):
    with memory_db() as session:
        run_mini_season(session, weeks=1)
        session.commit()
    with memory_db() as session:
        aggregate_team_season(session, season)
        aggregate_player_season(session, season)
        compute_and_persist_awards(session, season)
        apply_progression_for_season(session, season=season, seed=2025, force=True)

def test_rollover_idempotent():
    """Test that rollover is idempotent and creates audit records."""
    from_season, to_season = 2025, 2026
    _bootstrap(from_season)
    
    with memory_db() as session:
        res1 = apply_season_rollover(session, from_season, to_season, seed=2025, force=False)
        assert res1.get("status") in {"ok","skipped"}
        res2 = apply_season_rollover(session, from_season, to_season, seed=2025, force=False)
        assert res2["status"] == "skipped"
    
    with memory_db() as session:
        a = session.exec(select(RolloverAudit).where(RolloverAudit.from_season==from_season, RolloverAudit.to_season==to_season)).first()
        assert a is not None

def test_rollover_ages_players():
    """Test that rollover ages players and increments years_pro."""
    from_season, to_season = 2025, 2026
    _bootstrap(from_season)
    
    with memory_db() as session:
        from app.models.core_min import Player
        # Get a player before rollover
        player = session.exec(select(Player)).first()
        assert player is not None
        
        original_age = getattr(player, "age", 0)
        original_years_pro = getattr(player, "years_pro", 0)
        
        # Apply rollover
        result = apply_season_rollover(session, from_season, to_season, seed=2025, force=True)
        assert result["status"] == "ok"
        
        # Check that player was aged
        session.refresh(player)
        new_age = getattr(player, "age", 0)
        new_years_pro = getattr(player, "years_pro", 0)
        
        assert new_age == original_age + 1, f"Age not incremented: {original_age} -> {new_age}"
        assert new_years_pro == original_years_pro + 1, f"Years pro not incremented: {original_years_pro} -> {new_years_pro}"

def test_rollover_retirement_logic():
    """Test that retirement logic works correctly."""
    from_season, to_season = 2025, 2026
    _bootstrap(from_season)
    
    with memory_db() as session:
        from app.models.core_min import Player
        
        # Create an old player that should retire
        old_player = Player(
            first_name="Old",
            last_name="Player",
            pos="QB",
            name="Old Player",
            age=35,  # Should retire
            years_pro=10,
            awareness=80,
            speed=70,
            strength=70,
            agility=70,
            throw_power=80,
            throw_accuracy=80,
            catching=50,
            tackling=50,
            stamina=60,
            morale=60,
            injury_proneness=50,
            potential=50,
            team_id=1
        )
        session.add(old_player)
        session.commit()
        
        # Apply rollover
        result = apply_season_rollover(session, from_season, to_season, seed=2025, force=True)
        assert result["status"] == "ok"
        assert result["retired_count"] > 0, "Should have retired at least one player"
        
        # Check that old player was retired
        session.refresh(old_player)
        assert getattr(old_player, "team_id", None) is None, "Retired player should have team_id=None"
        assert getattr(old_player, "morale", 0) == 50, "Retired player should have morale=50"
        assert getattr(old_player, "stamina", 0) == 50, "Retired player should have stamina=50"

def test_rollover_recovery():
    """Test that rollover applies recovery to stamina and morale."""
    from_season, to_season = 2025, 2026
    _bootstrap(from_season)
    
    with memory_db() as session:
        from app.models.core_min import Player
        
        # Create a player with low stamina/morale
        tired_player = Player(
            first_name="Tired",
            last_name="Player",
            pos="RB",
            name="Tired Player",
            age=25,
            years_pro=3,
            awareness=70,
            speed=80,
            strength=70,
            agility=80,
            throw_power=50,
            throw_accuracy=50,
            catching=60,
            tackling=50,
            stamina=30,  # Low stamina
            morale=30,  # Low morale
            injury_proneness=50,
            potential=70,
            team_id=1
        )
        session.add(tired_player)
        session.commit()
        
        original_stamina = getattr(tired_player, "stamina", 0)
        original_morale = getattr(tired_player, "morale", 0)
        
        # Apply rollover
        result = apply_season_rollover(session, from_season, to_season, seed=2025, force=True)
        assert result["status"] == "ok"
        
        # Check that stamina and morale were improved
        session.refresh(tired_player)
        new_stamina = getattr(tired_player, "stamina", 0)
        new_morale = getattr(tired_player, "morale", 0)
        
        assert new_stamina > original_stamina, f"Stamina should improve: {original_stamina} -> {new_stamina}"
        assert new_morale > original_morale, f"Morale should improve: {original_morale} -> {new_morale}"

def test_rollover_force_recompute():
    """Test that force=True allows recomputation."""
    from_season, to_season = 2027, 2028
    _bootstrap(from_season)
    
    with memory_db() as session:
        # First rollover
        res1 = apply_season_rollover(session, from_season, to_season, seed=2025, force=False)
        assert res1["status"] == "ok"
        
        # Second rollover without force should be skipped
        res2 = apply_season_rollover(session, from_season, to_season, seed=2025, force=False)
        assert res2["status"] == "skipped"
        
        # Third rollover with force should work
        res3 = apply_season_rollover(session, from_season, to_season, seed=2025, force=True)
        assert res3["status"] == "ok"
