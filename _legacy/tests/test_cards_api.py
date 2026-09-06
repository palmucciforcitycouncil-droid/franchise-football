import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.core.db import engine as get_engine
from app.models.player import Player
from app.models.coach import Coach, CoachRole
from app.models.team import Team
from app.models.contracts import PlayerContract, PlayerContractAsk
from app.models.coach import CoachContract, CoachAsk
from app.models.injury import Injury, InjuryStatus, InjuryType
from app.models.player_market import PlayerOffer, PlayerOfferStatus
from app.models.contracts import TeamTradeBlock
from app.services.cards_service import build_player_card, build_coach_card, build_team_card

def test_player_card_bundle(client, seeded_db, season_setup):
    """Test complete player card with all sections."""
    s = season_setup.current_season
    
    # Minimal seed
    with Session(get_engine()) as sess:
        p = Player(name="QB Modal", team_id=1, pos="QB", age=27, overall=84)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        
        # Add contract and ask
        sess.add(PlayerContract(
            player_id=p.player_id, 
            team_id=1, 
            start_season=s-1, 
            end_season=s+2, 
            aav=12000000, 
            is_active=True
        ))
        sess.add(PlayerContractAsk(
            player_id=p.player_id, 
            updated_season=s, 
            desired_years=4, 
            desired_aav=14000000
        ))
        sess.commit()
        pid = p.player_id

    # Test API endpoint
    r = client.get(f"/api/v1/cards/player?player_id={pid}&season={s}")
    assert r.status_code == 200
    
    data = r.json()["data"]
    
    # Verify all sections are present
    assert "bio" in data
    assert "contract" in data
    assert "status" in data
    assert "stats" in data
    assert "market" in data
    assert "accolades" in data
    assert "actions" in data
    
    # Verify bio data
    assert data["bio"]["name"] == "QB Modal"
    assert data["bio"]["pos"] == "QB"
    assert data["bio"]["age"] == 27
    assert data["bio"]["overall"] == 84
    assert data["bio"]["team_id"] == 1
    
    # Verify contract data
    assert data["contract"]["active"] is not None
    assert data["contract"]["active"]["aav"] == 12000000
    assert data["contract"]["ask"] is not None
    assert data["contract"]["ask"]["desired_aav"] == 14000000
    assert data["contract"]["is_free_agent"] is False
    assert data["contract"]["on_trade_block"] is False
    
    # Verify actions
    assert isinstance(data["actions"]["trade_for"], bool)
    assert isinstance(data["actions"]["negotiate"], bool)
    assert isinstance(data["actions"]["release"], bool)

def test_coach_card_bundle(client, seeded_db, season_setup):
    """Test complete coach card with all sections."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        c = Coach(name="Coach Modal", team_id=1, role=CoachRole.OC, overall=79)
        sess.add(c)
        sess.commit()
        sess.refresh(c)
        
        # Add contract
        sess.add(CoachContract(
            coach_id=c.coach_id, 
            team_id=1, 
            start_season=s-1, 
            end_season=s+1, 
            aav=2500000, 
            is_active=True
        ))
        sess.commit()
        cid = c.coach_id

    # Test API endpoint
    r = client.get(f"/api/v1/cards/coach?coach_id={cid}&season={s}")
    assert r.status_code == 200
    
    data = r.json()["data"]
    
    # Verify all sections are present
    assert "bio" in data
    assert "contract" in data
    assert "status" in data
    assert "stats" in data
    assert "accolades" in data
    assert "actions" in data
    
    # Verify bio data
    assert data["bio"]["name"] == "Coach Modal"
    assert data["bio"]["role"] == "OC"
    assert data["bio"]["overall"] == 79
    assert data["bio"]["team_id"] == 1
    
    # Verify contract data
    assert data["contract"]["active"] is not None
    assert data["contract"]["active"]["aav"] == 2500000
    
    # Verify actions
    assert isinstance(data["actions"]["promote"], bool)
    assert isinstance(data["actions"]["fire"], bool)
    assert isinstance(data["actions"]["resign"], bool)

def test_player_card_with_injury(client, seeded_db, season_setup):
    """Test player card with injury information."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        p = Player(name="Injured Player", team_id=1, pos="RB", age=25, overall=78)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        
        # Add injury
        sess.add(Injury(
            season=s,
            week=3,
            player_id=p.player_id,
            team_id=1,
            injury_type=InjuryType.HAMSTRING,
            severity=5,
            weeks_out_total=4,
            weeks_out_remaining=3,
            status=InjuryStatus.OUT,
            resolved=False
        ))
        sess.commit()
        pid = p.player_id

    # Test API endpoint
    r = client.get(f"/api/v1/cards/player?player_id={pid}&season={s}")
    assert r.status_code == 200
    
    data = r.json()["data"]
    
    # Verify injury status
    assert data["status"]["active"] is True
    assert data["status"]["injury_type"] == "HAMSTRING"
    assert data["status"]["severity"] == 5
    assert data["status"]["weeks_out_remaining"] == 3
    assert data["status"]["status"] == "OUT"

