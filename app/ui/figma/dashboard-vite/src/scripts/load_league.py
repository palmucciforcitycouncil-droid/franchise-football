# scripts/load_league.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse, json
from pathlib import Path
from sqlmodel import Session
from app.db import get_engine
from app.services.save_load import import_league_from_json

def main():
    ap = argparse.ArgumentParser(description="Import league from deterministic JSON.")
    ap.add_argument("--path", required=True, help="Path to .json save")
    ap.add_argument("--strategy", choices=["replace","upsert"], default="replace")
    args = ap.parse_args()

    with Session(get_engine()) as s:
        res = import_league_from_json(s, Path(args.path), strategy=args.strategy)
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
