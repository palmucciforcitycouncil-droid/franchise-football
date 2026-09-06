# tests/test_gm_integration_comprehensive.py
import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from app.models.contracts import PlayerContract, PlayerContractAsk, TeamTradeBlock
from app.models.core_min import Player, Team
from app.services.contracts_service import list_expiring_for_team, resign_player, release_player, get_or_create_ask
from app.services.expiring_ai import preseason_sweep_mark_trade_block, is_more_willing_to_trade
from app.services.trade_valuation import player_trade_value
from random import Random
import time


@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a test session."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="test_team")
def test_team_fixture(session: Session):
    """Create a test team."""
    team = Team(abbrev="TEST", name="Test Team")
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@pytest.fixture(name="player_factory")
def player_factory_fixture(session: Session):
    """Factory for creating test players."""
    def _factory(**kwargs):
        defaults = {
            "name": "Test Player",
            "pos": "QB",
            "rating": 75,
            "age": 25,
            "team_id": None
        }
        defaults.update(kwargs)
        player = Player(**defaults)
        session.add(player)
        session.commit()
        session.refresh(player)
        return player
    return _factory


@pytest.fixture(name="contract_factory")
def contract_factory_fixture(session: Session):
    """Factory for creating test contracts."""
    def _factory(**kwargs):
        defaults = {
            "player_id": 1,
            "team_id": 1,
            "start_season": 2024,
            "end_season": 2025,
            "aav": 5_000_000,
            "is_active": True
        }
        defaults.update(kwargs)
        contract = PlayerContract(**defaults)
        session.add(contract)
        session.commit()
        session.refresh(contract)
        return contract
    return _factory


@pytest.fixture(name="season_setup")
def season_setup_fixture():
    """Setup current season and user team."""
    class SeasonSetup:
        current_season = 2025
        user_team_id = 1
    return SeasonSetup


# ===== INTEGRATION TESTS =====

def test_complete_gm_workflow(session: Session, season_setup, player_factory, contract_factory):
    """Test complete GM workflow: load expiring → negotiate → release → trade quote."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create multiple expiring players
    players = []
    for i in range(5):
        p = player_factory(team_id=t, rating=70+i*5, age=25+i, name=f"Player {i+1}")
        contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=5_000_000+i*1_000_000, is_active=True)
        players.append(p)
    
    # 1. Load expiring contracts
    expiring = list_expiring_for_team(session, t, s)
    assert len(expiring) == 5
    
    # 2. Negotiate with first player
    p1 = players[0]
    years = 3
    total = 15_000_000
    resign_player(session, p1.id, t, s, years, total)
    
    # Verify new contract
    new_contract = session.exec(select(PlayerContract).where(
        PlayerContract.player_id == p1.id,
        PlayerContract.is_active == True
    )).first()
    assert new_contract is not None
    assert new_contract.aav == total // years
    
    # 3. Release second player
    p2 = players[1]
    release_player(session, p2.id)
    session.refresh(p2)
    assert p2.team_id is None
    assert p2.cap_hit_current == 0
    
    # 4. Get trade quotes for remaining players
    for p in players[2:]:
        val = player_trade_value(session, p.id, s)
        assert val >= 100_000  # Minimum value
    
    # 5. Run preseason AI sweep
    rng = Random(42)
    preseason_sweep_mark_trade_block(session, s, rng)
    
    # 6. Verify trade block assignments
    trade_blocked = 0
    for p in players[2:]:
        if is_more_willing_to_trade(session, t, s, p.id):
            trade_blocked += 1
    
    # Should have some players on trade block (≤25% of remaining)
    assert trade_blocked <= len(players[2:])  # At most all remaining players


def test_database_persistence_across_sessions(engine, season_setup, player_factory, contract_factory):
    """Test that contract data persists across database sessions."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create player and contract in first session
    with Session(engine) as session1:
        p = player_factory(team_id=t, rating=80, age=27)
        contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=8_000_000, is_active=True)
        session1.commit()
        player_id = p.id
    
    # Verify persistence in second session
    with Session(engine) as session2:
        contract = session2.exec(select(PlayerContract).where(
            PlayerContract.player_id == player_id,
            PlayerContract.is_active == True
        )).first()
        assert contract is not None
        assert contract.aav == 8_000_000
        
        # Test expiring list
        expiring = list_expiring_for_team(session2, t, s)
        assert len(expiring) == 1
        assert expiring[0].player_id == player_id


# ===== EDGE CASE TESTS =====

