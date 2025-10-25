# app/services/coach_progression.py
from __future__ import annotations
from random import Random
from sqlmodel import Session, select
from app.models.coach import Coach, CoachRole

def _adj(x: int, d: int) -> int:
    return max(30, min(99, x + d))

def _delta_from_rank(top8: bool, bottom8: bool) -> int:
    return 2 if top8 else (-1 if bottom8 else 0)

def progress_coaches_end_of_season(sess: Session, team_id: int, season: int, rng: Random, metrics: dict):
    """
    metrics expected: {
      'off_rank','def_rank','st_rank','rz_off_rank','rz_def_rank','penalty_rate','lg_penalty_rate',
      'w_pct','two_min_eff','lg_two_min_eff','pace_rank'
    }
    """
    top8 = lambda r: r and r <= 8
    bot8 = lambda r: r and r >= 25  # for 32 teams

    for c in sess.exec(select(Coach).where(Coach.team_id==team_id, Coach.active==True)).all():
        if c.role == CoachRole.HC:
            c.clock_management = _adj(c.clock_management, _delta_from_rank(top8(metrics['pace_rank']), bot8(metrics['pace_rank'])))
            c.challenge_sense  = _adj(c.challenge_sense, 1 if metrics['two_min_eff'] >= metrics['lg_two_min_eff'] else -1)
            c.discipline       = _adj(c.discipline, 1 if metrics['penalty_rate'] <= metrics['lg_penalty_rate']*0.95 else -1)
            c.motivation_chemistry = _adj(c.motivation_chemistry, 2 if metrics['w_pct'] >= 0.65 else (-1 if metrics['w_pct'] <= 0.35 else 0))
        if c.role in {CoachRole.HC, CoachRole.OC, CoachRole.AC1, CoachRole.AC2}:
            c.red_zone_offense = _adj(c.red_zone_offense, _delta_from_rank(top8(metrics['rz_off_rank']), bot8(metrics['rz_off_rank'])))
        if c.role in {CoachRole.HC, CoachRole.DC, CoachRole.AC1, CoachRole.AC2}:
            c.red_zone_defense = _adj(c.red_zone_defense, _delta_from_rank(top8(metrics['rz_def_rank']), bot8(metrics['rz_def_rank'])))
        if c.role in {CoachRole.OC, CoachRole.AC1, CoachRole.AC2}:
            c.player_dev_offense = _adj(c.player_dev_offense, 1 if metrics['w_pct'] >= 0.55 else 0)
        if c.role in {CoachRole.DC, CoachRole.AC1, CoachRole.AC2}:
            c.player_dev_defense = _adj(c.player_dev_defense, 1 if metrics['w_pct'] >= 0.55 else 0)
        # mild stochastic drift
        for attr in ("offensive_aggression","defensive_aggression","coverage_mix","blitz_rate","special_teams_quality","fake_trick_tendency"):
            setattr(c, attr, _adj(getattr(c, attr), rng.choice([-1,0,1])))
        sess.add(c)
    sess.commit()
