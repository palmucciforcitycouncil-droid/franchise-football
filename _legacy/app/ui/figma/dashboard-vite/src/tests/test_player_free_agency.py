import pytest
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.player import Player
from app.models.contracts import PlayerContract, PlayerContractAsk
from app.models.player_market import PlayerOffer, PlayerOfferStatus
from app.services.player_fa import (
    list_free_agents, create_player_offer, release_player, list_player_offers,
    get_player_ask, update_player_ask, rescind_offer, get_team_offers,
    get_player_offer_history, get_free_agent_summary, get_player_market_value,
    batch_release_players, _position_mult, _accept_threshold
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_free_agents_list_and_offer_flow(client, seeded_db, season_setup):
    """Test free agents list and offer flow."""
    s = season_setup.current_season
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.player import Player

    # Seed two free agents
    with Session(get_engine()) as sess:
        p1 = Player(name="WR Street", team_id=None, pos="WR", age=26, overall=78)
        p2 = Player(name="CB Street", team_id=None, pos="CB", age=27, overall=76)
        sess.add(p1)
        sess.add(p2)
        sess.commit()
        sess.refresh(p1)
        sess.refresh(p2)

    # List FA pool
    r = client.get(f"/api/v1/players/free_agents?season={s}")
    assert r.status_code == 200
    fa = r.json()
    assert any(x["name"] == "WR Street" for x in fa)

    # Make an offer near threshold (should accept or at least return thresholds)
    pid = [x for x in fa if x["name"] == "WR Street"][0]["player_id"]
    ask_aav = [x for x in fa if x["player_id"] == pid][0]["desired_aav"]
    years = [x for x in fa if x["player_id"] == pid][0]["desired_years"]
    r = client.post("/api/v1/players/offer", json={
        "season": s, 
        "team_id": 1, 
        "player_id": pid, 
        "years": years, 
        "aav": int(ask_aav * 1.00)
    })
    assert r.status_code == 200
    data = r.json()
    assert "min_years" in data and "min_aav" in data

def test_release_moves_to_fa(client, seeded_db, season_setup):
    """Test that releasing a player moves them to free agency."""
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.player import Player
    from app.models.contracts import PlayerContract
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        p = Player(name="RB Cut", team_id=3, pos="RB", age=28, overall=74)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        sess.add(PlayerContract(
            player_id=p.player_id, 
            team_id=3, 
            start_season=s-1, 
            end_season=s+1, 
            aav=2500000, 
            is_active=True
        ))
        sess.commit()

    r = client.post(f"/api/v1/players/release/{p.player_id}")
    assert r.status_code == 200 and r.json()["ok"]

    # Should appear in FA list
    r = client.get(f"/api/v1/players/free_agents?season={s}")
    assert any(row["player_id"] == p.player_id for row in r.json())

def test_competing_offers_list(client, seeded_db, season_setup):
    """Test competing offers functionality."""
    s = season_setup.current_season
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.player import Player
    
    with Session(get_engine()) as sess:
        p = Player(name="TE Market", team_id=None, pos="TE", age=27, overall=75)
        sess.add(p)
        sess.commit()
        sess.refresh(p)

    # Two teams place offers below threshold
    r1 = client.post("/api/v1/players/offer", json={
        "season": s, 
        "team_id": 9, 
        "player_id": p.player_id, 
        "years": 2, 
        "aav": 900000
    })
    r2 = client.post("/api/v1/players/offer", json={
        "season": s, 
        "team_id": 10, 
        "player_id": p.player_id, 
        "years": 2, 
        "aav": 950000
    })
    assert r1.status_code == 200 and r2.status_code == 200

    r = client.get(f"/api/v1/players/offers?season={s}&player_id={p.player_id}")
    assert r.status_code == 200
    offers = r.json()
    assert isinstance(offers, list) and len(offers) >= 2

def test_position_multiplier():
    """Test position multiplier calculations."""
    assert _position_mult("QB") == 2.1
    assert _position_mult("WR") == 1.25
    assert _position_mult("RB") == 0.75
    assert _position_mult("K") == 0.45
    assert _position_mult("Unknown") == 1.0

def test_accept_threshold():
    """Test acceptance threshold calculations."""
    ask = PlayerContractAsk(
        player_id=1,
        desired_years=3,
        desired_aav=1000000,
        updated_season=2024
    )
    
    min_years, min_aav = _accept_threshold(ask)
    assert min_years == 2  # ask.years - 1
    assert min_aav == 970000  # ask.aav * 0.97

def test_instant_offer_acceptance(session: Session):
    """Test instant offer acceptance when threshold is met."""
    # Create free agent
    player = Player(name="Test Player", team_id=None, pos="WR", age=26, overall=80)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    # Create ask
    ask = PlayerContractAsk(
        player_id=player.player_id,
        desired_years=3,
        desired_aav=1000000,
        updated_season=2024
    )
    session.add(ask)
    session.commit()
    
    # Make offer that meets threshold
    result = create_player_offer(session, 2024, 1, player.player_id, 3, 1000000)
    
    assert result.accepted is True
    assert result.min_years == 2
    assert result.min_aav == 970000
    
    # Check player was moved to team
    updated_player = session.get(Player, player.player_id)
    assert updated_player.team_id == 1
    
    # Check contract was created
    contract = session.exec(select(PlayerContract).where(
        PlayerContract.player_id == player.player_id,
        PlayerContract.is_active == True  # noqa: E712
    )).first()
    assert contract is not None
    assert contract.team_id == 1
    assert contract.aav == 1000000

def test_offer_below_threshold(session: Session):
    """Test offer below threshold creates active offer."""
    # Create free agent
    player = Player(name="Test Player", team_id=None, pos="WR", age=26, overall=80)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    # Create ask
    ask = PlayerContractAsk(
        player_id=player.player_id,
        desired_years=3,
        desired_aav=1000000,
        updated_season=2024
    )
    session.add(ask)
    session.commit()
    
    # Make offer below threshold
    result = create_player_offer(session, 2024, 1, player.player_id, 2, 800000)
    
    assert result.accepted is False
    assert result.reason == "Below threshold"
    
    # Check player remains free agent
    updated_player = session.get(Player, player.player_id)
    assert updated_player.team_id is None
    
    # Check offer was created
    offer = session.exec(select(PlayerOffer).where(
        PlayerOffer.to_player_id == player.player_id,
        PlayerOffer.status == PlayerOfferStatus.ACTIVE
    )).first()
    assert offer is not None
    assert offer.from_team_id == 1
    assert offer.aav == 800000

def test_release_player(session: Session):
    """Test player release functionality."""
    # Create player with contract
    player = Player(name="Test Player", team_id=1, pos="WR", age=26, overall=80)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    contract = PlayerContract(
        player_id=player.player_id,
        team_id=1,
        start_season=2024,
        end_season=2026,
        aav=1000000,
        is_active=True
    )
    session.add(contract)
    session.commit()
    
    # Release player
    result = release_player(session, player.player_id)
    assert result is True
    
    # Check player is now free agent
    updated_player = session.get(Player, player.player_id)
    assert updated_player.team_id is None
    
    # Check contract is deactivated
    updated_contract = session.get(PlayerContract, contract.contract_id)
    assert updated_contract.is_active is False

def test_list_free_agents(session: Session):
    """Test free agents listing."""
    # Create free agents
    players = [
        Player(name="FA1", team_id=None, pos="WR", age=26, overall=80),
        Player(name="FA2", team_id=None, pos="RB", age=25, overall=75),
        Player(name="Rostered", team_id=1, pos="QB", age=28, overall=85)
    ]
    
    for player in players:
        session.add(player)
    session.commit()
    
    # List free agents
    fa_list = list_free_agents(session, 2024)
    
    assert len(fa_list) == 2  # Only free agents
    assert any(fa.name == "FA1" for fa in fa_list)
    assert any(fa.name == "FA2" for fa in fa_list)
    assert not any(fa.name == "Rostered" for fa in fa_list)

def test_competing_offers_count(session: Session):
    """Test competing offers count in free agents list."""
    # Create free agent
    player = Player(name="Test Player", team_id=None, pos="WR", age=26, overall=80)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    # Create multiple offers
    offers = [
        PlayerOffer(season=2024, from_team_id=1, to_player_id=player.player_id, years=3, aav=1000000),
        PlayerOffer(season=2024, from_team_id=2, to_player_id=player.player_id, years=2, aav=900000),
        PlayerOffer(season=2024, from_team_id=3, to_player_id=player.player_id, years=4, aav=1100000)
    ]
    
    for offer in offers:
        session.add(offer)
    session.commit()
    
    # List free agents
    fa_list = list_free_agents(session, 2024)
    player_fa = next(fa for fa in fa_list if fa.player_id == player.player_id)
    
    assert player_fa.competing_offers == 3

def test_rescind_offer(session: Session):
    """Test offer rescission."""
    # Create offer
    offer = PlayerOffer(
        season=2024,
        from_team_id=1,
        to_player_id=1,
        years=3,
        aav=1000000,
        status=PlayerOfferStatus.ACTIVE
    )
    session.add(offer)
    session.commit()
    session.refresh(offer)
    
    # Rescind offer
    result = rescind_offer(session, offer.offer_id)
    assert result is True
    
    # Check offer status
    updated_offer = session.get(PlayerOffer, offer.offer_id)
    assert updated_offer.status == PlayerOfferStatus.RESCINDED

def test_batch_release_players(session: Session):
    """Test batch release functionality."""
    # Create players
    players = [
        Player(name="Player1", team_id=1, pos="WR", age=26, overall=80),
        Player(name="Player2", team_id=1, pos="RB", age=25, overall=75),
        Player(name="Player3", team_id=2, pos="QB", age=28, overall=85)
    ]
    
    for player in players:
        session.add(player)
    session.commit()
    
    # Batch release
    player_ids = [p.player_id for p in players]
    result = batch_release_players(session, player_ids)
    
    assert len(result["success"]) == 3
    assert len(result["failed"]) == 0
    
    # Check all players are free agents
    for player in players:
        updated_player = session.get(Player, player.player_id)
        assert updated_player.team_id is None

def test_free_agent_summary(session: Session):
    """Test free agent summary statistics."""
    # Create free agents
    players = [
        Player(name="FA1", team_id=None, pos="WR", age=26, overall=80),
        Player(name="FA2", team_id=None, pos="RB", age=25, overall=75),
        Player(name="FA3", team_id=None, pos="QB", age=28, overall=85)
    ]
    
    for player in players:
        session.add(player)
    session.commit()
    
    # Create some offers
    offers = [
        PlayerOffer(season=2024, from_team_id=1, to_player_id=players[0].player_id, years=3, aav=1000000),
        PlayerOffer(season=2024, from_team_id=2, to_player_id=players[0].player_id, years=2, aav=900000),
        PlayerOffer(season=2024, from_team_id=3, to_player_id=players[1].player_id, years=3, aav=800000)
    ]
    
    for offer in offers:
        session.add(offer)
    session.commit()
    
    # Get summary
    summary = get_free_agent_summary(session, 2024)
    
    assert summary["season"] == 2024
    assert summary["total_free_agents"] == 3
    assert summary["total_active_offers"] == 3
    assert summary["average_overall"] == 80.0
    assert "WR" in summary["position_breakdown"]
    assert "RB" in summary["position_breakdown"]
    assert "QB" in summary["position_breakdown"]

def test_player_market_value(session: Session):
    """Test player market value analysis."""
    # Create free agent
    player = Player(name="Test Player", team_id=None, pos="WR", age=26, overall=80)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    # Create ask
    ask = PlayerContractAsk(
        player_id=player.player_id,
        desired_years=3,
        desired_aav=1000000,
        updated_season=2024
    )
    session.add(ask)
    session.commit()
    
    # Create offers
    offers = [
        PlayerOffer(season=2024, from_team_id=1, to_player_id=player.player_id, years=3, aav=1000000),
        PlayerOffer(season=2024, from_team_id=2, to_player_id=player.player_id, years=2, aav=900000),
        PlayerOffer(season=2024, from_team_id=3, to_player_id=player.player_id, years=4, aav=1100000)
    ]
    
    for offer in offers:
        session.add(offer)
    session.commit()
    
    # Get market value
    market_value = get_player_market_value(session, player.player_id, 2024)
    
    assert market_value["player_id"] == player.player_id
    assert market_value["player_name"] == "Test Player"
    assert market_value["position"] == "WR"
    assert market_value["overall"] == 80
    assert market_value["competing_offers"] == 3
    assert market_value["average_offer"] == 1000000
    assert market_value["max_offer"] == 1100000
    assert market_value["market_demand"] == "High"

def test_api_endpoints(client, seeded_db):
    """Test all API endpoints."""
    # Test free agents list
    r = client.get("/api/v1/players/free_agents?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test offer
    r = client.post("/api/v1/players/offer", json={
        "season": 2024,
        "team_id": 1,
        "player_id": 1,
        "years": 3,
        "aav": 1000000
    })
    assert r.status_code == 200
    assert "accepted" in r.json()
    
    # Test release
    r = client.post("/api/v1/players/release/1")
    assert r.status_code == 200
    assert "ok" in r.json()
    
    # Test offers list
    r = client.get("/api/v1/players/offers?season=2024&player_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test offer history
    r = client.get("/api/v1/players/offers/history?season=2024&player_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test team offers
    r = client.get("/api/v1/players/offers/team/1?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test rescind offer
    r = client.post("/api/v1/players/rescind/1")
    assert r.status_code == 200
    assert "ok" in r.json()
    
    # Test update ask
    r = client.post("/api/v1/players/ask/update", json={
        "player_id": 1,
        "season": 2024,
        "years": 3,
        "aav": 1000000
    })
    assert r.status_code == 200
    assert "ok" in r.json()
    
    # Test get ask
    r = client.get("/api/v1/players/ask/1?season=2024")
    assert r.status_code in [200, 404]  # May not exist
    
    # Test market value
    r = client.get("/api/v1/players/market_value/1?season=2024")
    assert r.status_code == 200
    
    # Test summary
    r = client.get("/api/v1/players/summary?season=2024")
    assert r.status_code == 200
    assert "season" in r.json()
    
    # Test batch release
    r = client.post("/api/v1/players/batch_release", json={"player_ids": [1, 2, 3]})
    assert r.status_code == 200
    assert "success" in r.json()
    
    # Test team free agents
    r = client.get("/api/v1/players/team_free_agents/1?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test position filter
    r = client.get("/api/v1/players/position/WR?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test top free agents
    r = client.get("/api/v1/players/top/10?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test search
    r = client.get("/api/v1/players/search?season=2024&min_overall=70&max_overall=90")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test offer stats
    r = client.get("/api/v1/players/offer_stats/1?season=2024")
    assert r.status_code == 200
    assert "total_offers" in r.json()

def test_error_handling(client, seeded_db):
    """Test error handling in API endpoints."""
    # Test offer to non-existent player
    r = client.post("/api/v1/players/offer", json={
        "season": 2024,
        "team_id": 1,
        "player_id": 99999,
        "years": 3,
        "aav": 1000000
    })
    assert r.status_code == 200
    assert r.json()["accepted"] is False
    assert "not found" in r.json()["reason"]
    
    # Test release non-existent player
    r = client.post("/api/v1/players/release/99999")
    assert r.status_code == 200
    assert r.json()["ok"] is False
    
    # Test rescind non-existent offer
    r = client.post("/api/v1/players/rescind/99999")
    assert r.status_code == 200
    assert r.json()["ok"] is False

def test_offer_acceptance_thresholds(session: Session):
    """Test offer acceptance thresholds."""
    # Create free agent
    player = Player(name="Test Player", team_id=None, pos="WR", age=26, overall=80)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    # Create ask
    ask = PlayerContractAsk(
        player_id=player.player_id,
        desired_years=3,
        desired_aav=1000000,
        updated_season=2024
    )
    session.add(ask)
    session.commit()
    
    # Test offer at exact threshold
    result = create_player_offer(session, 2024, 1, player.player_id, 2, 970000)
    assert result.accepted is True
    
    # Test offer below threshold
    result = create_player_offer(session, 2024, 2, player.player_id, 2, 960000)
    assert result.accepted is False
    
    # Test offer with insufficient years
    result = create_player_offer(session, 2024, 3, player.player_id, 1, 1000000)
    assert result.accepted is False

def test_contract_deactivation_on_release(session: Session):
    """Test that contracts are deactivated when players are released."""
    # Create player with contract
    player = Player(name="Test Player", team_id=1, pos="WR", age=26, overall=80)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    contract = PlayerContract(
        player_id=player.player_id,
        team_id=1,
        start_season=2024,
        end_season=2026,
        aav=1000000,
        is_active=True
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    
    # Release player
    release_player(session, player.player_id)
    
    # Check contract is deactivated
    updated_contract = session.get(PlayerContract, contract.contract_id)
    assert updated_contract.is_active is False
    
    # Check player is free agent
    updated_player = session.get(Player, player.player_id)
    assert updated_player.team_id is None

def test_offer_status_updates(session: Session):
    """Test offer status updates."""
    # Create free agent
    player = Player(name="Test Player", team_id=None, pos="WR", age=26, overall=80)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    # Create ask
    ask = PlayerContractAsk(
        player_id=player.player_id,
        desired_years=3,
        desired_aav=1000000,
        updated_season=2024
    )
    session.add(ask)
    session.commit()
    
    # Create multiple offers
    offer1 = PlayerOffer(season=2024, from_team_id=1, to_player_id=player.player_id, years=2, aav=900000)
    offer2 = PlayerOffer(season=2024, from_team_id=2, to_player_id=player.player_id, years=3, aav=1000000)
    session.add(offer1)
    session.add(offer2)
    session.commit()
    
    # Accept one offer
    result = create_player_offer(session, 2024, 3, player.player_id, 3, 1000000)
    assert result.accepted is True
    
    # Check all offers are marked as consummated
    offers = session.exec(select(PlayerOffer).where(
        PlayerOffer.to_player_id == player.player_id
    )).all()
    
    for offer in offers:
        assert offer.status == PlayerOfferStatus.CONSUMMATED

