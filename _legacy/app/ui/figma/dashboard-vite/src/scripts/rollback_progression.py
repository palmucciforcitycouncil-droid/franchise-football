# scripts/rollback_progression.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from sqlmodel import Session
from app.db import get_engine
from app.services.progression import rollback_progression

def main():
    parser = argparse.ArgumentParser(description="Rollback player progression to before-snapshot.")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--player-id", type=int, default=None)
    parser.add_argument("--purge", action="store_true", help="Also delete PlayerProgression rows after rollback")
    args = parser.parse_args()

    engine = get_engine()
    with Session(engine) as session:
        n = rollback_progression(session, season=args.season, player_id=args.player_id, purge=args.purge)
        scope = f"player_id={args.player_id}" if args.player_id is not None else "ALL players"
        print(f"Rolled back {n} progression rows for season {args.season} ({scope}). Purge={args.purge}")

if __name__ == "__main__":
    main()
