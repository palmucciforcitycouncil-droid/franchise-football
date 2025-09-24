from __future__ import annotations
from typing import Optional, Dict
from sqlmodel import SQLModel, Session, create_engine

# Re-export for tests that import Base
Base = SQLModel

# Ensure models are imported so tables are registered in SQLModel.metadata
for _mod in ("team", "player", "depth_chart", "game_result", "player_season_stats", "user_profile"):
    try:
        __import__(f"app.models.{_mod}")
    except Exception:
        # Keep database utilities import-safe even if a model is temporarily missing
        pass

# Simple per-URL engine cache so API/tests share the same engine instance
_ENGINE_CACHE: Dict[str, object] = {}

def get_engine(url: Optional[str] = None):
    if not url:
        url = "sqlite:///db/ff.db"
    engine = _ENGINE_CACHE.get(url)
    if engine is None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        engine = create_engine(url, echo=False, connect_args=connect_args)
        _ENGINE_CACHE[url] = engine
    return engine

def create_db_and_tables(url: Optional[str] = None):
    engine = get_engine(url)
    # Create all tables; connecting once will also materialize a sqlite file on disk
    with engine.begin() as conn:
        SQLModel.metadata.create_all(conn)

def get_session(url: Optional[str] = None):
    """
    FastAPI-friendly dependency/generator:
      from app.models.database import get_session
      def endpoint(db: Session = Depends(get_session)): ...
    """
    engine = get_engine(url)
    with Session(engine) as session:
        yield session
