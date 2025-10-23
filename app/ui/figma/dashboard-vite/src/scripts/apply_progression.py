#!/usr/bin/env python3
"""
Player Progression & Regression CLI
Applies deterministic progression/regression to players based on season performance.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from sqlmodel import Session
from app.db import get_engine
from app.services.progression import apply_progression_for_season

def main():
    parser = argparse.ArgumentParser(description="Apply player progression/regression for a season.")
    parser.add_argument("--season", type=int, required=True, help="Season year to apply progression for")
    parser.add_argument("--seed", type=int, default=2025, help="Random seed for deterministic progression (default: 2025)")
    parser.add_argument("--force", action="store_true", help="Recompute even if progression exists for this season")
    args = parser.parse_args()

    engine = get_engine()
    with Session(engine) as session:
        print(f"Applying progression for season {args.season} (seed={args.seed}, force={args.force})...")
        apply_progression_for_season(session, season=args.season, seed=args.seed, force=args.force)
        print(f"Progression applied for season {args.season} (seed={args.seed}, force={args.force})")

if __name__ == "__main__":
    main()
