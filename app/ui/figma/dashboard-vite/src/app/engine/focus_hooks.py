from __future__ import annotations
from dataclasses import dataclass
from sqlmodel import Session
from app.services.coach_focus_service import aggregate_weekly_effects, TeamFocusBundle

@dataclass
class PlaycallParams:
    run_pass_bias: float          # base 0.0; +pass / -run
    offense_aggr: float
    defense_aggr: float
    pace: float
    fourth_down: float
    two_point: float
    st_quality: float

def get_focus_bundle(sess: Session, team_id: int, season: int, week: int) -> TeamFocusBundle:
    return aggregate_weekly_effects(sess, team_id, season, week)

def apply_playcall_focus(base: PlaycallParams, f: TeamFocusBundle) -> PlaycallParams:
    return PlaycallParams(
        run_pass_bias = base.run_pass_bias + f.run_pass_tendency_delta,
        offense_aggr  = base.offense_aggr + f.offensive_aggression_delta,
        defense_aggr  = base.defense_aggr + f.defensive_aggression_delta,
        pace          = base.pace + f.pace_delta,
        fourth_down   = base.fourth_down + f.fourth_down_delta,
        two_point     = base.two_point + f.two_point_delta,
        st_quality    = base.st_quality + f.special_teams_quality_delta,
    )

def adjust_injury_probability(base_prob: float, f: TeamFocusBundle) -> float:
    return base_prob * f.injury_prob_multiplier

def adjust_stamina_drain(base_drain: float, f: TeamFocusBundle) -> float:
    return base_drain * f.stamina_drain_multiplier

def adjust_two_minute_success(base_prob: float, f: TeamFocusBundle) -> float:
    return base_prob + f.two_min_offense_success_delta
