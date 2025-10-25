from __future__ import annotations
from typing import Dict, List, Tuple, Iterable
from dataclasses import dataclass
from sqlmodel import Session, select
from app.models.coach_focus import (
    CoachFocusAssignment, TeamWeeklyCoachEffects, TeamSeasonFocusTally,
    CoachFocus, CoachRole
)

# ===== Role weights =====
ROLE_WEIGHT: Dict[CoachRole, float] = {
    CoachRole.HC: 2.0,
    CoachRole.OC: 1.5,
    CoachRole.DC: 1.5,
    CoachRole.AC1: 1.0,
    CoachRole.AC2: 1.0,
}

# ===== Effect constants (tunable, modest by design) =====
# These are the BASE per-coach deltas before role weight is applied.
# They are additive, then later clamped by the sim to sane ranges.
BASE_EFFECTS = {
    CoachFocus.OF_GAMEPLAN: dict(
        run_pass_tendency_delta=+0.015,     # tilt ~1.5% toward pass per weighted coach
        offensive_aggression_delta=+0.02,
        pace_delta=+0.015,
        fourth_down_delta=+0.01,
        two_point_delta=+0.01,
    ),
    CoachFocus.DF_GAMEPLAN: dict(
        defensive_aggression_delta=+0.02,
        pace_delta=-0.01,                   # slightly slower to help defense
        fourth_down_delta=-0.005,           # more conservative on 4th (def field position)
        two_point_delta=-0.005,
    ),
    CoachFocus.TRAINING: dict(
        injury_prob_multiplier=-0.03,       # -3% per weighted coach
        stamina_drain_multiplier=-0.02,     # -2% per weighted coach
    ),
    CoachFocus.DEVELOPMENT: dict(
        # In-week: no immediate sim impact; tallied for end-of-year bonuses
    ),
    CoachFocus.SCOUTING: dict(
        # Hook for draft/FA intel; no weekly sim impact (yet). You can add discovery bonuses later.
    ),
    CoachFocus.SPECIAL_TEAMS: dict(
        special_teams_quality_delta=+0.03,  # small ST boost per weighted coach
    ),
    CoachFocus.TWO_MIN_OFFENSE: dict(
        two_min_offense_success_delta=+0.03 # +3% absolute success per weighted coach in 2-min situations
    ),
}

# ===== Clamp helpers (engine will clamp again if needed) =====
def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

@dataclass
class TeamFocusBundle:
    """
    The shape the sim can consume easily. Values are already aggregated and clamped modestly.
    """
    run_pass_tendency_delta: float
    offensive_aggression_delta: float
    defensive_aggression_delta: float
    pace_delta: float
    fourth_down_delta: float
    two_point_delta: float
    special_teams_quality_delta: float
    injury_prob_multiplier: float
    stamina_drain_multiplier: float
    two_min_offense_success_delta: float

# ===== Public API =====

def set_coach_focus(sess: Session, coach_id: int, team_id: int, season: int, week: int, role: CoachRole, focus: CoachFocus):
    """
    Upsert this week's focus for a coach. We store one row per (coach, season, week).
    """
    row = sess.exec(select(CoachFocusAssignment).where(
        CoachFocusAssignment.coach_id==coach_id,
        CoachFocusAssignment.season==season,
        CoachFocusAssignment.week==week
    )).first()
    if not row:
        row = CoachFocusAssignment(coach_id=coach_id, team_id=team_id, season=season, week=week, role=role, focus=focus)
    else:
        row.team_id = team_id
        row.role = role
        row.focus = focus
    sess.add(row)
    sess.commit()

def get_team_week_focuses(sess: Session, team_id: int, season: int, week: int) -> List[CoachFocusAssignment]:
    return list(sess.exec(select(CoachFocusAssignment).where(
        CoachFocusAssignment.team_id==team_id,
        CoachFocusAssignment.season==season,
        CoachFocusAssignment.week==week
    )))

