# app/services/coach_focus.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
from sqlmodel import Session, select
from app.models.coach import Coach, CoachRole, CoachFocus, CoachFocusAssignment

# Role weights
ROLE_WT = {CoachRole.AC1:1.0, CoachRole.AC2:1.0, CoachRole.OC:2.0, CoachRole.DC:2.0, CoachRole.HC:4.0}

def _delta(r: int) -> float:
    """Map 0..99 to centered -1..+1 (50 = 0)."""
    return (r - 50) / 50.0

@dataclass
class TeamWeekModifiers:
    # Offense & Defense
    run_pass_shift: float = 0.0          # + favors PASS, - favors RUN
    off_success_mult: float = 0.0
    def_success_mult: float = 0.0
    rz_off_bonus: float = 0.0
    rz_def_bonus: float = 0.0

    # Tempo & Situational
    pace_mult: float = 0.0
    two_min_off_bonus: float = 0.0
    fourth_down_bias: float = 0.0
    two_point_bias: float = 0.0
    challenge_edge: float = 0.0

    # ST & Penalties & Tricks
    st_eff_bonus: float = 0.0
    penalty_rate_mult: float = 0.0
    fake_trick_prob: float = 0.0

    # Defense calls
    blitz_bias: float = 0.0
    coverage_eff: float = 0.0

    # Development (seasonal accumulation)
    dev_off_week: float = 0.0
    dev_def_week: float = 0.0
    chemistry_boost: float = 0.0

# Coefficients (tuned small; engine will treat as additive to probabilities/mults)
COEF = dict(
    RUN_PASS=0.020, OFF=0.010, DEF=0.010, RZ_OFF=0.012, RZ_DEF=0.012,
    PACE=0.015, TWO_MIN=0.015, FOURTH=0.015, TWO_PT=0.015, CHALL=0.008,
    ST=0.010, PEN=-0.012, FAKE=0.010, BLITZ=0.020, COV=0.010,
    DEV_OFF=0.020, DEV_DEF=0.020, CHEM=0.008
)

FOCUS_BOOST = {
    CoachFocus.OFF_GAMEPLAN: ("off_success_mult", 0.012),
    CoachFocus.DEF_GAMEPLAN: ("def_success_mult", 0.012),
    CoachFocus.SPECIAL_TEAMS: ("st_eff_bonus", 0.012),
    CoachFocus.TWO_MINUTE: ("two_min_off_bonus", 0.016),
    CoachFocus.TRAINING: ("penalty_rate_mult", -0.006),  # better practice lowers flags.
    CoachFocus.DEVELOPMENT: ("dev_off_week", 0.010),      # both sides added below
    CoachFocus.SCOUTING: ("coverage_eff", 0.006),         # mild coverage disguise help
}

def set_focus(sess: Session, team_id: int, season: int, week: int, coach_id: int, role: CoachRole, focus: CoachFocus):
    sess.add(CoachFocusAssignment(team_id=team_id, season=season, week=week, coach_id=coach_id, role=role, focus=focus))
    sess.commit()

def _focus_map(sess: Session, team_id: int, season: int, week: int) -> Dict[int, CoachFocus]:
    rows = sess.exec(select(CoachFocusAssignment).where(
        CoachFocusAssignment.team_id==team_id,
        CoachFocusAssignment.season==season,
        CoachFocusAssignment.week==week
    )).all()
    return {r.coach_id: r.focus for r in rows}

def compute_week_modifiers(sess: Session, team_id: int, season: int, week: int) -> TeamWeekModifiers:
    mods = TeamWeekModifiers()
    coaches = list(sess.exec(select(Coach).where(Coach.team_id==team_id, Coach.active==True)))
    f_map = _focus_map(sess, team_id, season, week)

    for c in coaches:
        if not c.role:
            continue
        w = ROLE_WT.get(c.role, 1.0)

        # Baseline contributions
        mods.run_pass_shift  += COEF["RUN_PASS"] * _delta(c.run_pass_tendency) * w
        mods.off_success_mult+= COEF["OFF"]      * (_delta(c.offensive_aggression) + 0.5*_delta(c.red_zone_offense)) * w
        mods.def_success_mult+= COEF["DEF"]      * (_delta(c.defensive_aggression) + 0.5*_delta(c.red_zone_defense)) * w
        mods.rz_off_bonus    += COEF["RZ_OFF"]   * _delta(c.red_zone_offense) * w
        mods.rz_def_bonus    += COEF["RZ_DEF"]   * _delta(c.red_zone_defense) * w

        mods.pace_mult       += COEF["PACE"]     * _delta(c.pace) * w
        mods.two_min_off_bonus += COEF["TWO_MIN"]* (_delta(c.clock_management)) * w
        mods.fourth_down_bias+= COEF["FOURTH"]   * (_delta(c.fourth_down_tendency) + 0.4*_delta(c.offensive_aggression)) * w
        mods.two_point_bias  += COEF["TWO_PT"]   * _delta(c.two_point_tendency) * w
        mods.challenge_edge  += COEF["CHALL"]    * _delta(c.challenge_sense) * w

        mods.st_eff_bonus    += COEF["ST"]       * _delta(c.special_teams_quality) * w
        mods.penalty_rate_mult += COEF["PEN"]    * (_delta(c.discipline)) * w
        mods.fake_trick_prob += COEF["FAKE"]     * _delta(c.fake_trick_tendency) * w

        mods.blitz_bias      += COEF["BLITZ"]    * (_delta(c.blitz_rate) + 0.3*_delta(c.defensive_aggression)) * w
        mods.coverage_eff    += COEF["COV"]      * _delta(c.coverage_mix) * w

        mods.dev_off_week    += COEF["DEV_OFF"]  * _delta(c.player_dev_offense) * (1.0 if c.role in {CoachRole.OC, CoachRole.AC1, CoachRole.AC2} else 0.5) * w/2.0
        mods.dev_def_week    += COEF["DEV_DEF"]  * _delta(c.player_dev_defense) * (1.0 if c.role in {CoachRole.DC, CoachRole.AC1, CoachRole.AC2} else 0.5) * w/2.0
        mods.chemistry_boost += COEF["CHEM"]     * _delta(c.motivation_chemistry) * (1.0 if c.role==CoachRole.HC else 0.5) * w/2.0

        # Focus overlays
        f = f_map.get(c.coach_id)
        if f:
            key, bump = FOCUS_BOOST[f]
            setattr(mods, key, getattr(mods, key) + bump * w)
            if f == CoachFocus.DEVELOPMENT:
                # Apply to both sides for dev focus
                mods.dev_def_week += bump * 0.8 * w
            if f == CoachFocus.TRAINING:
                # Training also reduces penalties slightly more
                mods.penalty_rate_mult += (-0.004) * w
            if f == CoachFocus.TWO_MINUTE:
                # Two-minute also nudges fourth-down decisions a hair
                mods.fourth_down_bias += 0.004 * w

    # Clamp sensitive multipliers
    clamp = lambda v: max(-0.30, min(0.30, v))
    mods.pace_mult = clamp(mods.pace_mult)
    mods.penalty_rate_mult = clamp(mods.penalty_rate_mult)
    mods.two_min_off_bonus = clamp(mods.two_min_off_bonus)
    mods.fourth_down_bias = clamp(mods.fourth_down_bias)
    mods.two_point_bias = clamp(mods.two_point_bias)
    mods.blitz_bias = clamp(mods.blitz_bias)
    mods.fake_trick_prob = max(0.0, min(0.15, mods.fake_trick_prob))
    return mods
