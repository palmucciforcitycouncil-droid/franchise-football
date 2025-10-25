import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from app.main import app

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def seeded_db():
    """Fresh database session for each test."""
    # Create a fresh in-memory database for each test
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Import all models to ensure they're registered
    from app.models.sim_models import Team, Game, GameEvent  # noqa: F401
    from app.models.stats import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats, PlayerCareerStats  # noqa: F401
    from app.models.defense_stats import TeamDefenseStatsWeekly, PlayerDefenseStatsWeekly  # noqa: F401
    from app.models.results import TeamGameStats, PlayerBox  # noqa: F401
    
    # Create all tables
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as sess:
        yield sess
