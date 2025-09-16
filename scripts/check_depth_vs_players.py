"""
Verify that every depth chart jersey exists on the same team's players list.

Usage (Windows CMD):
  python scripts\check_depth_vs_players.py --path app\data\generated
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="Directory with teams.csv, players.csv, depth_chart.csv")
    args = ap.parse_args()

    base = Path(args.path)
    players_csv = base / "players.csv"
    depth_csv = base / "depth_chart.csv"

    if not players_csv.exists() or not depth_csv.exists():
        print(f"ERROR: Missing CSVs under {base}. Expect players.csv and depth_chart.csv.")
        return

    with players_csv.open(newline="", encoding="utf-8") as f:
        players_rows = list(csv.DictReader(f))
    with depth_csv.open(newline="", encoding="utf-8") as f:
        depth_rows = list(csv.DictReader(f))

    team_jerseys = defaultdict(set)
    for r in players_rows:
        try:
            team_jerseys[r["team_key"]].add(int(r["jersey"]))
        except Exception:
            print(f"WARNING: bad player row: {r}")

    errors = []
    for d in depth_rows:
        tk = d["team_key"]
        try:
            s = int(d["starter_jersey"])
        except ValueError:
            errors.append((tk, d["position"], d["starter_jersey"], "starter (not an int)"))
            continue

        if s not in team_jerseys[tk]:
            errors.append((tk, d["position"], s, "starter"))

        b = (d.get("backup_jersey") or "").strip()
        if b:
            try:
                b_int = int(b)
            except ValueError:
                errors.append((tk, d["position"], b, "backup (not an int)"))
            else:
                if b_int not in team_jerseys[tk]:
                    errors.append((tk, d["position"], b_int, "backup"))

    if errors:
        print("MISMATCHES FOUND (team_key, position, jersey, kind):")
        for e in errors[:50]:
            print("  ", e)
        if len(errors) > 50:
            print(f"... and {len(errors) - 50} more")
        raise SystemExit(1)
    else:
        print("OK: depth_chart jerseys all exist on their teams")

if __name__ == "__main__":
    main()
