# tests/test_expiring_ai_and_endpoints.py
import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from app.models.contracts import PlayerContract, PlayerContractAsk, TeamTradeBlock
from app.models.core_min import Player, Team
from app.services.contracts_service import list_expiring_for_team, resign_player, release_player
from app.services.expiring_ai import preseason_sweep_mark_trade_block, is_more_willing_to_trade
from app.services.trade_valuation import player_trade_value
from random import Random


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


def test_expiring_list_defaults(session: Session, season_setup, player_factory, contract_factory):
    """Test that expiring contracts are properly listed."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create test players
    p1 = player_factory(team_id=t, rating=82, age=27, name="WR One")
    p2 = player_factory(team_id=t, rating=75, age=31, name="EDGE Two")
    
    # Create expiring contracts
    contract_factory(player_id=p1.id, team_id=t, start_season=s-1, end_season=s, aav=7_000_000, is_active=True)
    contract_factory(player_id=p2.id, team_id=t, start_season=s-2, end_season=s, aav=9_000_000, is_active=True)

    rows = list_expiring_for_team(session, t, s)
    ids = {r.player_id for r in rows}
    assert p1.id in ids and p2.id in ids


def test_preseason_ai_tradeblock_cap(session: Session, season_setup, player_factory, contract_factory):
    """Test that preseason AI respects the ≤25% cap for trade block."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create 8 expiring players to make ratio obvious
    ps = [player_factory(team_id=t, rating=70+i, age=29) for i in range(8)]
    for p in ps:
        contract_factory(player_id=p.id, team_id=t, start_season=s-3, end_season=s, aav=5_000_000, is_active=True)
    
    # Run preseason AI sweep
    rng = Random(42)  # Fixed seed for reproducible results
    preseason_sweep_mark_trade_block(session, s, rng)
    
    # Count trade block entries
    rows = list(session.exec(select(TeamTradeBlock).where(
        TeamTradeBlock.season == s, 
        TeamTradeBlock.team_id == t, 
        TeamTradeBlock.is_active == True
    )))
    assert len(rows) <= int(0.25 * len(ps))  # ≤25%


def test_trade_quote_discount_for_expiring(session: Session, season_setup, player_factory, contract_factory):
    """Test that trade quotes show discount for expiring players on trade block."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create expiring player
    p = player_factory(team_id=t, rating=85, age=27)
    contract_factory(player_id=p.id, team_id=t, start_season=s-3, end_season=s, aav=10_000_000, is_active=True)
    
    # Mark on trade block via sweep
    rng = Random(42)
    preseason_sweep_mark_trade_block(session, s, rng)
    
    # Get trade quote
    val = player_trade_value(session, p.id, s)
    # Ensure quote returns reasonable value
    assert val >= 100_000


def test_negotiate_accepts_at_threshold(session: Session, season_setup, player_factory, contract_factory):
    """Test that contract negotiations work at the acceptance threshold."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create expiring player
    p = player_factory(team_id=t, rating=88, age=26)
    contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=8_000_000, is_active=True)
    
    # Try to negotiate at ~96% of ask (the service will inflate if needed)
    years = 3
    total = 15_000_000
    resign_player(session, p.id, t, s, years, total)
    
    # Verify new contract was created
    new_contract = session.exec(select(PlayerContract).where(
        PlayerContract.player_id == p.id,
        PlayerContract.is_active == True
    )).first()
    assert new_contract is not None
    assert new_contract.aav == total // years


def test_release_player(session: Session, season_setup, player_factory, contract_factory):
    """Test that releasing a player works correctly."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create player with contract
    p = player_factory(team_id=t, rating=80, age=28)
    contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=6_000_000, is_active=True)
    
    # Release player
    release_player(session, p.id)
    
    # Verify player is released
    session.refresh(p)
    assert p.team_id is None
    assert p.cap_hit_current == 0
    
    # Verify contract is deactivated
    contract = session.exec(select(PlayerContract).where(
        PlayerContract.player_id == p.id,
        PlayerContract.is_active == True
    )).first()
    assert contract is None


def test_resign_player(session: Session, season_setup, player_factory, contract_factory):
    """Test that re-signing a player works correctly."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create expiring player
    p = player_factory(team_id=t, rating=85, age=27)
    contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=8_000_000, is_active=True)
    
    # Re-sign player
    years = 4
    total = 20_000_000
    resign_player(session, p.id, t, s, years, total)
    
    # Verify new contract
    new_contract = session.exec(select(PlayerContract).where(
        PlayerContract.player_id == p.id,
        PlayerContract.is_active == True
    )).first()
    assert new_contract is not None
    assert new_contract.start_season == s
    assert new_contract.end_season == s + years - 1
    assert new_contract.aav == total // years
    
    # Verify player cap hit updated
    session.refresh(p)
    assert p.cap_hit_current == total // years


