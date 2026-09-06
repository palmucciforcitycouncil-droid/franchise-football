from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from statistics import mean
from sqlmodel import Session, select
from app.models.awards import AwardsWeekly, AwardsAnnual, WeeklyAwardType, AnnualAwardType

def _try(path: str, name: str):
    try:
        mod = __import__(path, fromlist=[name]); return getattr(mod, name)
    except Exception:
        return None

# Optional imports - calculators degrade gracefully if models don't exist
PlayerBox = _try("app.models.results", "PlayerBox")
TeamGameStats = _try("app.models.results", "TeamGameStats")
Game = _try("app.models.schedule", "Game")
Team = _try("app.models.team", "Team")
PlayerSeasonStats = _try("app.models.stats", "PlayerSeasonStats")
CoachSeasonStats = _try("app.models.stats", "CoachSeasonStats")
PlayerCareerAgg = _try("app.models.stats", "PlayerCareerAgg")
CoachCareerAgg = _try("app.models.stats", "CoachCareerAgg")
Standings = _try("app.models.standings", "Standings")
Coach = _try("app.models.coach", "Coach")
Player = _try("app.models.player", "Player")

# ---------------------- Weekly Awards (uses PlayerBox only) ----------------------
def _off_score(box) -> float:
    # Simple fantasy-like scoring
    return (getattr(box, "pass_yds", 0)*0.04 + getattr(box, "pass_td", 0)*4 - getattr(box, "pass_int", 0)*2 +
            getattr(box, "rush_yds", 0)*0.1 + getattr(box, "rush_td", 0)*6 +
            getattr(box, "rec_yds", 0)*0.1 + getattr(box, "rec_td", 0)*6)

def _def_score(box) -> float:
    return (getattr(box, "tkl", 0)*1.0 + getattr(box, "tfl", 0)*1.5 + getattr(box, "sack", 0)*3.0 + 
            getattr(box, "ints", 0)*5.0 + getattr(box, "pdef", 0)*1.0 + getattr(box, "ff", 0)*2.0 + getattr(box, "fr", 0)*2.0)

def _st_score(box) -> float:
    return (getattr(box, "fgm", 0)*3.0 + (getattr(box, "fga", 0) - getattr(box, "fgm", 0))*-1.0 + 
            getattr(box, "xpm", 0)*1.0 + (getattr(box, "xpa", 0) - getattr(box, "xpm", 0))*-1.0 + 
            getattr(box, "kr_yds", 0)*0.02 + getattr(box, "pr_yds", 0)*0.03)

def compute_weekly_awards(sess: Session, *, season: int, week: int) -> Dict[str, Any]:
    # Clear and recompute (idempotent)
    if PlayerBox:
        sess.exec(select(AwardsWeekly).where(AwardsWeekly.season==season, AwardsWeekly.week==week))
        # Delete existing awards for this week
        existing = list(sess.exec(select(AwardsWeekly).where(AwardsWeekly.season==season, AwardsWeekly.week==week)))
        for award in existing:
            sess.delete(award)
        sess.commit()

        rows = list(sess.exec(select(PlayerBox).where(PlayerBox.season==season, PlayerBox.week==week)))
        if not rows:
            return {"ok": True, "awards": []}

        # Group into leaderboards
        best_off = max(rows, key=_off_score, default=None)
        best_def = max(rows, key=_def_score, default=None)
        best_st  = max(rows, key=_st_score,  default=None)

        out = []
        if best_off:
            a = AwardsWeekly(season=season, week=week, award_type=WeeklyAwardType.OFF_POW,
                             player_id=best_off.player_id, team_id=best_off.team_id, game_id=best_off.game_id, score=_off_score(best_off))
            sess.add(a); out.append(a)
        if best_def:
            a = AwardsWeekly(season=season, week=week, award_type=WeeklyAwardType.DEF_POW,
                             player_id=best_def.player_id, team_id=best_def.team_id, game_id=best_def.game_id, score=_def_score(best_def))
            sess.add(a); out.append(a)
        if best_st:
            a = AwardsWeekly(season=season, week=week, award_type=WeeklyAwardType.ST_POW,
                             player_id=best_st.player_id, team_id=best_st.team_id, game_id=best_st.game_id, score=_st_score(best_st))
            sess.add(a); out.append(a)
        sess.commit()
        return {"ok": True, "awards": [ {"id":x.id, "type":x.award_type.value, "player_id":x.player_id} for x in out ]}
    else:
        return {"ok": True, "awards": []}

