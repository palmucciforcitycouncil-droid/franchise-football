# scripts/draft_pipeline.py
import argparse, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session
from app.db import get_engine
from app.services.draft_pipeline import seed_four_year_pipeline, rollover_draft_pipeline, finalize_draft_year
from app.models.draft import Prospect

def main():
    ap = argparse.ArgumentParser(description="4-year Draft Pipeline tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sd = sub.add_parser("seed"); sd.add_argument("--season", type=int, required=True); sd.add_argument("--seed", type=int, default=2025)
    ro = sub.add_parser("rollover"); ro.add_argument("--season", type=int, required=True); ro.add_argument("--seed", type=int, default=2025)
    fn = sub.add_parser("finalize"); fn.add_argument("--season", type=int, required=True)
    wl = sub.add_parser("watch"); wl.add_argument("--ids", type=str, required=True)
    uw = sub.add_parser("unwatch"); uw.add_argument("--ids", type=str, required=True)

    args = ap.parse_args()
    with Session(get_engine()) as s:
        if args.cmd=="seed":
            print(json.dumps(seed_four_year_pipeline(s, args.season, args.seed), indent=2))
        elif args.cmd=="rollover":
            print(json.dumps(rollover_draft_pipeline(s, args.season, args.seed), indent=2))
        elif args.cmd=="finalize":
            print(json.dumps(finalize_draft_year(s, args.season), indent=2))
        elif args.cmd in ("watch","unwatch"):
            ids = [int(x) for x in args.ids.split(",") if x.strip()]
            for pid in ids:
                p = s.get(Prospect, pid)
                if p:
                    p.watchlist = (args.cmd=="watch")
                    s.add(p)
            s.commit()
            print(json.dumps({"updated": len(ids)}, indent=2))

if __name__=="__main__":
    main()
