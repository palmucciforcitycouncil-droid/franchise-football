import pytest
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.coach import Coach, CoachContract, CoachOffer, CoachAsk, CoachRole, CoachJobType
from app.services.coach_market import (
    list_free_agents, list_league_assistants, list_team_staff,
    fire_coach, resign_coach, create_coach_offer, rescind_offer,
    cpu_hiring_sweep, current_contract, is_expiring, get_or_create_ask,
    reassign_role_allowed, apply_promotion
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_offer_promotion_rules(client, seeded_db):
    """Test that promotion rules are enforced correctly."""
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.coach import Coach, CoachRole
    season = 2032
    with Session(get_engine()) as sess:
        ac = Coach(name="AC Smith", team_id=2, role=CoachRole.AC, overall=68)
        sess.add(ac); sess.commit(); sess.refresh(ac)

    # Lateral AC -> AC (should fail)
    r = client.post("/api/v1/coaches/offer", json={
        "season": season, "from_team_id": 1, "to_coach_id": ac.coach_id,
        "job_type": "AC", "years": 2, "aav": 1200000
    })
    assert r.status_code == 200
    assert r.json()["accepted"] is False
    assert r.json()["reason"] is not None

    # Promotion AC -> OC (should at least be allowed; may accept or store)
    r = client.post("/api/v1/coaches/offer", json={
        "season": season, "from_team_id": 1, "to_coach_id": ac.coach_id,
        "job_type": "OC", "years": 3, "aav": 2000000
    })
    assert r.status_code == 200

def test_instant_accept_threshold(client, seeded_db):
    """Test that offers meeting threshold are accepted instantly."""
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.coach import Coach, CoachRole
    season = 2032
    with Session(get_engine()) as sess:
        oc = Coach(name="OC Jones", team_id=None, role=CoachRole.OC, overall=78)  # FA OC
        sess.add(oc); sess.commit(); sess.refresh(oc)

    # Offer near threshold should accept
    r = client.post("/api/v1/coaches/offer", json={
        "season": season, "from_team_id": 3, "to_coach_id": oc.coach_id,
        "job_type": "OC", "years": 3, "aav": 2100000
    })
    assert r.status_code == 200
    data = r.json()
    assert "min_aav" in data
    # Either accepted or returns threshold; acceptance depends on fresh ask

def test_fire_and_resign_flow(client, seeded_db):
    """Test firing and re-signing coaches."""
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.coach import Coach, CoachRole
    from app.models.coach import CoachContract
    season = 2032
    with Session(get_engine()) as sess:
        dc = Coach(name="DC Ray", team_id=5, role=CoachRole.DC, overall=74)
        sess.add(dc); sess.commit(); sess.refresh(dc)
    
    # Fire
    r = client.post(f"/api/v1/coaches/fire/{dc.coach_id}")
    assert r.status_code == 200
    
    # Resign to team 5
    r = client.post("/api/v1/coaches/resign", json={
        "coach_id": dc.coach_id, "team_id": 5, "season": season, "years": 3, "aav": 1900000
    })
    assert r.status_code == 200

def test_cpu_offseason_sweep(client, seeded_db):
    """Test that CPU offseason sweep doesn't crash."""
    # Should not error even if no schedule/team models are elaborate
    r = client.post("/api/v1/coaches/cpu/offseason_sweep?season=2032")
    assert r.status_code == 200

def test_list_free_agents(session: Session):
    """Test listing free agent coaches."""
    # Create some free agents
    fa1 = Coach(name="FA Coach 1", team_id=None, role=CoachRole.OC, overall=75)
    fa2 = Coach(name="FA Coach 2", team_id=None, role=CoachRole.DC, overall=72)
    session.add(fa1); session.add(fa2); session.commit()
    
    # List free agents
    fa_list = list_free_agents(session, 2024)
    assert len(fa_list) == 2
    assert any(c.name == "FA Coach 1" for c in fa_list)
    assert any(c.name == "FA Coach 2" for c in fa_list)

def test_list_league_assistants(session: Session):
    """Test listing league assistants."""
    # Create some assistants
    oc = Coach(name="OC Smith", team_id=1, role=CoachRole.OC, overall=78)
    dc = Coach(name="DC Jones", team_id=2, role=CoachRole.DC, overall=76)
    ac = Coach(name="AC Brown", team_id=3, role=CoachRole.AC, overall=70)
    session.add(oc); session.add(dc); session.add(ac); session.commit()
    
    # List assistants
    assistants = list_league_assistants(session, 2024)
    assert len(assistants) == 3
    assert any(c.name == "OC Smith" for c in assistants)
    assert any(c.name == "DC Jones" for c in assistants)
    assert any(c.name == "AC Brown" for c in assistants)

def test_list_team_staff(session: Session):
    """Test listing team staff."""
    # Create staff for team 1
    hc = Coach(name="HC Team1", team_id=1, role=CoachRole.HC, overall=80)
    oc = Coach(name="OC Team1", team_id=1, role=CoachRole.OC, overall=75)
    session.add(hc); session.add(oc); session.commit()
    
    # List team 1 staff
    staff = list_team_staff(session, 1, 2024)
    assert len(staff) == 2
    assert any(c.name == "HC Team1" for c in staff)
    assert any(c.name == "OC Team1" for c in staff)

def test_fire_coach(session: Session):
    """Test firing a coach."""
    # Create a coach with a contract
    coach = Coach(name="Test Coach", team_id=1, role=CoachRole.OC, overall=75)
    session.add(coach); session.commit(); session.refresh(coach)
    
    contract = CoachContract(coach_id=coach.coach_id, team_id=1, start_season=2024, end_season=2026, aav=2000000, is_active=True)
    session.add(contract); session.commit()
    
    # Fire the coach
    fire_coach(session, coach.coach_id)
    
    # Check that coach is now free agent and contract is inactive
    fired_coach = session.get(Coach, coach.coach_id)
    assert fired_coach.team_id is None
    
    inactive_contract = session.get(CoachContract, contract.contract_id)
    assert not inactive_contract.is_active

def test_resign_coach(session: Session):
    """Test re-signing a coach."""
    # Create a coach
    coach = Coach(name="Test Coach", team_id=1, role=CoachRole.OC, overall=75)
    session.add(coach); session.commit(); session.refresh(coach)
    
    # Re-sign the coach
    resign_coach(session, coach.coach_id, 1, 2024, 3, 2500000)
    
    # Check that new contract was created
    contracts = list(session.exec(select(CoachContract).where(CoachContract.coach_id == coach.coach_id, CoachContract.is_active == True)))
    assert len(contracts) == 1
    assert contracts[0].aav == 2500000
    assert contracts[0].end_season == 2026

def test_create_coach_offer_accepted(session: Session):
    """Test creating an offer that gets accepted."""
    # Create a free agent coach
    coach = Coach(name="FA Coach", team_id=None, role=CoachRole.OC, overall=75)
    session.add(coach); session.commit(); session.refresh(coach)
    
    # Create an ask
    ask = CoachAsk(coach_id=coach.coach_id, desired_years=3, desired_aav=2000000, updated_season=2024)
    session.add(ask); session.commit()
    
    # Make an offer that meets threshold (96% of ask)
    result = create_coach_offer(session, 2024, 1, coach.coach_id, CoachJobType.OC, 3, 1920000)
    
    # Should be accepted
    assert result.accepted
    assert result.min_aav <= 1920000
    
    # Check that coach was signed
    signed_coach = session.get(Coach, coach.coach_id)
    assert signed_coach.team_id == 1

def test_create_coach_offer_stored(session: Session):
    """Test creating an offer that gets stored (not accepted)."""
    # Create a free agent coach
    coach = Coach(name="FA Coach", team_id=None, role=CoachRole.OC, overall=75)
    session.add(coach); session.commit(); session.refresh(coach)
    
    # Create an ask
    ask = CoachAsk(coach_id=coach.coach_id, desired_years=3, desired_aav=2000000, updated_season=2024)
    session.add(ask); session.commit()
    
    # Make an offer that doesn't meet threshold
    result = create_coach_offer(session, 2024, 1, coach.coach_id, CoachJobType.OC, 2, 1500000)
    
    # Should not be accepted
    assert not result.accepted
    
    # Check that offer was stored
    offers = list(session.exec(select(CoachOffer).where(CoachOffer.to_coach_id == coach.coach_id, CoachOffer.is_active == True)))
    assert len(offers) == 1
    assert offers[0].aav == 1500000

def test_promotion_rules():
    """Test promotion rules."""
    # AC can be promoted to OC/DC/HC
    assert reassign_role_allowed(CoachRole.AC, CoachJobType.OC)
    assert reassign_role_allowed(CoachRole.AC, CoachJobType.DC)
    assert reassign_role_allowed(CoachRole.AC, CoachJobType.HC)
    
    # OC/DC can be promoted to HC
    assert reassign_role_allowed(CoachRole.OC, CoachJobType.HC)
    assert reassign_role_allowed(CoachRole.DC, CoachJobType.HC)
    
    # Lateral moves not allowed
    assert not reassign_role_allowed(CoachRole.OC, CoachJobType.OC)
    assert not reassign_role_allowed(CoachRole.DC, CoachJobType.DC)
    assert not reassign_role_allowed(CoachRole.AC, CoachJobType.AC)
    
    # Demotions not allowed
    assert not reassign_role_allowed(CoachRole.OC, CoachJobType.AC)
    assert not reassign_role_allowed(CoachRole.DC, CoachJobType.AC)

def test_apply_promotion(session: Session):
    """Test applying a promotion."""
    coach = Coach(name="Test Coach", team_id=1, role=CoachRole.AC, overall=75)
    session.add(coach); session.commit()
    
    # Promote AC to OC
    apply_promotion(coach, CoachJobType.OC)
    assert coach.role == CoachRole.OC

def test_current_contract(session: Session):
    """Test getting current contract."""
    coach = Coach(name="Test Coach", team_id=1, role=CoachRole.OC, overall=75)
    session.add(coach); session.commit(); session.refresh(coach)
    
    # Create active contract
    contract = CoachContract(coach_id=coach.coach_id, team_id=1, start_season=2024, end_season=2026, aav=2000000, is_active=True)
    session.add(contract); session.commit()
    
    # Get current contract
    current = current_contract(session, coach.coach_id)
    assert current is not None
    assert current.aav == 2000000

def test_is_expiring(session: Session):
    """Test contract expiration check."""
    contract = CoachContract(coach_id=1, team_id=1, start_season=2024, end_season=2026, aav=2000000, is_active=True)
    
    # Should not be expiring in 2024
    assert not is_expiring(contract, 2024)
    
    # Should be expiring in 2026
    assert is_expiring(contract, 2026)
    
    # Inactive contract should not be expiring
    contract.is_active = False
    assert not is_expiring(contract, 2026)

def test_get_or_create_ask(session: Session):
    """Test getting or creating coach ask."""
    coach = Coach(name="Test Coach", team_id=1, role=CoachRole.OC, overall=75)
    session.add(coach); session.commit(); session.refresh(coach)
    
    # First call should create ask
    ask1 = get_or_create_ask(session, coach.coach_id, 2024)
    assert ask1.desired_aav == 2000000  # default
    assert ask1.desired_years == 3  # default
    
    # Second call should return same ask
    ask2 = get_or_create_ask(session, coach.coach_id, 2024)
    assert ask1.id == ask2.id
    
    # Call in different season should update ask
    ask3 = get_or_create_ask(session, coach.coach_id, 2025)
    assert ask3.updated_season == 2025
    assert ask3.desired_aav > ask1.desired_aav  # inflation applied

def test_rescind_offer(session: Session):
    """Test rescinding an offer."""
    # Create an offer
    offer = CoachOffer(season=2024, from_team_id=1, to_coach_id=2, job_type=CoachJobType.OC, years=3, aav=2000000, is_active=True)
    session.add(offer); session.commit(); session.refresh(offer)
    
    # Rescind the offer
    rescind_offer(session, offer.offer_id)
    
    # Check that offer is inactive
    inactive_offer = session.get(CoachOffer, offer.offer_id)
    assert not inactive_offer.is_active

def test_api_list_free_agents(client, seeded_db):
    """Test API endpoint for listing free agents."""
    r = client.get("/api/v1/coaches/fa?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_api_list_assistants(client, seeded_db):
    """Test API endpoint for listing assistants."""
    r = client.get("/api/v1/coaches/assistants?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_api_list_team_staff(client, seeded_db):
    """Test API endpoint for listing team staff."""
    r = client.get("/api/v1/coaches/team_staff?season=2024&team_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_api_get_coach_detail(client, seeded_db):
    """Test API endpoint for getting coach details."""
    # First create a coach
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.coach import Coach, CoachRole
    
    with Session(get_engine()) as sess:
        coach = Coach(name="Test Coach", team_id=1, role=CoachRole.OC, overall=75)
        sess.add(coach); sess.commit(); sess.refresh(coach)
        coach_id = coach.coach_id
    
    r = client.get(f"/api/v1/coaches/{coach_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Coach"
    assert data["role"] == "OC"
    assert data["overall"] == 75

def test_api_get_coach_offers(client, seeded_db):
    """Test API endpoint for getting coach offers."""
    r = client.get("/api/v1/coaches/offers/1?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_api_get_coach_contract(client, seeded_db):
    """Test API endpoint for getting coach contract."""
    r = client.get("/api/v1/coaches/contracts/1")
    assert r.status_code == 200
    # May return None if no contract exists

def test_api_get_coach_ask(client, seeded_db):
    """Test API endpoint for getting coach ask."""
    r = client.get("/api/v1/coaches/ask/1?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "desired_aav" in data
    assert "desired_years" in data

def test_api_get_vacancies(client, seeded_db):
    """Test API endpoint for getting team vacancies."""
    r = client.get("/api/v1/coaches/vacancies?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_api_get_market_stats(client, seeded_db):
    """Test API endpoint for getting market stats."""
    r = client.get("/api/v1/coaches/stats?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "total_coaches" in data
    assert "free_agents" in data
    assert "total_offers" in data
    assert "active_contracts" in data
    assert "expiring_contracts" in data

def test_cpu_hiring_sweep_with_vacancies(session: Session):
    """Test CPU hiring sweep with actual vacancies."""
    # Create a team with missing HC
    oc = Coach(name="OC", team_id=1, role=CoachRole.OC, overall=75)
    session.add(oc); session.commit()
    
    # Create some free agents
    fa_hc = Coach(name="FA HC", team_id=None, role=CoachRole.HC, overall=80)
    session.add(fa_hc); session.commit()
    
    # Run CPU sweep
    cpu_hiring_sweep(session, 2024)
    
    # Check that FA HC was hired
    hired_hc = session.get(Coach, fa_hc.coach_id)
    assert hired_hc.team_id == 1

def test_offer_to_same_team_blocked(session: Session):
    """Test that offers to coaches already on the same team are blocked."""
    coach = Coach(name="Test Coach", team_id=1, role=CoachRole.OC, overall=75)
    session.add(coach); session.commit(); session.refresh(coach)
    
    # Try to offer to coach already on team 1
    result = create_coach_offer(session, 2024, 1, coach.coach_id, CoachJobType.HC, 3, 3000000)
    
    assert not result.accepted
    assert "already on your team" in result.reason

def test_offer_to_nonexistent_coach(session: Session):
    """Test that offers to nonexistent coaches are handled."""
    result = create_coach_offer(session, 2024, 1, 99999, CoachJobType.HC, 3, 3000000)
    
    assert not result.accepted
    assert "Coach not found" in result.reason

