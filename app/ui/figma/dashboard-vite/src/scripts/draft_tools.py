# scripts/draft_tools.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse, json
from sqlmodel import Session, select
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks, make_selection
from app.models.draft import Prospect, DraftPick

def main():
    ap = argparse.ArgumentParser(description="Draft tools")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate"); g.add_argument("--season", type=int, required=True); g.add_argument("--seed", type=int, default=2025)
    l = sub.add_parser("list"); l.add_argument("--season", type=int, required=True)
    o = sub.add_parser("order"); o.add_argument("--season", type=int, required=True)
    p = sub.add_parser("pick"); p.add_argument("--season", type=int, required=True); p.add_argument("--overall", type=int, required=True); p.add_argument("--prospect-id", type=int, required=True); p.add_argument("--team-id", type=int, required=True)

    args = ap.parse_args()
    with Session(get_engine()) as s:
        if args.cmd == "generate":
            print(json.dumps({"res": {"prospects": generate_draft_class(s, args.season, seed=args.seed), "picks": assign_picks(s, args.season)}}, indent=2))
        elif args.cmd == "list":
            rows = s.exec(select(Prospect).where(Prospect.season==args.season).order_by(Prospect.pos, Prospect.overall.desc())).all()
            print(json.dumps([r.model_dump() for r in rows], indent=2))
        elif args.cmd == "order":
            rows = s.exec(select(DraftPick).where(DraftPick.season==args.season).order_by(DraftPick.overall_pick)).all()
            print(json.dumps([r.model_dump() for r in rows], indent=2))
        elif args.cmd == "pick":
            print(json.dumps(make_selection(s, args.season, args.overall, args.prospect_id, args.team_id), indent=2))

if __name__ == "__main__":
    main()
