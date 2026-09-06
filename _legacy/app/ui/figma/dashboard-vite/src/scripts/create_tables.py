#!/usr/bin/env python3
"""
Create database tables for progression system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import SQLModel, create_engine
from app.models.progression import PlayerProgression
from app.models.core_min import Team, Player, Game, TeamGame
from app.models.rollover import RolloverAudit
from app.models.season_stats import TeamSeasonStats, PlayerSeasonStats
from app.models.awards import AwardResult
from app.models.savegame import SaveGameAudit
from app.models.records import SingleSeasonRecord, CareerRecord
from app.models.draft import DraftClass, Prospect, DraftPick
from app.models.contracts import Contract
from app.models.cap import TeamCap
from app.services.contracts import FreeAgentBid, ReSignOffer

def main():
    engine = create_engine("sqlite:///franchise.db", future=True)
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully")

if __name__ == "__main__":
    main()
