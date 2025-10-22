#!/usr/bin/env python3
"""
Comprehensive Awards Test - Shows the awards system working with realistic data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.awards import compute_season_awards, compute_super_bowl_mvp, compute_league_leaders
from app.models.awards import AwardWinner, AwardType
from sqlmodel import select


def test_awards_with_realistic_data():
    """Test awards with more realistic data that meets qualifiers."""
    print("Testing Awards with Realistic Data")
    print("=" * 50)
    
    with memory_db() as session:
        # Run a longer season to generate more data
        out = run_mini_season(session, weeks=4)  # More games = more data
        season = 2025
        
        print(f"Generated {len(out['teams'])} teams, {len(out['games'])} games")
        
        # Check what data we have
        from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
        agg = aggregate_truth_from_pbp(session)
        
        print(f"Player season stats: {len(agg['player_season'])} players")
        print(f"Team season stats: {len(agg['team_season'])} teams")
        
        # Show some sample stats
        if agg['player_season']:
            sample_player = list(agg['player_season'].items())[0]
            print(f"Sample player stats: {sample_player[1]}")
        
        # Compute awards
        print("\nComputing season awards...")
        aw = compute_season_awards(session, season=season)
        
        print("Season Awards:")
        print("-" * 20)
        for award, winner in aw.items():
            if winner is not None and winner != -1:
                print(f"{award}: Player {winner}")
            else:
                print(f"{award}: No qualified winner")
        
        # Compute league leaders
        print("\nComputing league leaders...")
        boards = compute_league_leaders(session, season=season, top_n=3)
        
        print("\nLeague Leaders:")
        print("-" * 20)
        for board in boards:
            print(f"\n{board.title}")
            if board.leaders:
                for i, row in enumerate(board.leaders, 1):
                    print(f"  {i}. Player {row.player_id} (Team {row.team_id}): {row.value}")
            else:
                print("  No qualified leaders")
        
        # Check persisted awards
        rows = session.exec(select(AwardWinner).where(AwardWinner.season==season)).all()
        print(f"\nPersisted Awards: {len(rows)} total")
        
        # Test Super Bowl MVP
        if out.get("games"):
            champ_game_id = out["games"][-1]
            print(f"\nTesting Super Bowl MVP for game {champ_game_id}...")
            sb_mvp = compute_super_bowl_mvp(session, season, champ_game_id)
            
            if sb_mvp:
                print(f"Super Bowl MVP: Player {sb_mvp}")
            else:
                print("Super Bowl MVP: No qualified winner")
        
        print("\nAwards system test completed successfully!")


if __name__ == "__main__":
    test_awards_with_realistic_data()
