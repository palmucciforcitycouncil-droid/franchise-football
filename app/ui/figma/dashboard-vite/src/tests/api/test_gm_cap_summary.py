import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, create_engine, SQLModel
from app.core.db import get_session
from app.main import app
from app.models.team import Team
from app.models.contracts import PlayerContract
from app.models.league import League
from app.models.settings import Settings

@pytest.fixture(name="seeded_db")
def seeded_db_fixture():
    """Fresh in-memory SQLite database for each test, seeded with cap data."""
    test_engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # Seed a team
        team = Team(id=1, abbr="BUF", city="Buffalo", name="Bills", conference="AFC", division="East")
        session.add(team)
        
        # Seed league cap data
        league = League(id=1, year=2025, salary_cap=255_000_000)
        session.add(league)
        
        # Seed growth rate settings
        settings = Settings(id=1, cap_growth_rate=5.0)
        session.add(settings)
        
        # Seed some contracts for the team
        contracts = [
            PlayerContract(
                id=1, player_id=1, team_id=1, start_season=2025, end_season=2027,
                aav=15_000_000, is_active=True
            ),
            PlayerContract(
                id=2, player_id=2, team_id=1, start_season=2025, end_season=2026,
                aav=12_000_000, is_active=True
            ),
            PlayerContract(
                id=3, player_id=3, team_id=1, start_season=2026, end_season=2028,
                aav=8_000_000, is_active=True
            ),
        ]
        session.add_all(contracts)
        
        session.commit()
        yield session

    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client")
def client_fixture(seeded_db: Session):
    """Test client that uses the seeded_db session."""
    def override_get_session():
        yield seeded_db
    
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

class TestGMCapSummaryAPI:
    """Test the GM cap summary API endpoint."""
    
    def test_cap_summary_success(self, client: TestClient, seeded_db: Session):
        """Test successful cap summary retrieval."""
        response = client.get("/api/gm/1/cap-summary?base_year=2025&horizon=3")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["team_id"] == 1
        assert data["base_year"] == 2025
        assert len(data["items"]) == 4  # base_year + 3 future years
        
        # Check structure of each item
        for item in data["items"]:
            assert "year" in item
            assert "team_obligations" in item
            assert "league_cap" in item
            assert "cap_space" in item
            assert "is_projected" in item
            
            # Verify cap_space calculation
            assert item["cap_space"] == item["league_cap"] - item["team_obligations"]
    
    def test_current_year_not_projected(self, client: TestClient, seeded_db: Session):
        """Test that current year is not marked as projected."""
        response = client.get("/api/gm/1/cap-summary?base_year=2025&horizon=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # First item should be current year (not projected)
        current_year_item = data["items"][0]
        assert current_year_item["year"] == 2025
        assert current_year_item["is_projected"] == False
        assert current_year_item["league_cap"] == 255_000_000  # Actual league cap
    
    def test_future_years_projected(self, client: TestClient, seeded_db: Session):
        """Test that future years are marked as projected."""
        response = client.get("/api/gm/1/cap-summary?base_year=2025&horizon=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # Future years should be projected
        for i in range(1, 4):
            future_item = data["items"][i]
            assert future_item["is_projected"] == True
            assert future_item["year"] == 2025 + i
    
    def test_cap_projection_rounding(self, client: TestClient, seeded_db: Session):
        """Test that projected caps are rounded down to nearest multiple of 5."""
        response = client.get("/api/gm/1/cap-summary?base_year=2025&horizon=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that all league caps are multiples of 5
        for item in data["items"]:
            assert item["league_cap"] % 5 == 0, f"League cap {item['league_cap']} should be multiple of 5"
    
    def test_team_obligations_calculation(self, client: TestClient, seeded_db: Session):
        """Test that team obligations are calculated correctly."""
        response = client.get("/api/gm/1/cap-summary?base_year=2025&horizon=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # 2025: 15M + 12M = 27M
        # 2026: 15M + 8M = 23M  
        # 2027: 15M + 8M = 23M
        # 2028: 8M = 8M
        
        expected_obligations = [27_000_000, 23_000_000, 23_000_000, 8_000_000]
        
        for i, expected in enumerate(expected_obligations):
            assert data["items"][i]["team_obligations"] == expected
    
    def test_cap_space_calculation(self, client: TestClient, seeded_db: Session):
        """Test that cap space is calculated correctly."""
        response = client.get("/api/gm/1/cap-summary?base_year=2025&horizon=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # 2025: 255M - 27M = 228M
        # 2026: 265M - 23M = 242M (projected cap)
        # 2027: 280M - 23M = 257M (projected cap)
        # 2028: 295M - 8M = 287M (projected cap)
        
        expected_cap_space = [228_000_000, 242_000_000, 257_000_000, 287_000_000]
        
        for i, expected in enumerate(expected_cap_space):
            assert data["items"][i]["cap_space"] == expected
    
    def test_invalid_team_id(self, client: TestClient, seeded_db: Session):
        """Test error handling for invalid team ID."""
        response = client.get("/api/gm/999/cap-summary?base_year=2025&horizon=3")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_invalid_base_year(self, client: TestClient, seeded_db: Session):
        """Test error handling for invalid base year."""
        response = client.get("/api/gm/1/cap-summary?base_year=1900&horizon=3")
        
        assert response.status_code == 400
        assert "between 2020 and 2050" in response.json()["detail"]
    
    def test_invalid_horizon(self, client: TestClient, seeded_db: Session):
        """Test error handling for invalid horizon."""
        response = client.get("/api/gm/1/cap-summary?base_year=2025&horizon=10")
        
        assert response.status_code == 422  # Validation error
    
    def test_default_horizon(self, client: TestClient, seeded_db: Session):
        """Test that default horizon is 3."""
        response = client.get("/api/gm/1/cap-summary?base_year=2025")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 4  # base_year + 3 future years
    
    def test_different_horizon_values(self, client: TestClient, seeded_db: Session):
        """Test different horizon values."""
        for horizon in [1, 2, 3, 4, 5]:
            response = client.get(f"/api/gm/1/cap-summary?base_year=2025&horizon={horizon}")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == horizon + 1  # base_year + horizon future years
    
    def test_no_contracts_team(self, client: TestClient, seeded_db: Session):
        """Test team with no contracts."""
        # Add a team with no contracts
        team2 = Team(id=2, abbr="MIA", city="Miami", name="Dolphins", conference="AFC", division="East")
        seeded_db.add(team2)
        seeded_db.commit()
        
        response = client.get("/api/gm/2/cap-summary?base_year=2025&horizon=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # All obligations should be 0
        for item in data["items"]:
            assert item["team_obligations"] == 0
            assert item["cap_space"] == item["league_cap"]