def test_player_card_free_agent(client, seeded_db, season_setup):
    """Test player card for free agent."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        p = Player(name="Free Agent", team_id=None, pos="WR", age=28, overall=82)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        
        # Add contract ask
        sess.add(PlayerContractAsk(
            player_id=p.player_id, 
            updated_season=s, 
            desired_years=3, 
            desired_aav=8000000
        ))
        sess.commit()
        pid = p.player_id

    # Test API endpoint
    r = client.get(f"/api/v1/cards/player?player_id={pid}&season={s}")
    assert r.status_code == 200
    
    data = r.json()["data"]
    
    # Verify free agent status
    assert data["contract"]["is_free_agent"] is True
    assert data["contract"]["on_trade_block"] is False
    assert data["contract"]["active"] is None
    assert data["contract"]["ask"] is not None
    assert data["contract"]["ask"]["desired_aav"] == 8000000
    
    # Verify actions for FA
    assert data["actions"]["trade_for"] is False  # Can't trade FA
    assert data["actions"]["negotiate"] is True   # Can negotiate
    assert data["actions"]["release"] is False    # Can't release FA

def test_player_card_on_trade_block(client, seeded_db, season_setup):
    """Test player card for player on trade block."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        p = Player(name="Trade Block Player", team_id=1, pos="LB", age=29, overall=76)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        
        # Add to trade block
        sess.add(TeamTradeBlock(
            season=s,
            team_id=1,
            player_id=p.player_id,
            reason="Expiring contract"
        ))
        sess.commit()
        pid = p.player_id

    # Test API endpoint
    r = client.get(f"/api/v1/cards/player?player_id={pid}&season={s}")
    assert r.status_code == 200
    
    data = r.json()["data"]
    
    # Verify trade block status
    assert data["contract"]["on_trade_block"] is True
    assert data["contract"]["is_free_agent"] is False

def test_player_card_with_offers(client, seeded_db, season_setup):
    """Test player card with competing offers."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        p = Player(name="Offered Player", team_id=None, pos="CB", age=26, overall=80)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        
        # Add competing offers
        sess.add(PlayerOffer(
            season=s,
            from_team_id=2,
            to_player_id=p.player_id,
            years=3,
            aav=6000000,
            status=PlayerOfferStatus.ACTIVE
        ))
        sess.add(PlayerOffer(
            season=s,
            from_team_id=3,
            to_player_id=p.player_id,
            years=4,
            aav=6500000,
            status=PlayerOfferStatus.ACTIVE
        ))
        sess.commit()
        pid = p.player_id

    # Test API endpoint
    r = client.get(f"/api/v1/cards/player?player_id={pid}&season={s}")
    assert r.status_code == 200
    
    data = r.json()["data"]
    
    # Verify market offers
    assert len(data["market"]["offers"]) == 2
    offers = data["market"]["offers"]
    
    # Check offer details
    offer_aavs = [offer["aav"] for offer in offers]
    assert 6000000 in offer_aavs
    assert 6500000 in offer_aavs

def test_coach_card_promotion_eligibility(client, seeded_db, season_setup):
    """Test coach card promotion eligibility based on role."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Test AC (eligible for promotion)
        ac = Coach(name="Assistant Coach", team_id=1, role=CoachRole.AC1, overall=75)
        sess.add(ac)
        sess.commit()
        sess.refresh(ac)
        
        # Test HC (not eligible for promotion)
        hc = Coach(name="Head Coach", team_id=2, role=CoachRole.HC, overall=85)
        sess.add(hc)
        sess.commit()
        sess.refresh(hc)

    # Test AC card
    r = client.get(f"/api/v1/cards/coach?coach_id={ac.coach_id}&season={s}")
    assert r.status_code == 200
    ac_data = r.json()["data"]
    assert ac_data["actions"]["promote"] is True
    
    # Test HC card
    r = client.get(f"/api/v1/cards/coach?coach_id={hc.coach_id}&season={s}")
    assert r.status_code == 200
    hc_data = r.json()["data"]
    assert hc_data["actions"]["promote"] is False

