#!/usr/bin/env python3
"""
Big Stat Samples Printout Script.
Prints hundreds of rows across the four major stat views for visual verification.
"""

from __future__ import annotations
from typing import Any, List, Tuple
from sqlmodel import Session, select, create_engine


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


def _sample_rows(session: Session, cls, limit: int = 200) -> List[Any]:
    """Get sample rows from a table."""
    if not cls:
        return []
    return session.exec(select(cls).limit(limit)).all()


def main(db_url="sqlite:///:memory:", season=2025, per_table=200):
    """Main function to print stat samples."""
    eng = create_engine(db_url, future=True)
    with Session(eng) as s:
        print("=== SAMPLE: TEAM SEASON STATS ===")
        rows = _sample_rows(s, TeamSeason, per_table)
        for r in rows:
            print(r.__dict__)
        
        print(f"\n=== SAMPLE: PLAYER SEASON STATS ({len(rows)} rows) ===")
        rows = _sample_rows(s, PlayerSeason, per_table)
        for r in rows:
            print(r.__dict__)
        
        print(f"\n=== SAMPLE: TEAM GAME STATS ({len(rows)} rows) ===")
        rows = _sample_rows(s, TeamGame, per_table)
        for r in rows:
            print(r.__dict__)
        
        print(f"\n=== SAMPLE: PLAYER GAME STATS ({len(rows)} rows) ===")
        rows = _sample_rows(s, PlayerGame, per_table)
        for r in rows:
            print(r.__dict__)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        db_url = sys.argv[1]
    else:
        db_url = "sqlite:///:memory:"
    main(db_url)
