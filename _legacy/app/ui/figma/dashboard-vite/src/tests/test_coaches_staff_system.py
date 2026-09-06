# tests/test_coaches_staff_system.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import get_engine
from app.models.coach import Coach, CoachContract, CoachRole, CoachFocus
from app.models.core_min import Team
from datetime import date

client = TestClient(app)

def test_coach_model_creation(tmp_path):
    """Test Coach model creation and properties."""
    coach = Coach(
        first_name="John",
        last_name="Smith",
        age=45,
        role="HC",
        team_id=1,
        overall=85,
        off_rating=80,
        def_rating=90,
        st_rating=75,
        dev_rating=85,
        discipline=80,
        focus="OFF_GAMEPLAN"
    )
    
    assert coach.name == "John Smith"
    assert coach.role == "HC"
    assert coach.overall == 85
    assert coach.focus == "OFF_GAMEPLAN"

def test_coach_contract_model(tmp_path):
    """Test CoachContract model creation."""
    contract = CoachContract(
        coach_id=1,
        team_id=1,
        signed_on=date.today(),
        start_season=2025,
        end_season=2027,
        aav=3_000_000,
        is_active=True,
        acquired_via="HIRE"
    )
    
    assert contract.coach_id == 1
    assert contract.team_id == 1
    assert contract.aav == 3_000_000
    assert contract.is_active is True

def test_staff_service_queries(tmp_path):
    """Test staff service query functions."""
    from app.services.staff_service import get_team_staff, get_free_agent_coaches
    
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coaches
        coach1 = Coach(
            first_name="John", last_name="Smith", age=45, role="HC",
            team_id=team.id, overall=85, off_rating=80, def_rating=90
        )
        coach2 = Coach(
            first_name="Jane", last_name="Doe", age=40, role="OC",
            team_id=None, overall=80, off_rating=85, def_rating=75
        )
        s.add(coach1)
        s.add(coach2)
        s.commit()
        
        # Test queries
        team_staff = get_team_staff(s, team.id)
        assert len(team_staff) == 1
        assert team_staff[0].name == "John Smith"
        
        fa_coaches = get_free_agent_coaches(s)
        assert len(fa_coaches) == 1
        assert fa_coaches[0].name == "Jane Doe"

def test_coach_ai_acceptance_logic(tmp_path):
    """Test coach AI acceptance logic."""
    from app.services.coach_ai import coach_accepts, Offer
    
    # Test high-rated HC
    hc = Coach(
        role="HC", overall=90, off_rating=85, def_rating=95
    )
    
    # Good offer for HC
    good_offer = Offer(aav=4_000_000, years=4)
    assert coach_accepts(good_offer, hc, promotion=False) is True
    
    # Poor offer for HC
    poor_offer = Offer(aav=1_000_000, years=1)
    assert coach_accepts(poor_offer, hc, promotion=False) is False
    
    # Test promotion bonus
    oc = Coach(role="OC", overall=85, off_rating=80, def_rating=90)
    promotion_offer = Offer(aav=3_500_000, years=4)  # Lower than normal HC ask
    assert coach_accepts(promotion_offer, oc, promotion=True) is True

def test_coach_modifiers_computation(tmp_path):
    """Test coach modifiers computation."""
    from app.services.coach_modifiers import compute_team_modifiers
    
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coaches with different focuses
        hc = Coach(
            first_name="John", last_name="Smith", age=45, role="HC",
            team_id=team.id, overall=85, off_rating=80, def_rating=90,
            st_rating=75, dev_rating=85, discipline=80,
            focus="OFF_GAMEPLAN", weeks_focus_bank=10
        )
        oc = Coach(
            first_name="Jane", last_name="Doe", age=40, role="OC",
            team_id=team.id, overall=80, off_rating=85, def_rating=75,
            st_rating=70, dev_rating=80, discipline=75,
            focus="TWO_MIN_OFFENSE", weeks_focus_bank=8
        )
        s.add(hc)
        s.add(oc)
        s.commit()
        
        # Test modifiers computation
        mods = compute_team_modifiers(s, team.id)
        assert mods.off_gameplan > 0  # HC focusing on offense
        assert mods.two_min_offense > 0  # OC focusing on two-minute offense
        assert mods.discipline > 0  # HC oversight bonus