def test_team_card_bundle(client, seeded_db, season_setup):
    """Test team card with roster and staff."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add team
        team = Team(team_id=10, name="Test Team", conference="AFC", division="E")
        sess.add(team)
        sess.commit()
        
        # Add players
        for i in range(5):
            p = Player(name=f"Player {i}", team_id=10, pos="QB" if i == 0 else "WR", overall=75+i)
            sess.add(p)
        
        # Add coaches
        hc = Coach(name="Test HC", team_id=10, role=CoachRole.HC, overall=80)
        oc = Coach(name="Test OC", team_id=10, role=CoachRole.OC, overall=78)
        sess.add(hc)
        sess.add(oc)
        sess.commit()

    # Test API endpoint
    r = client.get(f"/api/v1/cards/team?team_id=10&season={s}")
    assert r.status_code == 200
    
    data = r.json()["data"]
    
    # Verify team bio
    assert data["bio"]["name"] == "Test Team"
    assert data["bio"]["conference"] == "AFC"
    assert data["bio"]["division"] == "E"
    
    # Verify roster counts
    assert data["roster"]["total_players"] == 5
    assert "by_position" in data["roster"]
    
    # Verify coaching staff
    assert len(data["coaching_staff"]) == 2
    staff_names = [staff["name"] for staff in data["coaching_staff"]]
    assert "Test HC" in staff_names
    assert "Test OC" in staff_names

def test_cards_summary(client, seeded_db, season_setup):
    """Test cards summary endpoint."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add some test data
        p1 = Player(name="Player 1", team_id=1, pos="QB", overall=80)
        p2 = Player(name="Player 2", team_id=None, pos="WR", overall=75)  # FA
        c1 = Coach(name="Coach 1", team_id=1, role=CoachRole.HC, overall=85)
        t1 = Team(team_id=20, name="Test Team", conference="NFC", division="N")
        
        sess.add(p1)
        sess.add(p2)
        sess.add(c1)
        sess.add(t1)
        sess.commit()

    # Test API endpoint
    r = client.get(f"/api/v1/cards/summary?season={s}")
    assert r.status_code == 200
    
    data = r.json()["summary"]
    
    # Verify summary counts
    assert data["season"] == s
    assert data["players"] >= 2
    assert data["free_agents"] >= 1
    assert data["coaches"] >= 1
    assert data["teams"] >= 1

def test_player_cards_batch(client, seeded_db, season_setup):
    """Test batch player cards endpoint."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add multiple players
        players = []
        for i in range(3):
            p = Player(name=f"Batch Player {i}", team_id=1, pos="RB", overall=75+i)
            sess.add(p)
            players.append(p)
        sess.commit()
        
        # Get player IDs
        pids = [p.player_id for p in players]

    # Test API endpoint
    player_ids_str = ",".join(map(str, pids))
    r = client.get(f"/api/v1/cards/players/batch?player_ids={player_ids_str}&season={s}")
    assert r.status_code == 200
    
    data = r.json()
    
    # Verify batch response
    assert data["total"] == 3
    assert len(data["cards"]) == 3
    
    # Verify each card
    for card in data["cards"]:
        assert "bio" in card
        assert "contract" in card
        assert "actions" in card

def test_coach_cards_batch(client, seeded_db, season_setup):
    """Test batch coach cards endpoint."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add multiple coaches
        coaches = []
        for i in range(3):
            c = Coach(name=f"Batch Coach {i}", team_id=1, role=CoachRole.AC1, overall=75+i)
            sess.add(c)
            coaches.append(c)
        sess.commit()
        
        # Get coach IDs
        cids = [c.coach_id for c in coaches]

    # Test API endpoint
    coach_ids_str = ",".join(map(str, cids))
    r = client.get(f"/api/v1/cards/coaches/batch?coach_ids={coach_ids_str}&season={s}")
    assert r.status_code == 200
    
    data = r.json()
    
    # Verify batch response
    assert data["total"] == 3
    assert len(data["cards"]) == 3
    
    # Verify each card
    for card in data["cards"]:
        assert "bio" in card
        assert "contract" in card
        assert "actions" in card

