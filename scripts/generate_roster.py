"""
Generate rosters and output teams.csv, players.csv, depth_chart.csv (and optionally JSON).

Usage:
  python scripts\generate_roster.py --out app\data\generated
  python scripts\generate_roster.py --seed 12345 --out app\data\generated
"""

import argparse
import csv
import json
import os
import random
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (DEFAULT_SEED, etc.)
load_dotenv()


def generate_data(seed: int, out_dir: Path, fmt: str = "csv", free_agents: int = 100):
    random.seed(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    # IMPORTANT: Keep values compatible with the DB enums
    # - conference: must be one of {"AFC", "NFC"}
    # - division:   must be one of {"East", "West", "North", "South"}

    teams = [
        {
            "location_name": "Arlington",
            "nickname": "Arrows",
            "conference": "AFC",     # ✅ valid
            "division": "East",      # ✅ valid
            "power_rating": 75,
            "cap_space": 1000000,
        }
    ]

    players = [
        {
            "team_key": "Arlington|Arrows",
            "first_name": "John",
            "last_name": "Doe",
            "position": "QB",
            "jersey": 12,
            "age": 25,
            "salary": 500000,
            "contract_years": 2,
            "speed": 60,
            "strength": 55,
            "agility": 70,
            "throw_power": 80,
            "throw_accuracy": 75,
            "catching": 40,
            "tackling": 30,
            "awareness": 65,
            "potential": 80,
            "stamina": 85,
            "injury_proneness": 20,
            "morale": 70,
        },
        {
            "team_key": "Arlington|Arrows",
            "first_name": "Jim",
            "last_name": "Smith",
            "position": "RB",
            "jersey": 28,
            "age": 24,
            "salary": 450000,
            "contract_years": 3,
            "speed": 78,
            "strength": 62,
            "agility": 75,
            "throw_power": 25,
            "throw_accuracy": 20,
            "catching": 68,
            "tackling": 40,
            "awareness": 60,
            "potential": 75,
            "stamina": 82,
            "injury_proneness": 15,
            "morale": 72,
        },
    ]

    depth_chart = [
        {
            "team_key": "Arlington|Arrows",
            "position": "QB",
            "starter_jersey": 12,
            "backup_jersey": "",
        },
        {
            "team_key": "Arlington|Arrows",
            "position": "RB",
            "starter_jersey": 28,
            "backup_jersey": "",
        },
    ]

    # Write CSVs
    def write_csv(name, rows, fieldnames):
        with (out_dir / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    write_csv("teams", teams, list(teams[0].keys()))
    write_csv("players", players, list(players[0].keys()))
    write_csv("depth_chart", depth_chart, list(depth_chart[0].keys()))

    if fmt in ("json", "both"):
        with (out_dir / "teams.json").open("w", encoding="utf-8") as f:
            json.dump(teams, f, indent=2)
        with (out_dir / "players.json").open("w", encoding="utf-8") as f:
            json.dump(players, f, indent=2)
        with (out_dir / "depth_chart.json").open("w", encoding="utf-8") as f:
            json.dump(depth_chart, f, indent=2)

    print(f"✅ Generated roster with seed={seed} in {out_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, help="Random seed (default from .env)")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--format", choices=["csv", "json", "both"], default="csv")
    parser.add_argument("--free-agents", type=int, default=100)
    args = parser.parse_args()

    # Use provided seed or fall back to DEFAULT_SEED
    seed = args.seed or int(os.getenv("DEFAULT_SEED", "2025"))

    out_dir = Path(args.out)
    generate_data(seed, out_dir, args.format, args.free_agents)


if __name__ == "__main__":
    main()
