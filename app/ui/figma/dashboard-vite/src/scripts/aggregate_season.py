#!/usr/bin/env python3
"""
Season Stats Aggregation CLI
Aggregates TeamGameStats and PlayerGameStats into season totals.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from sqlmodel import Session, create_engine
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season

def get_engine():
    """Get database engine - using franchise.db for consistency."""
    return create_engine("sqlite:///franchise.db", future=True)

def main():
    parser = argparse.ArgumentParser(description="Aggregate season stats")
    parser.add_argument("--season", type=int, required=True, help="Season year to aggregate")
    parser.add_argument("--teams-only", action="store_true", help="Only aggregate team stats")
    parser.add_argument("--players-only", action="store_true", help="Only aggregate player stats")
    args = parser.parse_args()

    engine = get_engine()
    with Session(engine) as session:
        print(f"Aggregating season {args.season} stats...")
        
        if not args.players_only:
            print("Aggregating team season stats...")
            aggregate_team_season(session, args.season)
            print("OK Team season stats aggregated")
        
        if not args.teams_only:
            print("Aggregating player season stats...")
            aggregate_player_season(session, args.season)
            print("OK Player season stats aggregated")
        
        print(f"Season {args.season} aggregation complete!")

if __name__ == "__main__":
    main()
