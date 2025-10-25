# scripts/draft_extras.py
import argparse, json
from sqlmodel import Session
from app.db import get_engine
from app.services.fa_cleanup import drop_uifas_without_contracts
from app.models.draft import Prospect
from app.models.draft_audit import ProspectProgressAudit
from sqlmodel import select

def main():
    ap = argparse.ArgumentParser(description="Draft extras tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    cl = sub.add_parser("fa-clean"); cl.add_argument("--season", type=int, required=True)
    sp = sub.add_parser("sparkline"); sp.add_argument("--season", type=int, required=True); sp.add_argument("--max", type=int, default=3)

    args = ap.parse_args()
    with Session(get_engine()) as s:
        if args.cmd == "fa-clean":
            print(json.dumps(drop_uifas_without_contracts(s, args.season), indent=2))
        elif args.cmd == "sparkline":
            # quick local dump for watchlisted items
            watch = s.exec(select(Prospect).where(Prospect.watchlist == True)).all()
            out = {}
            for p in watch:
                audits = s.exec(
                    select(ProspectProgressAudit)
                    .where(ProspectProgressAudit.prospect_id == p.id, ProspectProgressAudit.season <= args.season)
                    .order_by(ProspectProgressAudit.season.desc())
                ).all()
                points = [{"season": a.season, "ovr": a.ovr_after} for a in audits[:args.max]]
                out[p.id] = {"name": p.name, "pos": p.pos, "sparkline": list(reversed(points))}
            print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()


