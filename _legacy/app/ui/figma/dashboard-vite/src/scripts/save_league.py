# scripts/save_league.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse, json
from pathlib import Path
from sqlmodel import Session
from app.db import get_engine
from app.services.save_load import export_league_to_json

def main():
    ap = argparse.ArgumentParser(description="Export league to deterministic JSON.")
    ap.add_argument("--name", required=True, help="Save name (filename without .json)")
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--out", default="data/saves")
    ap.add_argument("--compress", action="store_true", help="Compress with gzip")
    args = ap.parse_args()

    with Session(get_engine()) as s:
        res = export_league_to_json(s, args.name, season=args.season, out_dir=Path(args.out), compress=args.compress)
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