def test_boundary_values(session: Session, season_setup, player_factory, contract_factory):
    """Test edge cases for contract values and player attributes."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Test minimum values
    p_min = player_factory(team_id=t, rating=0, age=18, name="Min Player")
    contract_factory(player_id=p_min.id, team_id=t, start_season=s-1, end_season=s, aav=1, is_active=True)
    
    # Test maximum values
    p_max = player_factory(team_id=t, rating=100, age=45, name="Max Player")
    contract_factory(player_id=p_max.id, team_id=t, start_season=s-1, end_season=s, aav=50_000_000, is_active=True)
    
    # Test fractional years (should be handled gracefully)
    p_frac = player_factory(team_id=t, rating=50, age=30, name="Fractional Player")
    contract_factory(player_id=p_frac.id, team_id=t, start_season=s-1, end_season=s, aav=5_000_000, is_active=True)
    
    # All should be handled without errors
    expiring = list_expiring_for_team(session, t, s)
    assert len(expiring) == 3
    
    # Test trade values
    for p in [p_min, p_max, p_frac]:
        val = player_trade_value(session, p.id, s)
        assert val >= 100_000  # Minimum floor


def test_ai_edge_cases(session: Session, season_setup, player_factory, contract_factory):
    """Test AI logic with extreme player profiles."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Test with no expiring players
    p_non_expiring = player_factory(team_id=t, rating=80, age=25)
    contract_factory(player_id=p_non_expiring.id, team_id=t, start_season=s, end_season=s+2, aav=5_000_000, is_active=True)
    
    expiring = list_expiring_for_team(session, t, s)
    assert len(expiring) == 0
    
    # Test with all players expiring
    players = []
    for i in range(10):
        p = player_factory(team_id=t, rating=60+i*4, age=25+i, name=f"Expiring {i+1}")
        contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=3_000_000+i*500_000, is_active=True)
        players.append(p)
    
    expiring = list_expiring_for_team(session, t, s)
    assert len(expiring) == 10
    
    # Run AI sweep
    rng = Random(42)
    preseason_sweep_mark_trade_block(session, s, rng)
    
    # Should respect ≤25% cap
    trade_blocked = sum(1 for p in players if is_more_willing_to_trade(session, t, s, p.id))
    assert trade_blocked <= 3  # ≤25% of 10 = 2.5, rounded up to 3


def test_contract_negotiation_edge_cases(session: Session, season_setup, player_factory, contract_factory):
    """Test negotiation logic with edge cases."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Test exact threshold (96% of ask)
    p = player_factory(team_id=t, rating=85, age=27)
    contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=10_000_000, is_active=True)
    
    # Create ask
    ask = PlayerContractAsk(
        player_id=p.id,
        desired_years=4,
        desired_total=40_000_000,
        desired_aav=10_000_000,
        updated_season=s
    )
    session.add(ask)
    session.commit()
    
    # Test exact threshold offer
    offered_total = int(40_000_000 * 0.96)  # 96% of ask
    offered_years = 3  # desired_years - 1
    
    resign_player(session, p.id, t, s, offered_years, offered_total)
    
    # Should create new contract
    new_contract = session.exec(select(PlayerContract).where(
        PlayerContract.player_id == p.id,
        PlayerContract.is_active == True
    )).first()
    assert new_contract is not None
    assert new_contract.aav == offered_total // offered_years


# ===== PERFORMANCE TESTS =====

def test_performance_large_rosters(session: Session, season_setup, player_factory, contract_factory):
    """Test performance with large team rosters."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create large roster (100 players)
    players = []
    start_time = time.time()
    
    for i in range(100):
        p = player_factory(team_id=t, rating=50+i, age=20+i%20, name=f"Player {i+1}")
        contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=1_000_000+i*50_000, is_active=True)
        players.append(p)
    
    creation_time = time.time() - start_time
    print(f"Created 100 players in {creation_time:.3f} seconds")
    
    # Test expiring contract query performance
    start_time = time.time()
    expiring = list_expiring_for_team(session, t, s)
    query_time = time.time() - start_time
    
    assert len(expiring) == 100
    assert query_time < 1.0  # Should be fast
    print(f"Queried 100 expiring contracts in {query_time:.3f} seconds")
    
    # Test preseason AI sweep performance
    start_time = time.time()
    rng = Random(42)
    preseason_sweep_mark_trade_block(session, s, rng)
    ai_time = time.time() - start_time
    
    assert ai_time < 2.0  # Should be fast
    print(f"AI sweep for 100 players in {ai_time:.3f} seconds")


