#!/usr/bin/env python3
"""
CSV Export CLI for League Reports
Exports awards, team stats, player stats, and league summary to CSV files.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from pathlib import Path
from sqlmodel import Session
from app.db import get_engine
from app.services.reports import (
    export_awards_csv,
    export_team_season_csv,
    export_player_season_csv,
    export_league_summary_csv,
)

def main():
    parser = argparse.ArgumentParser(description="Export league reports to CSV.")
    parser.add_argument("--season", type=int, required=True, help="Season year to export")
    parser.add_argument("--out", type=str, default="data/reports", help="Output directory (default: data/reports)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    engine = get_engine()
    with Session(engine) as session:
        print(f"Exporting reports for season {args.season} to {out_dir}...")
        
        a = export_awards_csv(session, args.season, out_dir)
        t = export_team_season_csv(session, args.season, out_dir)
        p = export_player_season_csv(session, args.season, out_dir)
        l = export_league_summary_csv(session, args.season, out_dir)
        
        print("Exported:")
        print(f"  Awards: {a}")
        print(f"  Team Stats: {t}")
        print(f"  Player Stats: {p}")
        print(f"  League Summary: {l}")

if __name__ == "__main__":
    main()