def aggregate_weekly_effects(sess: Session, team_id: int, season: int, week: int) -> TeamFocusBundle:
    assigns = get_team_week_focuses(sess, team_id, season, week)

    # Start with neutral
    agg: Dict[str, float] = dict(
        run_pass_tendency_delta=0.0,
        offensive_aggression_delta=0.0,
        defensive_aggression_delta=0.0,
        pace_delta=0.0,
        fourth_down_delta=0.0,
        two_point_delta=0.0,
        special_teams_quality_delta=0.0,
        injury_prob_multiplier=0.0,   # will be 1.0 + sum
        stamina_drain_multiplier=0.0, # will be 1.0 + sum
        two_min_offense_success_delta=0.0,
    )

    # Apply role-weighted base effects
    for a in assigns:
        base = BASE_EFFECTS.get(a.focus, {})
        w = ROLE_WEIGHT.get(a.role, 1.0)
        for k, v in base.items():
            agg[k] = agg.get(k, 0.0) + (v * w)

    # Convert relative multipliers to 1+delta; clamp deltas
    injury_mult = _clamp(1.0 + agg["injury_prob_multiplier"], 0.85, 1.05)
    stamina_mult = _clamp(1.0 + agg["stamina_drain_multiplier"], 0.85, 1.05)

    bundle = TeamFocusBundle(
        run_pass_tendency_delta=_clamp(agg["run_pass_tendency_delta"], -0.05, 0.05),
        offensive_aggression_delta=_clamp(agg["offensive_aggression_delta"], -0.05, 0.05),
        defensive_aggression_delta=_clamp(agg["defensive_aggression_delta"], -0.05, 0.05),
        pace_delta=_clamp(agg["pace_delta"], -0.05, 0.05),
        fourth_down_delta=_clamp(agg["fourth_down_delta"], -0.04, 0.04),
        two_point_delta=_clamp(agg["two_point_delta"], -0.04, 0.04),
        special_teams_quality_delta=_clamp(agg["special_teams_quality_delta"], -0.08, 0.08),
        injury_prob_multiplier=injury_mult,
        stamina_drain_multiplier=stamina_mult,
        two_min_offense_success_delta=_clamp(agg["two_min_offense_success_delta"], -0.08, 0.10),
    )

    # Persist snapshot
    snap = sess.exec(select(TeamWeeklyCoachEffects).where(
        TeamWeeklyCoachEffects.team_id==team_id,
        TeamWeeklyCoachEffects.season==season,
        TeamWeeklyCoachEffects.week==week
    )).first()
    if not snap:
        snap = TeamWeeklyCoachEffects(team_id=team_id, season=season, week=week)
    snap.run_pass_tendency_delta = bundle.run_pass_tendency_delta
    snap.offensive_aggression_delta = bundle.offensive_aggression_delta
    snap.defensive_aggression_delta = bundle.defensive_aggression_delta
    snap.pace_delta = bundle.pace_delta
    snap.fourth_down_delta = bundle.fourth_down_delta
    snap.two_point_delta = bundle.two_point_delta
    snap.special_teams_quality_delta = bundle.special_teams_quality_delta
    snap.injury_prob_multiplier = bundle.injury_prob_multiplier
    snap.stamina_drain_multiplier = bundle.stamina_drain_multiplier
    snap.two_min_offense_success_delta = bundle.two_min_offense_success_delta
    sess.add(snap)
    sess.commit()

    # Update season tally
    _bump_season_tally(sess, team_id, season, assigns)

    return bundle

def _tally_fields_for_focus(f: CoachFocus) -> str:
    return {
        CoachFocus.OF_GAMEPLAN: "of_gameplan_points",
        CoachFocus.DF_GAMEPLAN: "df_gameplan_points",
        CoachFocus.TRAINING: "training_points",
        CoachFocus.DEVELOPMENT: "development_points",
        CoachFocus.SCOUTING: "scouting_points",
        CoachFocus.SPECIAL_TEAMS: "special_teams_points",
        CoachFocus.TWO_MIN_OFFENSE: "two_min_offense_points",
    }[f]

def _get_or_create_tally(sess: Session, team_id: int, season: int) -> TeamSeasonFocusTally:
    row = sess.exec(select(TeamSeasonFocusTally).where(
        TeamSeasonFocusTally.team_id==team_id, TeamSeasonFocusTally.season==season
    )).first()
    if not row:
        row = TeamSeasonFocusTally(team_id=team_id, season=season)
    return row

def _bump_season_tally(sess: Session, team_id: int, season: int, assigns: List[CoachFocusAssignment]):
    tally = _get_or_create_tally(sess, team_id, season)
    for a in assigns:
        fld = _tally_fields_for_focus(a.focus)
        w = ROLE_WEIGHT.get(a.role, 1.0)
        setattr(tally, fld, getattr(tally, fld) + w)
    sess.add(tally)
    sess.commit()

# ===== End-of-season: convert DEVELOPMENT tally into progression bonus =====

def development_progression_bonus(sess: Session, team_id: int, season: int) -> float:
    """
    Returns a small scalar bonus (e.g., +0.0..+0.05) for player development
    to be applied during annual progression to players on this team.
    """
    tally = _get_or_create_tally(sess, team_id, season)
    # Each weighted "focus week" contributes +0.005 up to +0.05 cap
    bonus = min(0.05, 0.005 * tally.development_points)
    return bonus