# ---------------------- Annual Awards ----------------------
def _team_win_pct(sess: Session, season: int, team_id: int) -> float:
    try:
        if not Standings:
            return 0.0
        s = sess.exec(select(Standings).where(Standings.season==season, Standings.team_id==team_id)).first()
        if not s: return 0.0
        gp = getattr(s, "wins", 0) + getattr(s, "losses", 0) + getattr(s, "ties", 0)
        return (getattr(s, "wins", 0) + 0.5*getattr(s, "ties", 0)) / gp if gp > 0 else 0.0
    except Exception:
        return 0.0

def _power(sess: Session, season: int, team_id: int) -> float:
    try:
        if not Standings:
            return 1500.0
        s = sess.exec(select(Standings).where(Standings.season==season, Standings.team_id==team_id)).first()
        return getattr(s, "power_rating", 1500.0) if s else 1500.0
    except Exception:
        return 1500.0

def _rookie(player) -> bool:
    return getattr(player, "rookie", False)

def compute_annual_awards(sess: Session, *, season: int) -> Dict[str, Any]:
    # Clear and recompute (idempotent)
    existing = list(sess.exec(select(AwardsAnnual).where(AwardsAnnual.season==season)))
    for award in existing:
        sess.delete(award)
    sess.commit()

    # MVP/OPOY/DPOY/ROY from PlayerSeasonStats
    if PlayerSeasonStats:
        pstats = list(sess.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.season==season)))
        if pstats:
            # Offense composite: pass yds/tds, rush yds/tds, rec yds/tds with positional weighting
            def off_comp(p):
                pos = getattr(p, "pos", "")
                return (getattr(p, "pass_yds", 0)*0.04 + getattr(p, "pass_td", 0)*4 - getattr(p, "pass_int",0)*2 +
                        getattr(p, "rush_yds", 0)*0.1 + getattr(p, "rush_td", 0)*6 +
                        getattr(p, "rec_yds", 0)*0.1 + getattr(p, "rec_td", 0)*6 +
                        (15 if pos=="QB" else 0))  # slight QB bias
            def def_comp(p):
                return (getattr(p,"tackles",0)*1.0 + getattr(p,"sacks",0)*4.0 + getattr(p,"ints",0)*5.0 + getattr(p,"tfl",0)*1.5 + getattr(p,"ff",0)*3.0 + getattr(p,"fr",0)*2.0)

            top_off = max(pstats, key=off_comp)
            top_def = max(pstats, key=def_comp)
            # MVP = best OFF (simple), ROY = best composite among rookies
            mvp = top_off
            rookies = [x for x in pstats if _rookie(x)]
            roy = max(rookies, key=lambda p: off_comp(p)+def_comp(p), default=None)

            def add_annual(typ: AnnualAwardType, player_stat_row):
                if not player_stat_row: return
                sess.add(AwardsAnnual(season=season, award_type=typ,
                                      player_id=player_stat_row.player_id,
                                      team_id=getattr(player_stat_row, "team_id", None),
                                      score=float(off_comp(player_stat_row)+def_comp(player_stat_row))))
            add_annual(AnnualAwardType.MVP, mvp)
            add_annual(AnnualAwardType.OPOY, top_off)
            add_annual(AnnualAwardType.DPOY, top_def)
            add_annual(AnnualAwardType.ROY, roy)

    # COY/GMOY via CoachSeasonStats + team improvement/power
    if CoachSeasonStats:
        try:
            cstats = list(sess.exec(select(CoachSeasonStats).where(CoachSeasonStats.season==season)))
        except Exception:
            cstats = []
        if cstats:
            def coach_score(c):
                win_pct = _team_win_pct(sess, season, getattr(c, "team_id", 0))
                power = _power(sess, season, getattr(c, "team_id", 0))
                delta = getattr(c, "win_delta", 0.0)  # year over year improvement if tracked
                return win_pct*2.5 + (power-1500)/400 + delta
            coy = max(cstats, key=coach_score)
            sess.add(AwardsAnnual(season=season, award_type=AnnualAwardType.COY,
                                  coach_id=coy.coach_id, team_id=getattr(coy, "team_id", None),
                                  score=float(coach_score(coy))))
            # GMOY proxy = same score for now (tune later with cap & draft hit-rate)
            sess.add(AwardsAnnual(season=season, award_type=AnnualAwardType.GMOY,
                                  coach_id=coy.coach_id, team_id=getattr(coy, "team_id", None),
                                  score=float(coach_score(coy))))
    sess.commit()
    return {"ok": True}