def test_team_roster_cards(client, seeded_db, season_setup):
    """Test team roster cards endpoint."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add team with players
        team = Team(team_id=30, name="Roster Team", conference="AFC", division="S")
        sess.add(team)
        
        for i in range(4):
            p = Player(name=f"Roster Player {i}", team_id=30, pos="LB", overall=70+i)
            sess.add(p)
        sess.commit()

    # Test API endpoint
    r = client.get(f"/api/v1/cards/team/30/roster?season={s}")
    assert r.status_code == 200
    
    data = r.json()
    
    # Verify roster response
    assert data["total"] == 4
    assert len(data["cards"]) == 4
    
    # Verify each card is for the right team
    for card in data["cards"]:
        assert card["bio"]["team_id"] == 30

def test_team_staff_cards(client, seeded_db, season_setup):
    """Test team staff cards endpoint."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add team with coaches
        team = Team(team_id=40, name="Staff Team", conference="NFC", division="W")
        sess.add(team)
        
        hc = Coach(name="Staff HC", team_id=40, role=CoachRole.HC, overall=85)
        dc = Coach(name="Staff DC", team_id=40, role=CoachRole.DC, overall=80)
        sess.add(hc)
        sess.add(dc)
        sess.commit()

    # Test API endpoint
    r = client.get(f"/api/v1/cards/team/40/staff?season={s}")
    assert r.status_code == 200
    
    data = r.json()
    
    # Verify staff response
    assert data["total"] == 2
    assert len(data["cards"]) == 2
    
    # Verify each card is for the right team
    for card in data["cards"]:
        assert card["bio"]["team_id"] == 40

def test_free_agent_cards(client, seeded_db, season_setup):
    """Test free agent cards endpoint."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add free agents
        for i in range(3):
            p = Player(name=f"FA Player {i}", team_id=None, pos="WR", overall=75+i)
            sess.add(p)
        sess.commit()

    # Test API endpoint
    r = client.get(f"/api/v1/cards/free_agents?season={s}")
    assert r.status_code == 200
    
    data = r.json()
    
    # Verify free agent response
    assert data["total"] == 3
    assert len(data["cards"]) == 3
    
    # Verify each card is a free agent
    for card in data["cards"]:
        assert card["contract"]["is_free_agent"] is True

def test_free_agent_cards_with_filters(client, seeded_db, season_setup):
    """Test free agent cards with position and overall filters."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add free agents with different positions and overalls
        p1 = Player(name="FA QB", team_id=None, pos="QB", overall=85)
        p2 = Player(name="FA WR", team_id=None, pos="WR", overall=75)
        p3 = Player(name="FA CB", team_id=None, pos="CB", overall=80)
        sess.add(p1)
        sess.add(p2)
        sess.add(p3)
        sess.commit()

    # Test with position filter
    r = client.get(f"/api/v1/cards/free_agents?season={s}&position=QB")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["cards"][0]["bio"]["pos"] == "QB"
    
    # Test with overall filter
    r = client.get(f"/api/v1/cards/free_agents?season={s}&min_overall=80")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2  # QB (85) and CB (80)
    
    # Test with both filters
    r = client.get(f"/api/v1/cards/free_agents?season={s}&position=WR&min_overall=80")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0  # WR is 75 overall

