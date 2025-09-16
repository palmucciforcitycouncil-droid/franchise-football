"""
Database helpers for Franchise Football (SQLAlchemy 2.x).

- engine: low-level connector to SQLite
- Base: declarative base class for ORM models
- SessionLocal: factory that makes DB sessions
- get_engine(): return the configured engine
- create_db_and_tables(): import model modules safely, then create tables
- get_session(): context manager for sessions (use 'with')

Notes (plain language):
- A "context manager" lets you write 'with get_session() as session:'.
  It takes care of commit/rollback/close automatically.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from importlib import import_module
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Paths & Engine -------------------------------------------------------

# Ensure the data directory exists (so SQLite file can be created there)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# SQLite file lives under app/data/franchise.db
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'franchise.db')}"

# The engine is the low-level connector to SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite on Windows with threads
    future=True,
)

# --- Declarative Base & Session factory -----------------------------------

# Base class for all ORM models (your models should subclass this)
Base = declarative_base()

# Session factory (creates new DB sessions)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)

# --- Internal: robust model importer --------------------------------------

def _import_model_modules() -> None:
    """
    Import model submodules by fully-qualified path so we don't rely on
    app.models.__init__ exposing them. Missing modules are skipped.
    """
    candidates = [
        "app.models.team",
        "app.models.player",
        "app.models.depth_chart",
        "app.models.game_result",
        "app.models.player_season_stats",  # may not exist yet in your repo
        "app.models.user_profile",
    ]
    for mod in candidates:
        try:
            import_module(mod)
        except ModuleNotFoundError:
            # file not present; okay to skip
            continue
        except ImportError:
            # present but import failed; re-raise so you can see the real error
            raise

# --- Public Helpers --------------------------------------------------------

def get_engine():
    """Return the SQLAlchemy engine."""
    return engine

def create_db_and_tables() -> None:
    """
    Create all tables if they don't exist.
    Important: we import model modules FIRST so their tables are registered.
    """
    _import_model_modules()
    Base.metadata.create_all(engine)

@contextmanager
def get_session():
    """
    Context-managed database session.

    Usage (plain language):
        with get_session() as session:
            # do DB work
            session.add(obj)

    It will COMMIT if all goes well, or ROLLBACK if there is an error,
    and always CLOSE the session at the end.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
