# scripts/contracts_tools.py
import argparse, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session
from app.db import get_engine
from app.services.contracts import (
    expire_contracts, compute_and_persist_team_cap, list_free_agents,
    submit_bid, simulate_free_agency, team_contracts_in_season
)

def main():
    ap = argparse.ArgumentParser(description="Contracts & Free Agency tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("expire"); ex.add_argument("--season", type=int, required=True)
    cap = sub.add_parser("cap"); cap.add_argument("--season", type=int, required=True); cap.add_argument("--team", type=int, required=True)
    fa = sub.add_parser("fa-list"); fa.add_argument("--season", type=int, required=True)
    bid = sub.add_parser("fa-bid"); bid.add_argument("--season", type=int, required=True); bid.add_argument("--team", type=int, required=True); bid.add_argument("--player", type=int, required=True); bid.add_argument("--aav", type=int, required=True); bid.add_argument("--years", type=int, default=1)
    sim = sub.add_parser("fa-sim"); sim.add_argument("--season", type=int, required=True); sim.add_argument("--seed", type=int, default=2025)

    args = ap.parse_args()
    with Session(get_engine()) as s:
        if args.cmd == "expire":
            print(json.dumps(expire_contracts(s, args.season), indent=2))
        elif args.cmd == "cap":
            team = args.team
            from app.services.contracts import compute_and_persist_team_cap
            row = compute_and_persist_team_cap(s, team, args.season)
            print(json.dumps(row.model_dump(), indent=2))
            print(json.dumps({"contracts":[c.model_dump() for c in team_contracts_in_season(s, team, args.season)]}, indent=2))
        elif args.cmd == "fa-list":
            fas = list_free_agents(s, args.season)
            print(json.dumps([getattr(p,"player_id",getattr(p,"id")) for p in fas], indent=2))
        elif args.cmd == "fa-bid":
            print(json.dumps(submit_bid(s, args.season, args.team, args.player, args.aav, args.years), indent=2))
        elif args.cmd == "fa-sim":
            print(json.dumps(simulate_free_agency(s, args.season, seed=args.seed), indent=2))

if __name__ == "__main__":
    main()
