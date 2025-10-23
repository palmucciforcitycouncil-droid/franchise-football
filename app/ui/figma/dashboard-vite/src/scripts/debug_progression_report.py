# scripts/debug_progression_report.py
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from typing import Dict, List, Tuple
from sqlmodel import Session, select
from app.db import get_engine
from app.models.progression import PlayerProgression
from app.models.core_min import Player

ATTRS = ["awareness","throw_accuracy","throw_power","catching","tackling","speed","agility","strength","stamina","morale"]

def parse(js: str) -> Dict[str, int]:
    # Stored with json.dumps; safe to load via json
    return json.loads(js)

def total_delta(before: Dict[str,int], after: Dict[str,int]) -> int:
    return sum(after.get(k,0) - before.get(k,0) for k in ATTRS)

def per_attr_deltas(before: Dict[str,int], after: Dict[str,int]) -> Dict[str,int]:
    return {k: after.get(k,0) - before.get(k,0) for k in ATTRS}

def load_rows(season: int) -> List[Tuple[Player, PlayerProgression, Dict[str,int], Dict[str,int], Dict[str,int], int]]:
    engine = get_engine()
    out = []
    with Session(engine) as s:
        rows = s.exec(select(PlayerProgression).where(PlayerProgression.season == season)).all()
        for r in rows:
            p = s.get(Player, r.player_id)
            if not p:
                continue
            b = parse(r.before_json)
            a = parse(r.after_json)
            d = per_attr_deltas(b, a)
            t = total_delta(b, a)
            out.append((p, r, b, a, d, t))
    return out

def write_csv(rows, season: int, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "season","player_id","name","position","age","team_id","total_delta","components_json",
            *[f"delta_{k}" for k in ATTRS]
        ])
        for p, prog, b, a, d, t in rows:
            name = f"{getattr(p,'first_name','').strip()} {getattr(p,'last_name','').strip()}".strip() or getattr(p,"name","")
            w.writerow([
                prog.season, getattr(p,"player_id",getattr(p,"id",None)), name, getattr(p,"position",getattr(p,"pos","")),
                getattr(p,"age",0), getattr(p,"team_id",None), t, prog.components_json,
                *[d[k] for k in ATTRS]
            ])
    return path

def main(season: int = 2025):
    rows = load_rows(season)

    # Sort by total delta
    rows_sorted = sorted(rows, key=lambda r: r[-1], reverse=True)
    top_up = rows_sorted[:15]
    top_down = list(reversed(rows_sorted))[:15]

    # Print Top Risers
    print("\n=== TOP 15 RISERS ===")
    for p, prog, b, a, d, t in top_up:
        nm = f"{getattr(p,'first_name','').strip()} {getattr(p,'last_name','').strip()}".strip() or getattr(p,"name","")
        print(f"{nm:28} | {getattr(p,'position',''):>2} | age {getattr(p,'age',0):>2} | +{t:>2} | key: " +
              ", ".join(f"{k}:{v:+d}" for k,v in d.items() if v != 0))

    # Print Top Fallers
    print("\n=== TOP 15 FALLERS ===")
    for p, prog, b, a, d, t in top_down:
        nm = f"{getattr(p,'first_name','').strip()} {getattr(p,'last_name','').strip()}".strip() or getattr(p,"name","")
        print(f"{nm:28} | {getattr(p,'position',''):>2} | age {getattr(p,'age',0):>2} | {t:>+3} | key: " +
              ", ".join(f"{k}:{v:+d}" for k,v in d.items() if v != 0))

    # Probe: older RBs tend to stagnate/regress on speed/agility
    print("\n=== OLDER RB PROBE (age >= 30) ===")
    older_rbs = [(p, d) for p, prog, b, a, d, t in rows if getattr(p,"position","")=="RB" and getattr(p,"age",0)>=30]
    if not older_rbs:
        print("No RBs age >= 30 in this sample.")
    else:
        for p, d in older_rbs[:10]:
            nm = f"{getattr(p,'first_name','').strip()} {getattr(p,'last_name','').strip()}".strip() or getattr(p,"name","")
            sp = d.get("speed",0); ag = d.get("agility",0)
            print(f"{nm:28} | age {getattr(p,'age',0):>2} | Δspeed {sp:+d} | Δagility {ag:+d}")

    # Write CSV
    out_path = Path("data/reports") / f"progression_{season}.csv"
    out = write_csv(rows_sorted, season, out_path)
    print(f"\nCSV written: {out.resolve()}")

if __name__ == "__main__":
    main()
