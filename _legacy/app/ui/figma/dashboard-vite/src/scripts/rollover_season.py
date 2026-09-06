# scripts/rollover_season.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse, json
from sqlmodel import Session
from app.db import get_engine
from app.services.rollover import apply_season_rollover

def main():
    ap = argparse.ArgumentParser(description="Season rollover: age up, retire, reset fatigue, snapshot.")
    ap.add_argument("--from", dest="from_season", type=int, required=True)
    ap.add_argument("--to", dest="to_season", type=int, required=True)
    ap.add_argument("--seed", type=int, default=2025)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    engine = get_engine()
    with Session(engine) as s:
        result = apply_season_rollover(s, args.from_season, args.to_season, seed=args.seed, force=args.force)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
