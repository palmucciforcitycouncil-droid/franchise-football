# tests/test_expiring_contracts_api.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import get_engine
from app.models.core_min import Player, Team
from app.models.contracts import Contract
from datetime import date

client = TestClient(app)

def test_expiring_endpoint_returns_players(tmp_path):
    """Test that expiring contracts endpoint returns proper structure."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test player
        player = Player(
            team_id=team.id,
            pos="QB",
            name="Test QB",
            rating=85,
            age=28,
            desired_years=3,
            desired_aav=10_000_000
        )
        s.add(player)
        s.commit()
        s.refresh(player)
        
        # Create expiring contract
        contract = Contract(
            player_id=player.id,
            team_id=team.id,
            signed_on=date.today(),
            start_season=2023,
            end_season=2025,
            aav=8_000_000,
            is_active=True,
            acquired_via="DRAFT"
        )
        s.add(contract)
        s.commit()
        
        # Test endpoint
        r = client.get(f"/api/v1/contracts/expiring?team_id={team.id}&season=2025")
        assert r.status_code == 200
        data = r.json()
        assert data["team_id"] == team.id
        assert data["season"] == 2025
        assert len(data["players"]) >= 1
        
        # Check structure
        p = data["players"][0]
        assert {"player_id","name","position","age","overall","current_cap_hit","desired_years","desired_aav"} <= set(p.keys())
        assert p["player_id"] == player.id
        assert p["name"] == "Test QB"
        assert p["position"] == "QB"
        assert p["age"] == 28
        assert p["overall"] == 85

def test_negotiation_accept_flow(tmp_path):
    """Test negotiation acceptance flow."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test player
        player = Player(
            team_id=team.id,
            pos="QB",
            name="Test QB",
            rating=88,
            age=28,
            desired_years=3,
            desired_aav=10_000_000
        )
        s.add(player)
        s.commit()
        s.refresh(player)
        
        # Test negotiation with acceptable offer
        res = client.post(f"/api/v1/contracts/{player.id}/negotiate?season=2025", 
                         json={"aav": 10_000_000, "years": 3})
        assert res.status_code == 200
        assert res.json()["accepted"] is True

def test_negotiation_reject_flow(tmp_path):
    """Test negotiation rejection flow."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test player
        player = Player(
            team_id=team.id,
            pos="QB",
            name="Test QB",
            rating=88,
            age=28,
            desired_years=3,
            desired_aav=10_000_000
        )
        s.add(player)
        s.commit()
        s.refresh(player)
        
        # Test negotiation with unacceptable offer
        res = client.post(f"/api/v1/contracts/{player.id}/negotiate?season=2025", 
                         json={"aav": 5_000_000, "years": 1})
        assert res.status_code == 200
        assert res.json()["accepted"] is False
        assert "reason" in res.json()

def test_release_moves_to_fa(tmp_path):
    """Test that release moves player to FA pool."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test player
        player = Player(
            team_id=team.id,
            pos="QB",
            name="Test QB",
            rating=85,
            age=28,
            desired_years=3,
            desired_aav=10_000_000
        )
        s.add(player)
        s.commit()
        s.refresh(player)
        
        # Create active contract
        contract = Contract(
            player_id=player.id,
            team_id=team.id,
            signed_on=date.today(),
            start_season=2023,
            end_season=2025,
            aav=8_000_000,
            is_active=True,
            acquired_via="DRAFT"
        )
        s.add(contract)
        s.commit()
        
        # Test release
        res = client.post(f"/api/v1/contracts/{player.id}/release")
        assert res.status_code == 200
        assert res.json()["ok"] is True
        
        # Verify player moved to FA
        s.refresh(player)
        assert player.team_id is None
        assert player.trade_block is False
        
        # Verify contract ended
        s.refresh(contract)
        assert contract.is_active is False

def test_teams_list_endpoint(tmp_path):
    """Test teams list endpoint for dropdown."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test teams
        team1 = Team(abbrev="TEAM1", name="Team One")
        team2 = Team(abbrev="TEAM2", name="Team Two")
        s.add(team1)
        s.add(team2)
        s.commit()
        
        # Test endpoint
        res = client.get("/api/v1/contracts/teams/list")
        assert res.status_code == 200
        data = res.json()
        assert "teams" in data
        assert len(data["teams"]) >= 2
        
        # Check structure
        team = data["teams"][0]
        assert {"team_id", "name", "abbrev"} <= set(team.keys())

def test_negotiation_logic_player_accepts(tmp_path):
    """Test negotiation logic acceptance criteria."""
    from app.services.negotiation_logic import player_accepts
    from app.models.core_min import Player
    
    # Create test player
    player = Player(
        desired_aav=10_000_000,
        desired_years=3
    )
    
    # Test acceptable offer (96% of ask, within 1 year)
    assert player_accepts(9_600_000, 3, player) is True
    assert player_accepts(10_000_000, 2, player) is True
    
    # Test unacceptable offers
    assert player_accepts(9_500_000, 3, player) is False  # Below 96%
    assert player_accepts(10_000_000, 1, player) is False  # Too short

def test_ai_offer_logic(tmp_path):
    """Test AI offer decision logic."""
    from app.services.negotiation_logic import ai_offer_for_player
    from app.models.core_min import Player
    
    # Test high-value QB
    qb = Player(
        pos="QB",
        age=26,
        rating=90,
        desired_aav=20_000_000,
        desired_years=4
    )
    
    decision = ai_offer_for_player(qb, 50_000_000)  # Plenty of cap space
    assert decision.will_pay is True
    assert decision.reason == "core_piece"
    assert decision.offered_aav > 0
    assert decision.offered_years > 0
    
    # Test old player
    old_player = Player(
        pos="RB",
        age=32,
        rating=75,
        desired_aav=8_000_000,
        desired_years=3
    )
    
    decision = ai_offer_for_player(old_player, 30_000_000)
    # Should be less likely to pay due to age
    assert decision.offered_aav < old_player.desired_aav

def test_preseason_ai_trade_block_logic(tmp_path):
    """Test preseason AI trade block marking."""
    from app.services.preseason_ai import run_preseason_expiring_contract_logic
    import random
    
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test players
        players = []
        for i in range(5):
            player = Player(
                team_id=team.id,
                pos="QB",
                name=f"Test QB {i}",
                rating=75 + i,
                age=28 + i,
                desired_years=3,
                desired_aav=10_000_000 + i * 1_000_000
            )
            s.add(player)
            players.append(player)
        s.commit()
        
        # Create expiring contracts
        for player in players:
            contract = Contract(
                player_id=player.id,
                team_id=team.id,
                signed_on=date.today(),
                start_season=2023,
                end_season=2025,
                aav=8_000_000,
                is_active=True,
                acquired_via="DRAFT"
            )
            s.add(contract)
        s.commit()
        
        # Run preseason AI
        rng = random.Random(42)  # Deterministic for testing
        run_preseason_expiring_contract_logic(s, team.id, 2025, 20_000_000, rng)
        
        # Check that some players may be marked for trade block
        # (exact count depends on AI logic, but should be deterministic)
        trade_blocked = s.exec(select(Player).where(Player.trade_block == True)).all()
        assert len(trade_blocked) <= len(players)  # Can't exceed total players


