#!/usr/bin/env python3
"""
Seed script for draft data.
Creates a realistic draft class with prospects and initializes picks.
"""

import random
from sqlmodel import Session
from app.db import get_engine, create_db_and_tables
from app.models.draft import Prospect, DraftPick, DraftState, PickStatus

def seed_draft_data():
    """Create draft prospects and initialize draft state."""
    # Create database tables
    create_db_and_tables()
    
    engine = get_engine()
    with Session(engine) as sess:
        # Clear existing data
        sess.exec("DELETE FROM prospect")
        sess.exec("DELETE FROM draftpick")
        sess.exec("DELETE FROM draftstate")
        sess.commit()
        
        # Create prospects (80 total)
        colleges = [
            "Alabama", "Ohio State", "Georgia", "Michigan", "Clemson", "LSU", 
            "USC", "Texas", "Oklahoma", "Florida", "Notre Dame", "Penn State",
            "Auburn", "Tennessee", "Miami", "Florida State", "Oregon", "Washington",
            "Utah", "Stanford", "UCLA", "Arizona State", "Colorado", "Texas A&M"
        ]
        
        positions = [
            "QB", "RB", "WR", "TE", "OT", "OG", "C", 
            "DE", "DT", "LB", "CB", "S", "K", "P"
        ]
        
        # Position-specific OVR ranges
        position_ovr_ranges = {
            "QB": (75, 95), "RB": (70, 90), "WR": (70, 92), "TE": (65, 88),
            "OT": (70, 90), "OG": (65, 88), "C": (65, 85),
            "DE": (70, 92), "DT": (70, 90), "LB": (70, 90),
            "CB": (70, 92), "S": (70, 88), "K": (60, 80), "P": (60, 80)
        }
        
        prospects = []
        for i in range(80):
            position = random.choice(positions)
            ovr_min, ovr_max = position_ovr_ranges[position]
            ovr = random.randint(ovr_min, ovr_max)
            
            # Generate realistic names
            first_names = [
                "James", "John", "Robert", "Michael", "William", "David", "Richard",
                "Charles", "Joseph", "Thomas", "Christopher", "Daniel", "Paul", "Mark",
                "Donald", "Steven", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
                "George", "Timothy", "Ronald", "Jason", "Edward", "Jeffrey", "Ryan"
            ]
            
            last_names = [
                "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
                "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
                "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark"
            ]
            
            prospect = Prospect(
                first_name=random.choice(first_names),
                last_name=random.choice(last_names),
                position=position,
                college=random.choice(colleges),
                ovr=ovr,
                draft_grade=round(ovr / 12.0, 1),  # Rough grade calculation
                board_rank=i + 1 if i < 20 else None
            )
            
            sess.add(prospect)
            prospects.append(prospect)
        
        sess.commit()
        
        # Create draft picks for 7 rounds × 32 picks
        picks = []
        pick_number = 1
        
        for round_no in range(1, 8):
            for pick_in_round in range(1, 33):
                # Simple team assignment (round-robin)
                team_id = ((pick_number - 1) % 32) + 1
                
                pick = DraftPick(
                    season_year=2024,
                    round_no=round_no,
                    pick_in_round=pick_in_round,
                    overall_pick=pick_number,
                    team_id=team_id,
                    selected_prospect_id=None,
                    status=PickStatus.PENDING
                )
                
                sess.add(pick)
                picks.append(pick)
                pick_number += 1
        
        sess.commit()
        
        # Create draft state (user team 1, current pick 1)
        state = DraftState(
            season_year=2024,
            current_pick_overall=1,
            user_team_id=1,
            is_paused=False,
            last_tick_utc=None
        )
        
        sess.add(state)
        sess.commit()
        
        print(f"✅ Created {len(prospects)} prospects")
        print(f"✅ Created {len(picks)} draft picks")
        print(f"✅ Created draft state for season {state.season_year}")
        print(f"✅ User team {state.user_team_id} is ready to draft!")

if __name__ == "__main__":
    seed_draft_data()