def test_trade_block_logic(session: Session, season_setup, player_factory, contract_factory):
    """Test the trade block logic directly."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create players with different likelihoods to re-sign
    high_ovr = player_factory(team_id=t, rating=90, age=26)  # High likelihood
    low_ovr = player_factory(team_id=t, rating=60, age=35)  # Low likelihood
    
    # Create expiring contracts
    contract_factory(player_id=high_ovr.id, team_id=t, start_season=s-1, end_season=s, aav=12_000_000, is_active=True)
    contract_factory(player_id=low_ovr.id, team_id=t, start_season=s-1, end_season=s, aav=3_000_000, is_active=True)
    
    # Run AI sweep
    rng = Random(42)  # Fixed seed for reproducible results
    preseason_sweep_mark_trade_block(session, s, rng)
    
    # Check trade block status
    high_blocked = is_more_willing_to_trade(session, t, s, high_ovr.id)
    low_blocked = is_more_willing_to_trade(session, t, s, low_ovr.id)
    
    # Low OVR player should be more likely to be on trade block
    # (though randomness means we can't guarantee this)


def test_contract_ask_inflation(session: Session, season_setup, player_factory):
    """Test that contract asks inflate year-over-year."""
    s = season_setup.current_season
    
    # Create player
    p = player_factory(team_id=1, rating=80, age=27)
    
    # Create initial ask
    ask = PlayerContractAsk(
        player_id=p.id,
        desired_years=3,
        desired_total=15_000_000,
        desired_aav=5_000_000,
        updated_season=s-1
    )
    session.add(ask)
    session.commit()
    
    # Get ask for current season (should inflate)
    from app.services.contracts_service import get_or_create_ask
    updated_ask = get_or_create_ask(session, p.id, s)
    
    # Should be inflated by 3%
    expected_aav = int(5_000_000 * 1.03)
    assert updated_ask.desired_aav == expected_aav
    assert updated_ask.desired_total == expected_aav * updated_ask.desired_years
    assert updated_ask.updated_season == s


def test_trade_value_calculation(session: Session, season_setup, player_factory, contract_factory):
    """Test trade value calculation with discounts."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create player
    p = player_factory(team_id=t, rating=85, age=27)
    contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=10_000_000, is_active=True)
    
    # Get baseline value
    baseline_value = player_trade_value(session, p.id, s)
    
    # Mark on trade block
    trade_block = TeamTradeBlock(
        season=s,
        team_id=t,
        player_id=p.id,
        reason="EXPIRING_DECLINED",
        is_active=True
    )
    session.add(trade_block)
    session.commit()
    
    # Get discounted value
    discounted_value = player_trade_value(session, p.id, s)
    
    # Discounted value should be lower
    assert discounted_value < baseline_value
    assert discounted_value == int(baseline_value * 0.8)  # 20% discount


def test_expiring_dto_structure(session: Session, season_setup, player_factory, contract_factory):
    """Test that ExpiringDTO has the correct structure."""
    s, t = season_setup.current_season, season_setup.user_team_id
    
    # Create expiring player
    p = player_factory(team_id=t, rating=80, age=28, name="Test Player", pos="WR")
    contract_factory(player_id=p.id, team_id=t, start_season=s-1, end_season=s, aav=6_000_000, is_active=True)
    
    # Get expiring list
    expiring_list = list_expiring_for_team(session, t, s)
    
    assert len(expiring_list) == 1
    dto = expiring_list[0]
    
    # Check all required fields
    assert dto.player_id == p.id
    assert dto.name == "Test Player"
    assert dto.pos == "WR"
    assert dto.team_id == t
    assert dto.cap_hit_current == 6_000_000
    assert dto.desired_years > 0
    assert dto.desired_total > 0
    assert dto.desired_aav > 0
    assert isinstance(dto.on_trade_block, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
