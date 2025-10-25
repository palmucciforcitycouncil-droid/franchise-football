# app/services/players.py
from __future__ import annotations
from typing import Dict, Any, List
from sqlmodel import Session, select
from app.models.core_min import Player
from app.models.season_stats import PlayerSeasonStats
from app.models.awards import AwardResult

def get_player_career_summary(session: Session, player_id: int) -> Dict[str, Any]:
    p = session.get(Player, player_id)
    if not p:
        return {}
    rows = session.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == player_id).order_by(PlayerSeasonStats.season)).all()
    # Flexible fields with safe getattr
    def g(r, k, d=0): return getattr(r, k, d) if getattr(r, k, d) is not None else d
    seasons: List[Dict[str, Any]] = []
    totals: Dict[str, float] = {"games": 0, "pass_yards":0, "pass_tds":0, "rush_yards":0, "rush_tds":0, "recv_yards":0, "recv_tds":0, "tackles":0, "sacks":0, "interceptions_def":0}
    teams = set()
    for r in rows:
        line = {
            "season": r.season, "team_id": g(r, "team_id", None),
            "games": g(r, "games", 0),
            "pass_yards": g(r, "pass_yards", 0), "pass_tds": g(r, "pass_tds", 0),
            "rush_yards": g(r, "rush_yards", 0), "rush_tds": g(r, "rush_tds", 0),
            "recv_yards": g(r, "recv_yards", 0), "recv_tds": g(r, "recv_tds", 0),
            "tackles": g(r, "tackles", 0), "sacks": g(r, "sacks", 0), "interceptions_def": g(r, "interceptions_def", 0),
        }
        for k in totals.keys():
            totals[k] += line.get(k, 0) or 0
        seasons.append(line)
        if line["team_id"] is not None:
            teams.add(line["team_id"])

    awards_rows = session.exec(select(AwardResult).where(AwardResult.player_id == player_id)).all()
    awards = [{"season":ar.season, "award":ar.award, "rank":ar.rank, "score":ar.score} for ar in awards_rows]

    best_season = None
    if seasons:
        # crude heuristic: sum of skill stats
        def season_score(s): 
            return (s["pass_yards"] + 20*s["pass_tds"] + s["rush_yards"] + 20*s["rush_tds"] + s["recv_yards"] + 20*s["recv_tds"] + 2*s["tackles"] + 15*s["sacks"] + 25*s["interceptions_def"])
        best_season = max(seasons, key=season_score)

    return {
        "player": {
            "player_id": getattr(p, "player_id", getattr(p, "id", player_id)),
            "name": getattr(p, "name", None),
            "team_id": getattr(p, "team_id", None),
            "position": getattr(p, "position", getattr(p, "pos", None)),
            "rookie_season": getattr(p, "rookie_season", None),
            "is_rookie": getattr(p, "is_rookie", None),
            "potential": getattr(p, "potential", None),
        },
        "totals": totals,
        "seasons": seasons,
        "awards": awards,
        "teams": sorted(list(teams)),
        "best_season": best_season,
    }

