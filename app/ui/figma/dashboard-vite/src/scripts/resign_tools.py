# scripts/resign_tools.py
import argparse, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session
from app.db import get_engine
from app.services.contracts import (
    init_season_cap_for_all_teams, resign_candidates, submit_resign_offer, simulate_resign_window, compute_and_persist_team_cap
)

def main():
    ap = argparse.ArgumentParser(description="Auto-cap + Re-sign window tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    capi = sub.add_parser("cap-init"); capi.add_argument("--season", type=int, required=True); capi.add_argument("--limit", type=int, default=2000)
    cand = sub.add_parser("candidates"); cand.add_argument("--season", type=int, required=True)
    bid = sub.add_parser("bid"); bid.add_argument("--season", type=int, required=True); bid.add_argument("--team", type=int, required=True); bid.add_argument("--player", type=int, required=True); bid.add_argument("--aav", type=int, required=True); bid.add_argument("--years", type=int, default=2)
    sim = sub.add_parser("simulate"); sim.add_argument("--season", type=int, required=True)

    args = ap.parse_args()
    with Session(get_engine()) as s:
        if args.cmd == "cap-init":
            print(json.dumps(init_season_cap_for_all_teams(s, args.season, args.limit), indent=2))
        elif args.cmd == "candidates":
            pairs = resign_candidates(s, args.season)
            out = [{"player_id": getattr(p,"player_id",getattr(p,"id")), "team_id": getattr(p,"team_id",None)} for (p,_) in pairs]
            print(json.dumps({"count": len(out), "items": out}, indent=2))
        elif args.cmd == "bid":
            print(json.dumps(submit_resign_offer(s, args.season, args.team, args.player, args.aav, args.years), indent=2))
        elif args.cmd == "simulate":
            print(json.dumps(simulate_resign_window(s, args.season), indent=2))

if __name__ == "__main__":
    main()


