import pytest
from random import Random
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.contracts import PlayerContract, PlayerContractAsk, TeamTradeBlock
from app.services.expiring_contracts import (
    _current_contract, is_expiring_this_season, _position_multiplier,
    get_or_update_ask, list_team_expiring, make_resign_offer,
    cpu_preseason_contract_pass, get_trade_block_players,
    add_to_trade_block, remove_from_trade_block, get_contract_summary
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_expiring_list_and_resign_flow(client, seeded_db, season_setup):
    """Test expiring contracts list and resign flow."""
    s = season_setup.current_season
    
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.player import Player
    from app.models.contracts import PlayerContract
    
    with Session(get_engine()) as sess:
        p = Player(name="WR ContractYear", team_id=1, pos="WR", age=27, overall=82, cap_hit=4500000)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        
        sess.add(PlayerContract(
            player_id=p.player_id, 
            team_id=1, 
            start_season=s-2, 
            end_season=s, 
            aav=4500000, 
            is_active=True
        ))
        sess.commit()
    
    # List expiring contracts
    r = client.get(f"/api/v1/contracts/expiring?team_id=1&season={s}")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1 and rows[0]["player_id"] > 0
    
    # Make resign offer
    pid = rows[0]["player_id"]
    ask_aav = rows[0]["ask_aav"]
    ask_years = rows[0]["ask_years"]
    
    offer = {
        "season": s, 
        "team_id": 1, 
        "player_id": pid, 
        "years": max(1, ask_years-0), 
        "aav": int(ask_aav*1.00)
    }
    
    r = client.post("/api/v1/contracts/resign", json=offer)
    assert r.status_code == 200
    resp = r.json()
    
    # May accept or point to min thresholds; at least the fields exist
    assert "min_years" in resp and "min_aav" in resp

def test_cpu_preseason_cap_25_percent_trade_block(client, seeded_db, season_setup):
    """Test CPU preseason with 25% cap on trade block."""
    s = season_setup.current_season
    
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.player import Player
    from app.models.contracts import PlayerContract, TeamTradeBlock
    
    with Session(get_engine()) as sess:
        # Seed a team with 8 expiring mid-tier players
        for i in range(8):
            p = Player(
                name=f"Exp{i}", 
                team_id=2, 
                pos="LB", 
                age=29, 
                overall=72+i, 
                cap_hit=2000000+i*50000
            )
            sess.add(p)
            sess.commit()
            sess.refresh(p)
            
            sess.add(PlayerContract(
                player_id=p.player_id, 
                team_id=2, 
                start_season=s-1, 
                end_season=s, 
                aav=2000000, 
                is_active=True
            ))
        sess.commit()
    
    r = client.post("/api/v1/contracts/cpu/preseason_pass", json={
        "season": s, 
        "team_id": 2, 
        "seed": 999
    })
    assert r.status_code == 200
    data = r.json()
    
    # Ensure trade block is a subset of unlikely and capped at 25%
    assert set(data["trade_block_ids"]).issubset(set(data["unlikely_ids"]))
    assert len(data["trade_block_ids"]) <= int(len(data["unlikely_ids"]) * 0.25 + 1e-9)

def test_trade_block_endpoint(client, seeded_db, season_setup):
    """Test trade block endpoint."""
    s = season_setup.current_season
    
    r = client.get(f"/api/v1/contracts/trade_block_ids?season={s}&team_id=2")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_position_multiplier():
    """Test position multiplier calculations."""
    assert _position_multiplier("QB") == 2.0
    assert _position_multiplier("WR") == 1.25
    assert _position_multiplier("RB") == 0.8
    assert _position_multiplier("K") == 0.5
    assert _position_multiplier("UNKNOWN") == 1.0

def test_current_contract(session: Session):
    """Test current contract retrieval."""
    # Create test contract
    contract = PlayerContract(
        player_id=12345,
        team_id=1,
        start_season=2022,
        end_season=2024,
        aav=5000000,
        is_active=True
    )
    session.add(contract)
    session.commit()
    
    # Test retrieval
    current = _current_contract(session, 12345)
    assert current is not None
    assert current.player_id == 12345
    assert current.is_active is True
    
    # Test inactive contract
    contract.is_active = False
    session.add(contract)
    session.commit()
    
    current = _current_contract(session, 12345)
    assert current is None

def test_is_expiring_this_season():
    """Test expiring contract detection."""
    contract = PlayerContract(
        player_id=12345,
        team_id=1,
        start_season=2022,
        end_season=2024,
        aav=5000000,
        is_active=True
    )
    
    assert is_expiring_this_season(contract, 2024) is True
    assert is_expiring_this_season(contract, 2023) is False
    assert is_expiring_this_season(contract, 2025) is False
    
    # Test inactive contract
    contract.is_active = False
    assert is_expiring_this_season(contract, 2024) is False

def test_get_or_update_ask(session: Session):
    """Test contract ask creation and updating."""
    # Create mock player
    class MockPlayer:
        def __init__(self):
            self.player_id = 12345
            self.pos = "WR"
            self.age = 27
            self.overall = 80
    
    player = MockPlayer()
    
    # First call should create ask
    ask = get_or_update_ask(session, player, 2024)
    assert ask.player_id == 12345
    assert ask.desired_years > 0
    assert ask.desired_aav > 0
    assert ask.updated_season == 2024
    
    # Second call with same season should not update
    ask2 = get_or_update_ask(session, player, 2024)
    assert ask2.id == ask.id
    assert ask2.desired_years == ask.desired_years
    assert ask2.desired_aav == ask.desired_aav
    
    # Third call with new season should update
    ask3 = get_or_update_ask(session, player, 2025)
    assert ask3.id == ask.id
    assert ask3.updated_season == 2025

def test_list_team_expiring(session: Session):
    """Test listing team expiring contracts."""
    # Create mock player and contract
    class MockPlayer:
        def __init__(self):
            self.player_id = 12345
            self.name = "Test Player"
            self.pos = "WR"
            self.age = 27
            self.overall = 80
            self.team_id = 1
            self.cap_hit = 5000000
    
    # Create contract
    contract = PlayerContract(
        player_id=12345,
        team_id=1,
        start_season=2022,
        end_season=2024,
        aav=5000000,
        is_active=True
    )
    session.add(contract)
    session.commit()
    
    # Mock the Player query
    try:
        from app.models.player import Player
        player = Player(
            player_id=12345,
            name="Test Player",
            pos="WR",
            age=27,
            overall=80,
            team_id=1,
            cap_hit=5000000
        )
        session.add(player)
        session.commit()
        
        # Test listing
        expiring = list_team_expiring(session, 1, 2024)
        assert len(expiring) == 1
        assert expiring[0].player_id == 12345
        assert expiring[0].name == "Test Player"
        assert expiring[0].pos == "WR"
    except ImportError:
        # Skip if Player model doesn't exist
        assert True

def test_make_resign_offer(session: Session):
    """Test making resign offers."""
    # Create mock player and contract
    class MockPlayer:
        def __init__(self):
            self.player_id = 12345
            self.name = "Test Player"
            self.pos = "WR"
            self.age = 27
            self.overall = 80
            self.team_id = 1
    
    try:
        from app.models.player import Player
        player = Player(
            player_id=12345,
            name="Test Player",
            pos="WR",
            age=27,
            overall=80,
            team_id=1
        )
        session.add(player)
        session.commit()
        
        # Create expiring contract
        contract = PlayerContract(
            player_id=12345,
            team_id=1,
            start_season=2022,
            end_season=2024,
            aav=5000000,
            is_active=True
        )
        session.add(contract)
        session.commit()
        
        # Test successful offer
        result = make_resign_offer(session, 2024, 1, 12345, 3, 6000000)
        assert result.accepted is True
        assert result.min_years > 0
        assert result.min_aav > 0
        
        # Test failed offer
        result2 = make_resign_offer(session, 2024, 1, 12345, 1, 1000000)
        assert result2.accepted is False
        assert "Below threshold" in result2.reason
        
    except ImportError:
        # Skip if Player model doesn't exist
        assert True

def test_cpu_preseason_contract_pass(session: Session):
    """Test CPU preseason contract decisions."""
    try:
        from app.models.player import Player
        
        # Create test players
        players = []
        for i in range(5):
            player = Player(
                player_id=1000 + i,
                name=f"Player {i}",
                pos="WR",
                age=27,
                overall=75 + i,
                team_id=1
            )
            session.add(player)
            players.append(player)
        
        session.commit()
        
        # Create expiring contracts
        for i, player in enumerate(players):
            contract = PlayerContract(
                player_id=player.player_id,
                team_id=1,
                start_season=2022,
                end_season=2024,
                aav=3000000 + i * 500000,
                is_active=True
            )
            session.add(contract)
        
        session.commit()
        
        # Run CPU preseason pass
        decision = cpu_preseason_contract_pass(session, 2024, 1, 12345)
        
        assert len(decision.resign_ids) + len(decision.unlikely_ids) == 5
        assert len(decision.trade_block_ids) <= len(decision.unlikely_ids)
        assert len(decision.trade_block_ids) <= int(len(decision.unlikely_ids) * 0.25 + 1)
        
    except ImportError:
        # Skip if Player model doesn't exist
        assert True

def test_trade_block_management(session: Session):
    """Test trade block management."""
    # Add to trade block
    success = add_to_trade_block(session, 2024, 1, 12345, "Test reason")
    assert success is True
    
    # Try to add again (should fail)
    success2 = add_to_trade_block(session, 2024, 1, 12345, "Test reason")
    assert success2 is False
    
    # Get trade block players
    players = get_trade_block_players(session, 2024, 1)
    assert 12345 in players
    
    # Remove from trade block
    success3 = remove_from_trade_block(session, 2024, 1, 12345)
    assert success3 is True
    
    # Try to remove again (should fail)
    success4 = remove_from_trade_block(session, 2024, 1, 12345)
    assert success4 is False

def test_contract_summary(session: Session):
    """Test contract summary generation."""
    summary = get_contract_summary(session, 1, 2024)
    
    assert summary["team_id"] == 1
    assert summary["season"] == 2024
    assert "expiring_count" in summary
    assert "trade_block_count" in summary
    assert "total_ask_value" in summary
    assert "total_cap_hit" in summary

def test_api_endpoints(client, seeded_db):
    """Test various API endpoints."""
    # Test expiring contracts
    r = client.get("/api/v1/contracts/expiring?team_id=1&season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test trade block IDs
    r = client.get("/api/v1/contracts/trade_block_ids?season=2024&team_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test contract summary
    r = client.get("/api/v1/contracts/summary?team_id=1&season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "team_id" in data
    assert "season" in data
    
    # Test trade block details
    r = client.get("/api/v1/contracts/trade_block/details?season=2024&team_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test contract stats
    r = client.get("/api/v1/contracts/stats?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "total_expiring" in data
    assert "total_trade_block" in data

def test_trade_block_api(client, seeded_db):
    """Test trade block API endpoints."""
    # Add to trade block
    r = client.post("/api/v1/contracts/trade_block/add", json={
        "season": 2024,
        "team_id": 1,
        "player_id": 12345,
        "reason": "Test addition"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    
    # Remove from trade block
    r = client.post("/api/v1/contracts/trade_block/remove", json={
        "season": 2024,
        "team_id": 1,
        "player_id": 12345
    })
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True

def test_cpu_preseason_api(client, seeded_db):
    """Test CPU preseason API."""
    r = client.post("/api/v1/contracts/cpu/preseason_pass", json={
        "season": 2024,
        "team_id": 1,
        "seed": 12345
    })
    assert r.status_code == 200
    data = r.json()
    assert "resign_ids" in data
    assert "unlikely_ids" in data
    assert "trade_block_ids" in data

def test_bulk_cpu_preseason_api(client, seeded_db):
    """Test bulk CPU preseason API."""
    r = client.post("/api/v1/contracts/cpu/bulk_preseason_pass", json={
        "season": 2024,
        "team_ids": [1, 2, 3],
        "seed": 12345
    })
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert "total_resigned" in data
    assert "total_trade_block" in data
    assert len(data["results"]) == 3

def test_contract_history_api(client, seeded_db):
    """Test contract history API."""
    r = client.get("/api/v1/contracts/history/12345")
    assert r.status_code == 200
    data = r.json()
    assert "player_id" in data
    assert "contracts" in data
    assert isinstance(data["contracts"], list)

def test_resign_offer_api(client, seeded_db):
    """Test resign offer API."""
    r = client.post("/api/v1/contracts/resign", json={
        "season": 2024,
        "team_id": 1,
        "player_id": 12345,
        "years": 3,
        "aav": 5000000
    })
    assert r.status_code == 200
    data = r.json()
    assert "accepted" in data
    assert "min_years" in data
    assert "min_aav" in data

def test_error_handling(client, seeded_db):
    """Test error handling in API endpoints."""
    # Test invalid team ID
    r = client.get("/api/v1/contracts/expiring?team_id=999&season=2024")
    assert r.status_code == 200  # Should return empty list, not error
    
    # Test invalid season
    r = client.get("/api/v1/contracts/expiring?team_id=1&season=9999")
    assert r.status_code == 200  # Should return empty list, not error

def test_contract_models(session: Session):
    """Test contract model creation and validation."""
    # Test PlayerContract
    contract = PlayerContract(
        player_id=12345,
        team_id=1,
        start_season=2022,
        end_season=2024,
        aav=5000000,
        guaranteed=2000000,
        is_active=True
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    
    assert contract.contract_id is not None
    assert contract.player_id == 12345
    assert contract.aav == 5000000
    
    # Test PlayerContractAsk
    ask = PlayerContractAsk(
        player_id=12345,
        updated_season=2024,
        desired_years=3,
        desired_aav=6000000
    )
    session.add(ask)
    session.commit()
    session.refresh(ask)
    
    assert ask.id is not None
    assert ask.player_id == 12345
    assert ask.desired_years == 3
    
    # Test TeamTradeBlock
    trade_block = TeamTradeBlock(
        season=2024,
        team_id=1,
        player_id=12345,
        reason="Test trade block"
    )
    session.add(trade_block)
    session.commit()
    session.refresh(trade_block)
    
    assert trade_block.id is not None
    assert trade_block.player_id == 12345
    assert trade_block.reason == "Test trade block"

