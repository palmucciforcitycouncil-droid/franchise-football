#!/usr/bin/env python3
"""
RECREATE STATS TABLES
Delete and recreate the stats tables with the correct schema.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def recreate_stats_tables():
    """Recreate the stats tables"""
    
    print("RECREATING STATS TABLES")
    print("=" * 25)
    
    try:
        from app.core.db import engine
        from sqlmodel import SQLModel
        from sqlalchemy import text
        from app.models.stats import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats, PlayerCareerStats
        from app.models.defense_stats import TeamDefenseStatsWeekly, PlayerDefenseStatsWeekly
        
        # Drop existing stats tables
        print("Dropping existing stats tables...")
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS player_game_stats"))
            conn.execute(text("DROP TABLE IF EXISTS team_game_stats"))
            conn.execute(text("DROP TABLE IF EXISTS player_season_stats"))
            conn.execute(text("DROP TABLE IF EXISTS team_season_stats"))
            conn.execute(text("DROP TABLE IF EXISTS player_career_stats"))
            conn.execute(text("DROP TABLE IF EXISTS team_defense_stats_weekly"))
            conn.execute(text("DROP TABLE IF EXISTS player_defense_stats_weekly"))
            conn.commit()
        
        print("SUCCESS: Existing stats tables dropped")
        
        # Create new stats tables
        print("Creating new stats tables...")
        SQLModel.metadata.create_all(engine)
        
        print("SUCCESS: New stats tables created")
        
        # Verify tables were created
        print("Verifying tables...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%stats%'"))
            tables = [row[0] for row in result]
            print(f"Stats tables found: {tables}")
        
        print("\nStats tables recreated successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to recreate stats tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    recreate_stats_tables()
