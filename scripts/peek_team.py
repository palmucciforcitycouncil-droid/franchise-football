"""
Print players and depth entries for one team_key, e.g. "Arlington|Arrows".

Usage:
  python scripts\peek_team.py --path app\data\generated --team "Arlington|Arrows"
"""

import argparse
import csv
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--team", required=True)
    args = ap.parse_args()

    base = Path(args.path)
    players_csv = base / "players.csv"
    depth_csv = base / "depth_chart.csv"

    with players_csv.open(newline="", encoding="utf-8") as f:
        players = [r for r in csv.DictReader(f) if r["team_key"].strip() == args.team.strip()]
    with depth_csv.open(newline="", encoding="utf-8") as f:
        depth = [r for r in csv.DictReader(f) if r["team_key"].strip() == args.team.strip()]

    jerseys = sorted({int(p["jersey"]) for p in players})
    print(f"TEAM: {args.team}")
    print(f"Player jerseys ({len(jerseys)}): {jerseys[:60]}{' ...' if len(jerseys) > 60 else ''}")
    print("Depth chart (first 20 rows):")
    for d in depth[:20]:
        sj = d['starter_jersey'].strip()
        bj = (d.get('backup_jersey') or '').strip()
        print(f"  {d['position'].strip()}: starter={sj} backup={bj}")

    # Quick sanity: report any depth rows whose starter isn't in player jerseys
    missing = [
        (d['position'].strip(), int(d['starter_jersey'].strip()))
        for d in depth
        if d['starter_jersey'].strip().isdigit() and int(d['starter_jersey'].strip()) not in jerseys
    ]
    if missing:
        print("\nWARNING: Depth starters not present in players.csv for this team:")
        for pos, j in missing:
            print(f"  - {pos}: {j}")


if __name__ == "__main__":
    main()

