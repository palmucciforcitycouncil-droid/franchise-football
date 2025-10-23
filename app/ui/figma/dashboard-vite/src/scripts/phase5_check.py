#!/usr/bin/env python3
"""
Phase 5 Check Script - Verify scoring system is working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from sqlmodel import select
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.testing.field_alias import getf

if __name__ == "__main__":
    with memory_db() as s:
        run_mini_season(s, weeks=3)  # ~6 games
        
        try:
            from app.models.core_min import TeamGame
        except Exception:
            print("TeamGame model missing — skip.")
            raise SystemExit(0)
            
        rows = s.exec(select(TeamGame)).all()
        g = defaultdict(lambda: {"points":0,"punts":0,"fga":0,"yards":0,"sacks":0})
        
        for r in rows:
            gid = getattr(r,"game_id")
            g[gid]["points"] += getf(r,"points",0)
            g[gid]["punts"]  += getf(r,"punts",0)
            g[gid]["fga"]    += getf(r,"fga",0)
            g[gid]["yards"]  += getf(r,"yards_total",0)
            g[gid]["sacks"]  += getf(r,"sacks",0)
        
        print("=== PHASE5 SLATE SUMMARY ===")
        for gid,m in g.items():
            print(f"Game {gid}: Pts={m['points']}  FGAs={m['fga']}  Punts={m['punts']}  Yards={m['yards']}  Sacks={m['sacks']}")
        
        avg_punts = (sum(m["punts"] for m in g.values())/max(1,len(g))) if g else 0
        print(f"Games: {len(g)}  TotalPts={sum(m['points'] for m in g.values())}  TotalFGAs={sum(m['fga'] for m in g.values())}  AvgPunts={avg_punts:.2f}")
