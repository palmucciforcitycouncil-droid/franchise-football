"""
Lightweight DB integrity checker for local debugging.
Usage: python -m scripts.check_integrity
"""
from sqlmodel import select
from app.db import get_session
from app.models.sim_models import Team, Game
from app.models.player_models import Player, DepthChart
from app.models.contract_models import PlayerContract, CapSummary

def main():
    with get_session() as s:
        ok = True
        teams = s.exec(select(Team)).all()
        if not teams:
            ok = False; print("WARN: no teams")
        # Each team should have a cap summary
        caps = {c.team_id for c in s.exec(select(CapSummary)).all()}
        missing_caps = [t.id for t in teams if t.id not in caps]
        if missing_caps:
            ok = False; print("WARN: missing CapSummary for teams:", missing_caps)
        # Depth chart players must exist and belong to same team
        for dc in s.exec(select(DepthChart)).all():
            p = s.get(Player, dc.player_id)
            if not p or p.team_id != dc.team_id:
                ok = False; print(f"WARN: depth chart mismatch team {dc.team_id} -> player {dc.player_id} team {getattr(p,'team_id',None)}")
        # Games flags
        for g in s.exec(select(Game)).all():
            if g.is_played and (g.home_score is None or g.away_score is None):
                ok = False; print("WARN: played game missing scores:", g.id)
        print("INTEGRITY:", "OK" if ok else "ISSUES FOUND")

if __name__ == "__main__":
    main()

