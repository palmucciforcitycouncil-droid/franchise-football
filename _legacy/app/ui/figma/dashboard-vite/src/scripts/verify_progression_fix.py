# scripts/verify_progression_fix.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.services.progression import apply_progression_for_season
from app.models.progression import PlayerProgression
from app.models.core_min import Player
import json, sys

def main(season: int = 2025):
    engine = get_engine()
    with Session(engine) as s:
        apply_progression_for_season(s, season=season, seed=2025, force=True)

    changed = 0
    mismatches = []
    with Session(engine) as s:
        rows = s.exec(select(PlayerProgression).where(PlayerProgression.season == season)).all()
        for r in rows:
            b = json.loads(r.before_json); a = json.loads(r.after_json)
            if any(a.get(k,0)!=b.get(k,0) for k in ["awareness","throw_accuracy","catching","tackling","speed","agility","strength","stamina","morale"]):
                changed += 1
                p = s.get(Player, r.player_id)
                if not p: 
                    continue
                # spot-check that at least one changed key equals DB value
                ok = False
                for k in ["awareness","throw_accuracy","catching","tackling","speed","agility","strength","stamina","morale"]:
                    if a.get(k, None) is not None and a.get(k) != b.get(k):
                        ok = getattr(p, k, None) == a[k]
                        if not ok:
                            mismatches.append((r.player_id, k, a[k], getattr(p, k, None)))
                        break
    status = "SUCCESS" if changed > 0 and not mismatches else "FAIL"
    print(f"[verify_progression_fix] status={status} season={season} changed_rows={changed} mismatches={len(mismatches)}")
    if mismatches:
        for pid, k, exp, got in mismatches[:10]:
            print(f"  MISMATCH pid={pid} attr={k} expected={exp} got={got}")
    sys.exit(0 if status == "SUCCESS" else 1)

if __name__ == "__main__":
    main()
