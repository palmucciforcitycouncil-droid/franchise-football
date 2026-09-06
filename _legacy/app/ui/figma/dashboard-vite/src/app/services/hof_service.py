from __future__ import annotations
from typing import List, Dict, Any
from sqlmodel import Session, select
from app.models.hof import HallOfFameInductee, HoFType

def _try(path: str, name: str):
    try:
        mod = __import__(path, fromlist=[name]); return getattr(mod, name)
    except Exception:
        return None

# Optional imports - calculators degrade gracefully if models don't exist
PlayerCareerAgg = _try("app.models.stats", "PlayerCareerAgg")
CoachCareerAgg = _try("app.models.stats", "CoachCareerAgg")
Coach = _try("app.models.coach", "Coach")
Player = _try("app.models.player", "Player")

# Transparent, tunable thresholds (MVP)
PLAYER_THRESH = {
    "yards_pass": 50_000, "yards_rush": 10_000, "yards_rec": 12_000, "sacks": 120, "ints": 60, "td_total": 120,
    "rings": 2, "mvp": 1, "opoy_dpoy": 2
}
COACH_THRESH = {
    "wins": 150, "rings": 2, "coy": 2
}

def _score_player(c) -> float:
    s = 0.0
    s += getattr(c, "pass_yds_career", 0) / 1_000_000
    s += getattr(c, "rush_yds_career", 0) / 200_000
    s += getattr(c, "rec_yds_career", 0) / 240_000
    s += getattr(c, "sacks_career", 0) * 0.8
    s += getattr(c, "ints_career", 0) * 1.0
    s += getattr(c, "td_career", 0) * 0.5
    s += getattr(c, "rings", 0) * 15
    s += getattr(c, "mvps", 0) * 20
    s += getattr(c, "opoy_dpoy", 0) * 10
    return s

def _score_coach(c) -> float:
    s = 0.0
    s += getattr(c, "wins", 0) * 0.5
    s += getattr(c, "rings", 0) * 25
    s += getattr(c, "coy", 0) * 12
    s += getattr(c, "win_pct", 0.0) * 100
    return s

def induct_hof(sess: Session, *, season: int) -> Dict[str, Any]:
    # Idempotent: clear and rebuild this season's inductions
    existing = list(sess.exec(select(HallOfFameInductee).where(HallOfFameInductee.season==season)))
    for inductee in existing:
        sess.delete(inductee)
    sess.commit()

    players = []
    coaches = []
    
    if PlayerCareerAgg:
        players = list(sess.exec(select(PlayerCareerAgg)))
    if CoachCareerAgg:
        coaches = list(sess.exec(select(CoachCareerAgg)))

    out = []

    # Players
    for c in players:
        passes = (
            getattr(c,"pass_yds_career",0) >= PLAYER_THRESH["yards_pass"] or
            getattr(c,"rush_yds_career",0) >= PLAYER_THRESH["yards_rush"] or
            getattr(c,"rec_yds_career",0)  >= PLAYER_THRESH["yards_rec"] or
            getattr(c,"sacks_career",0)    >= PLAYER_THRESH["sacks"] or
            getattr(c,"ints_career",0)     >= PLAYER_THRESH["ints"] or
            getattr(c,"td_career",0)       >= PLAYER_THRESH["td_total"] or
            getattr(c,"rings",0)           >= PLAYER_THRESH["rings"] or
            getattr(c,"mvps",0)            >= PLAYER_THRESH["mvp"] or
            getattr(c,"opoy_dpoy",0)       >= PLAYER_THRESH["opoy_dpoy"]
        )
        if passes:
            score = _score_player(c)
            sess.add(HallOfFameInductee(season=season, entity_type=HoFType.PLAYER,
                                        player_id=c.player_id, summary="Career milestone thresholds met", score=score))
    # Coaches
    for c in coaches:
        passes = (
            getattr(c,"wins",0)  >= COACH_THRESH["wins"] or
            getattr(c,"rings",0) >= COACH_THRESH["rings"] or
            getattr(c,"coy",0)   >= COACH_THRESH["coy"]
        )
        if passes:
            score = _score_coach(c)
            sess.add(HallOfFameInductee(season=season, entity_type=HoFType.COACH,
                                        coach_id=c.coach_id, summary="Coaching career thresholds met", score=score))
    sess.commit()
    rows = list(sess.exec(select(HallOfFameInductee).where(HallOfFameInductee.season==season)))
    out = [{"id":r.id,"type":r.entity_type.value,"player_id":r.player_id,"coach_id":r.coach_id,"score":r.score} for r in rows]
    return {"ok": True, "inductees": out}