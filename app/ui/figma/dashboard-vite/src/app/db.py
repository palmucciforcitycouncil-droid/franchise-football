# app/db.py
from __future__ import annotations
from sqlmodel import create_engine, Session

def get_engine():
    """Get database engine - using franchise.db for consistency."""
    return create_engine("sqlite:///franchise.db", future=True)
