#!/usr/bin/env python3
"""
Create database tables for progression system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import SQLModel, create_engine
from app.models.progression import PlayerProgression

def main():
    engine = create_engine("sqlite:///franchise.db", future=True)
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully")

if __name__ == "__main__":
    main()
