#!/usr/bin/env python3
"""
CLI script to print awards and leaders.
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, create_engine, select
from app.services.awards import compute_season_awards, compute_super_bowl_mvp, compute_league_leaders
from app.models.awards import AwardWinner
from app.testing.mini_season_runner import memory_db, run_mini_season


def print_awards_and_leaders():
    """Print awards and leaders for a mini season."""
    print("Season Awards and Leaders")
    print("=" * 50)
    
    with memory_db() as session:
        # Run mini season
        out = run_mini_season(session, weeks=2)
        season = 2025
        
        print(f"Generated {len(out['teams'])} teams, {len(out['games'])} games")
        print()
        
        # Compute season awards
        print("Computing season awards...")
        res = compute_season_awards(session, season)
        
        print("Season Awards:")
        print("-" * 20)
        for award, winner in res.items():
            if winner is not None and winner != -1:
                print(f"{award}: Player {winner}")
            else:
                print(f"{award}: No qualified winner")
        print()
        
        # Compute league leaders
        print("Computing league leaders...")
        boards = compute_league_leaders(session, season, top_n=5)
        
        print("League Leaders:")
        print("-" * 20)
        for board in boards:
            print(f"\n{board.title}")
            for i, row in enumerate(board.leaders, 1):
                print(f"  {i}. Player {row.player_id} (Team {row.team_id}): {row.value}")
        print()
        
        # Compute Super Bowl MVP if we have games
        if out.get("games"):
            champ_game_id = out["games"][-1]
            print(f"Computing Super Bowl MVP for game {champ_game_id}...")
            sb_mvp = compute_super_bowl_mvp(session, season, champ_game_id)
            
            if sb_mvp:
                print(f"Super Bowl MVP: Player {sb_mvp}")
            else:
                print("Super Bowl MVP: No qualified winner")
            print()
        
        # Show persisted awards
        rows = session.exec(select(AwardWinner).where(AwardWinner.season==season)).all()
        print(f"Persisted Awards: {len(rows)} total")
        print("-" * 20)
        for row in rows:
            if row.player_id:
                print(f"{row.award}: Player {row.player_id}")
            elif row.team_id:
                print(f"{row.award}: Team {row.team_id}")
            else:
                print(f"{row.award}: No winner")


if __name__ == "__main__":
    print_awards_and_leaders()
