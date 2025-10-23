#!/usr/bin/env python3
"""
Comprehensive demonstration of Weekly Awards + Season Export + Big Stat Samples.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, create_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.weekly_awards import compute_weekly_awards
from app.services.season_export import export_season_summary
from app.services.awards import compute_season_awards, compute_league_leaders
from scripts.print_stat_samples import main as print_samples


def demo_weekly_awards_and_export():
    """Demonstrate the complete weekly awards and export system."""
    print("Weekly Awards + Season Export + Big Stat Samples Demo")
    print("=" * 60)
    
    with memory_db() as session:
        # Run a mini season
        print("\n1. Running Mini Season (4 teams, 2 weeks)...")
        out = run_mini_season(session, weeks=2, seed=2025)
        print(f"   Generated {len(out['games'])} games")
        print(f"   Teams: {out['teams']}")
        
        season = 2025
        
        # Compute weekly awards
        print("\n2. Computing Weekly Awards...")
        try:
            weekly_winners = compute_weekly_awards(session, season)
            print(f"   Generated {len(weekly_winners)} weekly awards")
            for award in weekly_winners[:3]:  # Show first 3
                print(f"      - Week {award.week}: {award.award} -> Player {award.player_id}")
        except Exception as e:
            print(f"   Weekly awards: {e}")
        
        # Compute season awards
        print("\n3. Computing Season Awards...")
        try:
            season_awards = compute_season_awards(session, season)
            print(f"   Generated season awards: {list(season_awards.keys())}")
        except Exception as e:
            print(f"   Season awards: {e}")
        
        # Compute league leaders
        print("\n4. Computing League Leaders...")
        try:
            leaders = compute_league_leaders(session, season, top_n=5)
            print(f"   Generated {len(leaders)} leaderboards")
            for leaderboard in leaders[:2]:  # Show first 2
                print(f"      - {leaderboard.title}: {len(leaderboard.leaders)} leaders")
        except Exception as e:
            print(f"   League leaders: {e}")
        
        # Export season summary
        print("\n5. Exporting Season Summary...")
        try:
            payload = export_season_summary(
                session, 
                season, 
                out_json="data/reports/demo_season_summary.json",
                out_html="data/reports/demo_season_summary.html"
            )
            print(f"   Exported JSON with keys: {list(payload.keys())}")
            print(f"   Weekly awards: {len(payload['weekly_awards'])}")
            print(f"   Season awards: {len(payload['awards'])}")
            print(f"   Leaderboards: {len(payload['leaders'])}")
        except Exception as e:
            print(f"   Export failed: {e}")
        
        # Print stat samples
        print("\n6. Printing Stat Samples...")
        try:
            print_samples("sqlite:///:memory:", season, per_table=50)
        except Exception as e:
            print(f"   Stat samples: {e}")
    
    print("\n" + "=" * 60)
    print("Demo completed! Check data/reports/ for exported files.")


if __name__ == "__main__":
    demo_weekly_awards_and_export()