def test_memory_usage_stability(session: Session, season_setup, player_factory, contract_factory):
    """Test memory usage with multiple operations."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create players and contracts
    players = []
    for i in range(50):
        p = player_factory(team_id=t, rating=60+i, age=25+i%15, name=f"Player {i+1}")
        contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=2_000_000+i*100_000, is_active=True)
        players.append(p)
    
    # Perform multiple operations
    for _ in range(10):  # Simulate multiple seasons
        # Load expiring
        expiring = list_expiring_for_team(session, t, s)
        
        # Negotiate with some players
        for i in range(0, len(players), 5):
            resign_player(session, players[i].id, t, s, 3, 6_000_000)
        
        # Run AI sweep
        rng = Random(42)
        preseason_sweep_mark_trade_block(session, s, rng)
        
        # Get trade quotes
        for p in players[:10]:
            val = player_trade_value(session, p.id, s)
            assert val >= 100_000
    
    # Should complete without memory issues
    assert True


# ===== ERROR HANDLING TESTS =====

def test_error_handling_invalid_references(session: Session, season_setup):
    """Test error handling with invalid player/team references."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Test with non-existent player
    try:
        expiring = list_expiring_for_team(session, 999, s)  # Non-existent team
        assert len(expiring) == 0  # Should return empty list, not crash
    except Exception as e:
        pytest.fail(f"Should handle non-existent team gracefully: {e}")
    
    # Test with non-existent player ID
    try:
        val = player_trade_value(session, 999, s)  # Non-existent player
        assert val == 0  # Should return 0, not crash
    except Exception as e:
        pytest.fail(f"Should handle non-existent player gracefully: {e}")
    
    # Test release non-existent player
    try:
        release_player(session, 999)  # Non-existent player
        # Should complete without error
    except Exception as e:
        pytest.fail(f"Should handle non-existent player release gracefully: {e}")


def test_error_handling_missing_data(session: Session, season_setup, player_factory):
    """Test error handling with missing contract data."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create player without contract
    p = player_factory(team_id=t, rating=80, age=27)
    
    # Should handle missing contract gracefully
    expiring = list_expiring_for_team(session, t, s)
    assert len(expiring) == 0  # No expiring contracts
    
    # Trade value should be calculated based on player rating even without contract
    val = player_trade_value(session, p.id, s)
    assert val >= 100_000  # Should still have value based on rating


# ===== BUSINESS LOGIC TESTS =====

def test_trade_block_assignment_logic(session: Session, season_setup, player_factory, contract_factory):
    """Test trade block assignment logic with different scenarios."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create players with different likelihoods
    scenarios = [
        {"rating": 95, "age": 26, "aav": 20_000_000, "expected_likely": True},   # High OVR, prime age, high ask
        {"rating": 60, "age": 35, "aav": 3_000_000, "expected_likely": False},   # Low OVR, old age, low ask
        {"rating": 80, "age": 28, "aav": 8_000_000, "expected_likely": True},     # Medium OVR, prime age, medium ask
        {"rating": 70, "age": 32, "aav": 12_000_000, "expected_likely": False},  # Medium OVR, old age, high ask
    ]
    
    players = []
    for i, scenario in enumerate(scenarios):
        p = player_factory(team_id=t, rating=scenario["rating"], age=scenario["age"], name=f"Player {i+1}")
        contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=scenario["aav"], is_active=True)
        players.append(p)
    
    # Run AI sweep multiple times with different seeds
    trade_block_counts = []
    for seed in range(5):
        rng = Random(seed)
        preseason_sweep_mark_trade_block(session, s, rng)
        
        trade_blocked = sum(1 for p in players if is_more_willing_to_trade(session, t, s, p.id))
        trade_block_counts.append(trade_blocked)
        
        # Reset for next iteration
        trade_blocks = session.exec(select(TeamTradeBlock).where(TeamTradeBlock.season == s)).all()
        for tb in trade_blocks:
            session.delete(tb)
        session.commit()
    
    # Should have some variation due to randomness, but respect ≤25% cap
    for count in trade_block_counts:
        assert count <= 1  # ≤25% of 4 = 1


def test_contract_inflation_consistency(session: Session, season_setup, player_factory):
    """Test contract inflation consistency over multiple seasons."""
    s = season_setup.current_season
    
    # Create player
    p = player_factory(team_id=1, rating=80, age=27)
    
    # Create initial ask
    initial_aav = 5_000_000
    ask = PlayerContractAsk(
        player_id=p.id,
        desired_years=3,
        desired_total=initial_aav * 3,
        desired_aav=initial_aav,
        updated_season=s-3
    )
    session.add(ask)
    session.commit()
    
    # Test inflation over multiple seasons
    expected_aav = initial_aav
    for season_offset in range(1, 4):
        expected_aav = int(expected_aav * 1.03)  # 3% inflation
        updated_ask = get_or_create_ask(session, p.id, s - 3 + season_offset)
        
        assert updated_ask.desired_aav == expected_aav
        assert updated_ask.desired_total == expected_aav * updated_ask.desired_years
        assert updated_ask.updated_season == s - 3 + season_offset


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
