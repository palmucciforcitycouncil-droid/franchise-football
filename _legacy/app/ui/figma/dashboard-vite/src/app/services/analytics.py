# app/services/analytics.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from sqlmodel import Session, select
from app.models.season_stats import TeamSeasonStats
from app.models.awards import AwardResult
from app.models.progression import PlayerProgression
from app.models.core_min import Player

def _name(p: Player) -> str:
    fn = getattr(p,"first_name","") or ""; ln = getattr(p,"last_name","") or ""; nm = (fn+" "+ln).strip()
    return nm or getattr(p,"name","")

def league_summary_for(session: Session, season: int) -> Dict[str, Any]:
    rows = session.exec(select(TeamSeasonStats).where(TeamSeasonStats.season==season)).all()
    if not rows: return {}
    games = sum(r.games for r in rows) or 1
    ppg = sum(r.points_for for r in rows)/games
    plays_pg = sum(r.plays_offense for r in rows)/games
    pass_att = sum(r.pass_attempts for r in rows); rush_att = sum(r.rush_attempts for r in rows)
    pr = (pass_att/(pass_att+rush_att)) if (pass_att+rush_att)>0 else 0.0
    return {"season":season,"league_ppg":round(ppg,3),"plays_per_game":round(plays_pg,3),"pass_rate":round(pr,4)}

def trend_summary(session: Session, start_season: int, end_season: int) -> Dict[str, Any]:
    seasons = list(range(start_season, end_season+1))
    data = []
    for yr in seasons:
        s = league_summary_for(session, yr)
        if s: data.append(s)
    return {"start":start_season,"end":end_season,"seasons":data}

def awards_recap(session: Session, season: int) -> Dict[str, Any]:
    res = {}
    for aw in ["MVP","OPOY","DPOY","ROY"]:
        r = session.exec(select(AwardResult).where(AwardResult.season==season, AwardResult.award==aw, AwardResult.rank==1)).first()
        if not r:
            res[aw] = None
        else:
            p = session.get(Player, r.player_id) if r.player_id else None
            res[aw] = {
                "player_id": r.player_id, "name": _name(p) if p else r.player_name,
                "team_id": r.team_id, "position": getattr(p,"position",None) if p else r.position, "score": r.score
            }
    return res

def progression_risers_fallers(session: Session, season: int, top_n: int = 5) -> Dict[str, Any]:
    rows = session.exec(select(PlayerProgression).where(PlayerProgression.season==season)).all()
    if not rows: return {"risers":[],"fallers":[]}
    import json
    def total(r):
        b = json.loads(r.before_json); a = json.loads(r.after_json)
        keys = ["awareness","throw_accuracy","throw_power","catching","tackling","speed","agility","strength","stamina","morale"]
        return sum(int(a.get(k,0))-int(b.get(k,0)) for k in keys)
    augmented = []
    for r in rows:
        p = session.get(Player, r.player_id)
        augmented.append((r, total(r), _name(p), getattr(p,"position",None), getattr(p,"team_id",None)))
    augmented.sort(key=lambda t: t[1], reverse=True)
    risers = [{"player_id": rr.player_id, "name": nm, "position": pos, "team_id": tid, "total_delta": td} for (rr,td,nm,pos,tid) in augmented[:top_n]]
    fallers = [{"player_id": rr.player_id, "name": nm, "position": pos, "team_id": tid, "total_delta": td} for (rr,td,nm,pos,tid) in augmented[-top_n:]]
    return {"risers":risers, "fallers":fallers}
