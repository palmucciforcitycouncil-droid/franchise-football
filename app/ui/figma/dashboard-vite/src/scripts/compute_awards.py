#!/usr/bin/env python3
"""
Seasonal Awards Computation CLI
Computes deterministic seasonal awards and persists results.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from sqlmodel import Session, create_engine
from app.services.awards import compute_and_persist_awards

def get_engine():
    """Get database engine - using franchise.db for consistency."""
    return create_engine("sqlite:///franchise.db", future=True)

def main():
    parser = argparse.ArgumentParser(description="Compute seasonal awards and persist results.")
    parser.add_argument("--season", type=int, required=True, help="Season year to compute awards for")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top candidates to store per award (default: 5)")
    args = parser.parse_args()

    engine = get_engine()
    with Session(engine) as session:
        print(f"Computing awards for season {args.season}...")
        compute_and_persist_awards(session, season=args.season, top_n=args.top_n)
        print(f"Awards computed and saved for season {args.season}")

if __name__ == "__main__":
    main()
