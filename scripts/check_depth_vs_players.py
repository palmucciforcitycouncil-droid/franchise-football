"""
Check CSVs for mismatches between depth_chart.csv and players.csv.

Usage:
  python scripts\check_depth_vs_players.py --path app\data\generated
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load_players(path: Path):
    players_by_team = defaultdict(set)  # team_key -> set(jerseys)
    with (path / "players.csv").open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            team_key = row["team_key"].strip()
            try:
                jersey = int(str(row["jersey"]).strip())
            except Exception:
                continue
            players_by_team[team_key].add(jersey)
    return players_by_team


def load_depth(path: Path):
    depth_rows = []
    with (path / "depth_chart.csv").open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            team_key = row["team_key"].strip()
            pos = row["position"].strip()
            try:
                starter = int(str(row["starter_jersey"]).strip())
            except Exception:
                starter = None
            backup_raw = (row.get("backup_jersey") or "").strip()
            backup = int(backup_raw) if backup_raw.isdigit() else None
            depth_rows.append((team_key, pos, starter, backup))
    return depth_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="Directory containing teams.csv, players.csv, depth_chart.csv")
    args = ap.parse_args()

    base = Path(args.path)
    players_by_team = load_players(base)
    depth_rows = load_depth(base)

    errors = []
    for team_key, pos, starter, backup in depth_rows:
        roster = players_by_team.get(team_key, set())
        if starter is None:
            errors.append((team_key, pos, "starter", "<not an int>"))
        elif starter not in roster:
            errors.append((team_key, pos, "starter", starter))
        if backup is not None and backup not in roster:
            errors.append((team_key, pos, "backup", backup))

    if not errors:
        print("✅ All depth chart jerseys are present in players.csv for their team_keys.")
        return

    print("❌ Mismatches found between depth_chart.csv and players.csv:")
    last_team = None
    for team_key, pos, kind, jersey in errors:
        if team_key != last_team:
            print(f"\nTeam: {team_key}")
            last_team = team_key
        print(f"  - {pos}: {kind} jersey {jersey} not found in players.csv")


if __name__ == "__main__":
    main()
