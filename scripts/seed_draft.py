#!/usr/bin/env python3
"""
Seed script for draft data - creates faux prospects and initializes draft picks.
Run with: python scripts/seed_draft.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, func, delete
from app.core.db import engine, create_db_and_tables
from app.models.draft import Prospect, DraftPick, DraftState, PickStatus
from datetime import datetime
import random

def seed_draft_data():
    """Create draft data for testing."""
    create_db_and_tables()
    
    with Session(engine) as session:
        # Clear existing data
        session.exec(delete(DraftPick))
        session.exec(delete(Prospect))
        session.exec(delete(DraftState))
        session.commit()
        
        # Create prospects
        positions = ["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                    "DE", "DT", "LB", "CB", "S", "K", "P"]
        colleges = ["Alabama", "Ohio State", "Georgia", "Michigan", "Texas", 
                   "USC", "Notre Dame", "LSU", "Clemson", "Florida State"]
        first_names = ["John", "Mike", "David", "Chris", "Ryan", "Matt", "Josh", "Nick", "Tom", "Ben"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        
        prospects = []
        for i in range(1, 201):  # 200 prospects
            ovr = random.randint(60, 95)
            grade = round(random.uniform(5.0, 8.5), 1)
            pos = random.choice(positions)
            college = random.choice(colleges)
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            prospects.append(Prospect(
                prospect_id=i,
                first_name=first_name,
                last_name=last_name,
                position=pos,
                college=college,
                ovr=ovr,
                draft_grade=grade
            ))
        
        session.add_all(prospects)
        session.commit()
        
        # Create draft picks for 7 rounds * 32 teams
        season_year = 2025
        overall_pick_counter = 1
        team_ids = list(range(1, 33))  # 32 teams
        random.shuffle(team_ids)  # Randomize initial pick order
        
        draft_picks = []
        for round_no in range(1, 8):
            current_round_teams = list(team_ids)
            if round_no > 1:  # Snake draft logic
                if round_no % 2 == 0:  # Even rounds reverse order
                    current_round_teams.reverse()
            
            for pick_in_round in range(1, 33):
                team_id = current_round_teams[pick_in_round - 1]
                draft_picks.append(DraftPick(
                    season_year=season_year,
                    round_no=round_no,
                    pick_in_round=pick_in_round,
                    overall_pick=overall_pick_counter,
                    team_id=team_id,
                    status=PickStatus.PENDING
                ))
                overall_pick_counter += 1
        
        session.add_all(draft_picks)
        
        # Create draft state
        draft_state = DraftState(
            season_year=season_year,
            current_pick_overall=1,
            user_team_id=1,  # User controls Team 1
            is_paused=False,
            last_tick_utc=datetime.utcnow()
        )
        session.add(draft_state)
        session.commit()
        
        print(f"Seeded {len(prospects)} prospects and {len(draft_picks)} draft picks for season {season_year}")
        print(f"Draft state initialized with user_team_id={draft_state.user_team_id}")

if __name__ == "__main__":
    seed_draft_data()