def test_search_cards(client, seeded_db, season_setup):
    """Test search cards endpoint."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Add test data
        p = Player(name="Search Player", team_id=1, pos="QB", overall=80)
        c = Coach(name="Search Coach", team_id=1, role=CoachRole.HC, overall=85)
        t = Team(team_id=50, name="Search Team", conference="AFC", division="E")
        
        sess.add(p)
        sess.add(c)
        sess.add(t)
        sess.commit()

    # Test search for players
    r = client.get(f"/api/v1/cards/search?query=Search&season={s}&card_type=player")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["cards"][0]["bio"]["name"] == "Search Player"
    
    # Test search for coaches
    r = client.get(f"/api/v1/cards/search?query=Search&season={s}&card_type=coach")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["cards"][0]["bio"]["name"] == "Search Coach"
    
    # Test search for teams
    r = client.get(f"/api/v1/cards/search?query=Search&season={s}&card_type=team")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["cards"][0]["bio"]["name"] == "Search Team"
    
    # Test search for all
    r = client.get(f"/api/v1/cards/search?query=Search&season={s}&card_type=all")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3  # Player + Coach + Team

def test_cards_error_handling(client, seeded_db, season_setup):
    """Test error handling for non-existent cards."""
    s = season_setup.current_season
    
    # Test non-existent player
    r = client.get(f"/api/v1/cards/player?player_id=99999&season={s}")
    assert r.status_code == 404
    assert "Player not found" in r.json()["detail"]
    
    # Test non-existent coach
    r = client.get(f"/api/v1/cards/coach?coach_id=99999&season={s}")
    assert r.status_code == 404
    assert "Coach not found" in r.json()["detail"]
    
    # Test non-existent team
    r = client.get(f"/api/v1/cards/team?team_id=99999&season={s}")
    assert r.status_code == 404
    assert "Team not found" in r.json()["detail"]

def test_batch_endpoints_error_handling(client, seeded_db, season_setup):
    """Test error handling for batch endpoints."""
    s = season_setup.current_season
    
    # Test invalid player IDs format
    r = client.get(f"/api/v1/cards/players/batch?player_ids=invalid&season={s}")
    assert r.status_code == 400
    assert "Invalid player IDs format" in r.json()["detail"]
    
    # Test too many player IDs
    too_many_ids = ",".join(map(str, range(51)))  # 51 IDs
    r = client.get(f"/api/v1/cards/players/batch?player_ids={too_many_ids}&season={s}")
    assert r.status_code == 400
    assert "Too many player IDs" in r.json()["detail"]

def test_cards_service_directly(seeded_db, season_setup):
    """Test cards service functions directly."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Test player card
        p = Player(name="Direct Test Player", team_id=1, pos="QB", age=28, overall=82)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        
        card = build_player_card(sess, p.player_id, s)
        assert "bio" in card
        assert "contract" in card
        assert "actions" in card
        assert card["bio"]["name"] == "Direct Test Player"
        
        # Test coach card
        c = Coach(name="Direct Test Coach", team_id=1, role=CoachRole.HC, overall=85)
        sess.add(c)
        sess.commit()
        sess.refresh(c)
        
        card = build_coach_card(sess, c.coach_id, s)
        assert "bio" in card
        assert "contract" in card
        assert "actions" in card
        assert card["bio"]["name"] == "Direct Test Coach"
        
        # Test team card
        t = Team(team_id=60, name="Direct Test Team", conference="AFC", division="N")
        sess.add(t)
        sess.commit()
        
        card = build_team_card(sess, t.team_id, s)
        assert "bio" in card
        assert "roster" in card
        assert "coaching_staff" in card
        assert card["bio"]["name"] == "Direct Test Team"

def test_cards_service_defensive_imports(seeded_db, season_setup):
    """Test that cards service handles missing models gracefully."""
    s = season_setup.current_season
    
    with Session(get_engine()) as sess:
        # Test with minimal data (no contracts, injuries, etc.)
        p = Player(name="Minimal Player", team_id=1, pos="RB", age=25, overall=75)
        sess.add(p)
        sess.commit()
        sess.refresh(p)
        
        # Should not crash even if models are missing
        card = build_player_card(sess, p.player_id, s)
        assert "bio" in card
        assert "contract" in card
        assert "status" in card
        assert "stats" in card
        assert "market" in card
        assert "accolades" in card
        assert "actions" in card
        
        # Verify default values
        assert card["contract"]["active"] is None
        assert card["contract"]["ask"] is None
        assert card["status"]["active"] is False
        assert card["stats"]["season"] == {}
        assert card["stats"]["career"] == {}
        assert card["market"]["offers"] == []
        assert card["accolades"]["total_awards"] == 0