def test_staff_api_endpoints(tmp_path):
    """Test staff API endpoints."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coach
        coach = Coach(
            first_name="John", last_name="Smith", age=45, role="HC",
            team_id=team.id, overall=85, off_rating=80, def_rating=90,
            st_rating=75, dev_rating=85, discipline=80,
            focus="OFF_GAMEPLAN", weeks_focus_bank=0
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Test team staff endpoint
        res = client.get(f"/api/v1/staff/team?team_id={team.id}")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["name"] == "John Smith"
        assert data[0]["role"] == "HC"
        
        # Test free agents endpoint
        res = client.get("/api/v1/staff/free_agents")
        assert res.status_code == 200
        data = res.json()
        # Should be empty since coach is on team
        
        # Test poachable endpoint
        res = client.get("/api/v1/staff/poachable")
        assert res.status_code == 200
        data = res.json()
        # Should be empty since only HC exists

def test_staff_api_offer_endpoint(tmp_path):
    """Test staff offer endpoint."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create free agent coach
        coach = Coach(
            first_name="Jane", last_name="Doe", age=40, role="AC",
            team_id=None, overall=80, off_rating=85, def_rating=75,
            st_rating=70, dev_rating=80, discipline=75,
            focus="OFF_GAMEPLAN", weeks_focus_bank=0
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Test offer endpoint
        offer_data = {
            "aav": 2_000_000,
            "years": 3,
            "role": "OC",
            "team_id": team.id,
            "season": 2025
        }
        
        res = client.post(f"/api/v1/staff/offer/{coach.coach_id}", json=offer_data)
        assert res.status_code == 200
        data = res.json()
        assert "accepted" in data
        # Result depends on AI logic, but should be consistent

def test_staff_api_fire_endpoint(tmp_path):
    """Test staff fire endpoint."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coach
        coach = Coach(
            first_name="John", last_name="Smith", age=45, role="HC",
            team_id=team.id, overall=85, off_rating=80, def_rating=90,
            st_rating=75, dev_rating=85, discipline=80,
            focus="OFF_GAMEPLAN", weeks_focus_bank=0
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Test fire endpoint
        res = client.post(f"/api/v1/staff/fire/{coach.coach_id}")
        assert res.status_code == 200
        assert res.json()["ok"] is True
        
        # Verify coach moved to FA
        s.refresh(coach)
        assert coach.team_id is None
        assert coach.role == "AC"  # Neutralized role

def test_staff_api_focus_endpoint(tmp_path):
    """Test staff focus endpoint."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coach
        coach = Coach(
            first_name="John", last_name="Smith", age=45, role="HC",
            team_id=team.id, overall=85, off_rating=80, def_rating=90,
            st_rating=75, dev_rating=85, discipline=80,
            focus="OFF_GAMEPLAN", weeks_focus_bank=0
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Test focus endpoint
        focus_data = {"focus": "DEF_GAMEPLAN"}
        res = client.post(f"/api/v1/staff/focus/{coach.coach_id}", json=focus_data)
        assert res.status_code == 200
        assert res.json()["ok"] is True
        
        # Verify focus changed
        s.refresh(coach)
        assert coach.focus == "DEF_GAMEPLAN"

def test_simulation_integration(tmp_path):
    """Test simulation integration."""
    from app.engine.game_sim_adapter import get_team_sim_mods
    
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coaches
        hc = Coach(
            first_name="John", last_name="Smith", age=45, role="HC",
            team_id=team.id, overall=85, off_rating=80, def_rating=90,
            st_rating=75, dev_rating=85, discipline=80,
            focus="OFF_GAMEPLAN", weeks_focus_bank=10
        )
        s.add(hc)
        s.commit()
        
        # Test simulation modifiers
        mods = get_team_sim_mods(s, team.id)
        assert "offense_eff" in mods
        assert "defense_eff" in mods
        assert "two_min_bonus" in mods
        assert "st_bonus" in mods
        assert "discipline_bonus" in mods
        assert "stamina_injury" in mods
        assert isinstance(mods["offense_eff"], float)
        assert isinstance(mods["defense_eff"], float)


