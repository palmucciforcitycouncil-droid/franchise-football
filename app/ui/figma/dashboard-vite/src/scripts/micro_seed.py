#!/usr/bin/env python3
"""
Micro Seed Script - Create minimal database tables and seed data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import SQLModel, create_engine, Session, select
from app.models.core_min import Team, Game, TeamGame, Player

TEAMS = [
    ("BUF","Bills"),("KC","Chiefs"),("PHI","Eagles"),("DAL","Cowboys"),
    ("SF","49ers"),("BAL","Ravens"),("CIN","Bengals"),("DET","Lions")
]

def ensure_tables(engine):
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(engine)

def seed_min(engine, season=2025, week=1):
    """Seed the database with minimal data."""
    with Session(engine) as s:
        # teams
        existing = s.exec(select(Team)).all()
        if not existing:
            for abbr,name in TEAMS:
                s.add(Team(abbrev=abbr, name=name))
            s.commit()
        
        teams = s.exec(select(Team)).all()
        ids = [t.id for t in teams]
        
        # players (one QB, K, P per team)
        has_players = s.exec(select(Player)).first()
        if not has_players:
            for t in teams:
                s.add(Player(team_id=t.id, pos="QB", name=f"{t.abbrev} QB", rating=75))
                s.add(Player(team_id=t.id, pos="K",  name=f"{t.abbrev} K",  rating=70, kicker_power=0.6, kicker_base_40_49=0.85))
                s.add(Player(team_id=t.id, pos="P",  name=f"{t.abbrev} P",  rating=70))
            s.commit()
        
        # games (round-robin pairs)
        existing_g = s.exec(select(Game)).all()
        if not existing_g:
            pairs = [(ids[i], ids[i+1]) for i in range(0, len(ids), 2)]
            gid = 1
            for (home, away) in pairs:
                g = Game(id=gid, season=season, week=week, home_team_id=home, away_team_id=away)
                s.add(g)
                s.commit()
                s.add(TeamGame(game_id=g.id, team_id=home, is_home=True))
                s.add(TeamGame(game_id=g.id, team_id=away, is_home=False))
                gid += 1
            s.commit()

if __name__ == "__main__":
    eng = create_engine("sqlite:///franchise.db", future=True)
    ensure_tables(eng)
    seed_min(eng)
    print("Micro-seed done: Teams/Games/TeamGames/Players created.")
