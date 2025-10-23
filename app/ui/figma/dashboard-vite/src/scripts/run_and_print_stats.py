#!/usr/bin/env python3
"""
Run & Print Stats Now - Big samples to console with optional CSV export.
"""

from __future__ import annotations
import argparse
import sys
import json
import os
from typing import Any, List, Tuple
from sqlmodel import Session, select, create_engine

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- helpers to locate your tables/services, duck-typed ---
def _try(cls_path: List[Tuple[str, str]]):
    """Try to import a class from various module paths."""
    for mod, name in cls_path:
        try:
            m = __import__(mod, fromlist=[name])
            return getattr(m, name)
        except Exception:
            continue
    return None


# Try to import stat models
TeamSeason = _try([("app.models.stats_models", "TeamSeasonStats")])
PlayerSeason = _try([("app.models.stats_models", "PlayerSeasonStats")])
TeamGame = _try([("app.models.stats_models", "TeamGameStats")])
PlayerGame = _try([("app.models.stats_models", "PlayerGameStats")])


def _sample_rows(session: Session, cls, limit: int) -> List[Any]:
    """Get sample rows from a table."""
    if not cls:
        return []
    try:
        return session.exec(select(cls).limit(limit)).all()
    except Exception:
        return []


def _print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 12 + f" {title} " + "=" * 12)


def _row_to_dict(r: Any) -> dict:
    """Convert a row to dictionary, preserving escapes for easy eyeballing."""
    try:
        d = r.__dict__.copy()
        # drop SQLAlchemy internal state if present
        d.pop("_sa_instance_state", None)
        return d
    except Exception:
        return {"_repr": repr(r)}


def run_from_db(db_url: str, rows: int):
    """Run stats sampling from existing database."""
    eng = create_engine(db_url, future=True)
    with Session(eng) as s:
        _print_section("TEAM SEASON STATS (sample)")
        team_season_rows = _sample_rows(s, TeamSeason, rows)
        print(f"Found {len(team_season_rows)} team season records")
        for r in team_season_rows:
            print(json.dumps(_row_to_dict(r), ensure_ascii=False))

        _print_section("PLAYER SEASON STATS (sample)")
        player_season_rows = _sample_rows(s, PlayerSeason, rows)
        print(f"Found {len(player_season_rows)} player season records")
        for r in player_season_rows:
            print(json.dumps(_row_to_dict(r), ensure_ascii=False))

        _print_section("TEAM GAME STATS (sample)")
        team_game_rows = _sample_rows(s, TeamGame, rows)
        print(f"Found {len(team_game_rows)} team game records")
        for r in team_game_rows:
            print(json.dumps(_row_to_dict(r), ensure_ascii=False))

        _print_section("PLAYER GAME STATS (sample)")
        player_game_rows = _sample_rows(s, PlayerGame, rows)
        print(f"Found {len(player_game_rows)} player game records")
        for r in player_game_rows:
            print(json.dumps(_row_to_dict(r), ensure_ascii=False))


def run_in_memory_and_print(rows: int, weeks: int):
    """Run mini season simulation and print stats."""
    # Uses the mini season harness you already have to create fresh data & print it
    from app.testing.mini_season_runner import memory_db, run_mini_season
    
    with memory_db() as session:
        print(f"Running mini season with {weeks} weeks...")
        out = run_mini_season(session, weeks=weeks)
        print(f"Generated {len(out['games'])} games for teams {out['teams']}")
        
        _print_section("TEAM SEASON STATS (sample)")
        team_season_rows = _sample_rows(session, TeamSeason, rows)
        print(f"Found {len(team_season_rows)} team season records")
        for r in team_season_rows:
            print(json.dumps(_row_to_dict(r), ensure_ascii=False))

        _print_section("PLAYER SEASON STATS (sample)")
        player_season_rows = _sample_rows(session, PlayerSeason, rows)
        print(f"Found {len(player_season_rows)} player season records")
        for r in player_season_rows:
            print(json.dumps(_row_to_dict(r), ensure_ascii=False))

        _print_section("TEAM GAME STATS (sample)")
        team_game_rows = _sample_rows(session, TeamGame, rows)
        print(f"Found {len(team_game_rows)} team game records")
        for r in team_game_rows:
            print(json.dumps(_row_to_dict(r), ensure_ascii=False))

        _print_section("PLAYER GAME STATS (sample)")
        player_game_rows = _sample_rows(session, PlayerGame, rows)
        print(f"Found {len(player_game_rows)} player game records")
        for r in player_game_rows:
            print(json.dumps(_row_to_dict(r), ensure_ascii=False))


def maybe_export_csv(db_url: str, rows: int, out_prefix: str | None):
    """Optionally export stats to CSV files."""
    if not out_prefix:
        return
    
    import csv
    
    eng = create_engine(db_url, future=True)
    with Session(eng) as s:
        def dump(cls, name):
            if not cls:
                return
            filepath = f"{out_prefix}_{name}.csv"
            rows_list = _sample_rows(s, cls, rows)
            if not rows_list:
                print(f"[CSV] No data for {name}")
                return
            
            dicts = [_row_to_dict(r) for r in rows_list]
            cols = sorted({k for d in dicts for k in d.keys()})
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for d in dicts:
                    w.writerow(d)
            print(f"[CSV] Wrote {filepath} ({len(rows_list)} rows)")
        
        dump(TeamSeason, "team_season")
        dump(PlayerSeason, "player_season")
        dump(TeamGame, "team_game")
        dump(PlayerGame, "player_game")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Print big samples of season & game stats for spot checks.")
    ap.add_argument("--mode", choices=["db", "memory"], default="db", 
                   help="db=read existing DB; memory=simulate mini season and print")
    ap.add_argument("--db", default="sqlite:///franchise.db", 
                   help="SQLAlchemy DB URL (when --mode db)")
    ap.add_argument("--rows", type=int, default=200, 
                   help="rows per table to print")
    ap.add_argument("--weeks", type=int, default=2, 
                   help="mini season weeks (when --mode memory)")
    ap.add_argument("--csv-prefix", default=None, 
                   help="optional path prefix to also export CSVs")
    args = ap.parse_args()

    print(f"Run & Print Stats Now - Mode: {args.mode}, Rows: {args.rows}")
    if args.mode == "memory":
        print(f"Weeks: {args.weeks}")
    if args.csv_prefix:
        print(f"CSV Export: {args.csv_prefix}_*.csv")

    if args.mode == "db":
        run_from_db(args.db, args.rows)
        maybe_export_csv(args.db, args.rows, args.csv_prefix)
    else:
        run_in_memory_and_print(args.rows, args.weeks)
