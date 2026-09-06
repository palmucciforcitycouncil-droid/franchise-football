# scripts/test_dashboard_simple.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.models.season_stats import TeamSeasonStats
from app.models.awards import AwardResult
from app.models.progression import PlayerProgression
from app.models.core_min import Player
from app.services.analytics import league_summary_for, trend_summary, awards_recap, progression_risers_fallers

def main():
    print("=== DASHBOARD ANALYTICS TEST ===")
    
    engine = get_engine()
    
    # Test league summary
    print("\n1. Testing league_summary_for...")
    with Session(engine) as session:
        summary = league_summary_for(session, 2025)
        print(f"   Summary: {summary}")
    
    # Test trend summary
    print("\n2. Testing trend_summary...")
    with Session(engine) as session:
        trends = trend_summary(session, 2024, 2025)
        print(f"   Trends: {trends}")
    
    # Test awards recap
    print("\n3. Testing awards_recap...")
    with Session(engine) as session:
        awards = awards_recap(session, 2025)
        print(f"   Awards: {awards}")
    
    # Test progression risers/fallers
    print("\n4. Testing progression_risers_fallers...")
    with Session(engine) as session:
        prog = progression_risers_fallers(session, 2025, top_n=3)
        print(f"   Progression: {prog}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
