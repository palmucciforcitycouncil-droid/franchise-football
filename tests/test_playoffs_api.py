import pytest
from sqlmodel import Session, create_engine, SQLModel
from fastapi.testclient import TestClient
from app.main import app
from app.models.team import Team, Conference, Division

# Test database
engine = create_engine("sqlite:///:memory:", echo=False)

@pytest.fixture
def db_session():
    """Create a test database session"""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)

@pytest.fixture
def seed_teams_32(db_session):
    """Seed 32 teams (16 AFC, 16 NFC) for testing"""
    teams = []
    # AFC teams
    for i in range(16):
        team = Team(
            id=100+i,
            location_name=f"AFC Team {i+1}",
            nickname=f"Team{i+1}",
            conference=Conference.AFC,
            division=Division.EAST if i < 4 else Division.NORTH if i < 8 else Division.SOUTH if i < 12 else Division.WEST,
            wins=12-i%4,
            losses=i%4,
            power_rating=1500+i
        )
        teams.append(team)
        db_session.add(team)
    
    # NFC teams
    for i in range(16):
        team = Team(
            id=200+i,
            location_name=f"NFC Team {i+1}",
            nickname=f"Team{i+1}",
            conference=Conference.NFC,
            division=Division.EAST if i < 4 else Division.NORTH if i < 8 else Division.SOUTH if i < 12 else Division.WEST,
            wins=11-i%4,
            losses=i%4,
            power_rating=1400+i
        )
        teams.append(team)
        db_session.add(team)
    
    db_session.commit()
    return teams

def test_api_playoffs_smoke(client, db_session, seed_teams_32):
    # assumes test fixtures that insert 32 teams into DB
    resp = client.get("/api/playoffs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["season_year"] == 2025
    assert any(r["round_name"]=="WC" for r in data["rounds"])
