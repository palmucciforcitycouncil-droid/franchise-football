# app/db.py
from __future__ import annotations
from sqlmodel import create_engine, Session, SQLModel

def get_engine():
    """Get database engine - using franchise.db for consistency."""
    return create_engine("sqlite:///franchise.db", future=True)

def get_session():
    """Get database session for dependency injection."""
    engine = get_engine()
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """Create database tables for all models."""
    # Import all models to ensure they're registered
    from app.models.draft import Prospect, DraftPick, DraftState  # noqa: F401
    from app.models.results import TeamGameStats, PlayerBox  # noqa: F401
    from app.models.sim_models import Team, Game, GameEvent  # noqa: F401
    
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
