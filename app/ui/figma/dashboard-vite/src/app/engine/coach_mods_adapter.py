# app/engine/coach_mods_adapter.py
from __future__ import annotations
from sqlmodel import Session
from app.services.coach_focus import compute_week_modifiers, TeamWeekModifiers

def get_team_week_mods(sess: Session, team_id: int, season: int, week: int) -> TeamWeekModifiers:
    return compute_week_modifiers(sess, team_id, season, week)

def apply_offense_modifiers(offense_prob: float, team_mods: TeamWeekModifiers) -> float:
    """Apply offense success modifiers to probability."""
    return offense_prob * (1.0 + team_mods.off_success_mult)

def apply_defense_modifiers(defense_prob: float, team_mods: TeamWeekModifiers) -> float:
    """Apply defense success modifiers to probability."""
    return defense_prob * (1.0 + team_mods.def_success_mult)

def apply_run_pass_shift(run_pass_bias: float, team_mods: TeamWeekModifiers) -> float:
    """Apply run/pass tendency shift."""
    return run_pass_bias + team_mods.run_pass_shift

def apply_pace_modifiers(plays_per_game: float, team_mods: TeamWeekModifiers) -> float:
    """Apply pace modifiers to plays per game."""
    return plays_per_game * (1.0 + team_mods.pace_mult)

def apply_red_zone_modifiers(rz_td_prob: float, team_mods: TeamWeekModifiers, is_offense: bool) -> float:
    """Apply red zone modifiers to TD probability."""
    bonus = team_mods.rz_off_bonus if is_offense else team_mods.rz_def_bonus
    return rz_td_prob * (1.0 + bonus)

def apply_two_minute_modifiers(two_min_td_prob: float, team_mods: TeamWeekModifiers) -> float:
    """Apply two-minute offense modifiers to TD probability."""
    return two_min_td_prob * (1.0 + team_mods.two_min_off_bonus)

def apply_fourth_down_modifiers(fourth_down_aggr: float, team_mods: TeamWeekModifiers) -> float:
    """Apply fourth down tendency modifiers."""
    return fourth_down_aggr + team_mods.fourth_down_bias

def apply_two_point_modifiers(two_point_aggr: float, team_mods: TeamWeekModifiers) -> float:
    """Apply two-point conversion tendency modifiers."""
    return two_point_aggr + team_mods.two_point_bias

def apply_challenge_modifiers(challenge_success: float, team_mods: TeamWeekModifiers) -> float:
    """Apply challenge success modifiers."""
    return challenge_success + team_mods.challenge_edge

def apply_special_teams_modifiers(st_success: float, team_mods: TeamWeekModifiers) -> float:
    """Apply special teams efficiency modifiers."""
    return st_success * (1.0 + team_mods.st_eff_bonus)

def apply_penalty_modifiers(penalty_rate: float, team_mods: TeamWeekModifiers) -> float:
    """Apply penalty rate modifiers."""
    return penalty_rate * (1.0 + team_mods.penalty_rate_mult)

def apply_blitz_modifiers(blitz_bias: float, team_mods: TeamWeekModifiers) -> float:
    """Apply blitz tendency modifiers."""
    return blitz_bias + team_mods.blitz_bias

def apply_coverage_modifiers(coverage_efficiency: float, team_mods: TeamWeekModifiers) -> float:
    """Apply coverage efficiency modifiers."""
    return coverage_efficiency + team_mods.coverage_eff

def apply_fake_trick_modifiers(fake_play_prob: float, team_mods: TeamWeekModifiers) -> float:
    """Apply fake/trick play probability modifiers."""
    return fake_play_prob + team_mods.fake_trick_prob

def apply_all_modifiers(
    offense_prob: float,
    defense_prob: float,
    run_pass_bias: float,
    plays_per_game: float,
    rz_td_prob_off: float,
    rz_td_prob_def: float,
    two_min_td_prob: float,
    fourth_down_aggr: float,
    two_point_aggr: float,
    challenge_success: float,
    st_success: float,
    penalty_rate: float,
    blitz_bias: float,
    coverage_efficiency: float,
    fake_play_prob: float,
    team_mods: TeamWeekModifiers
) -> dict[str, float]:
    """Apply all modifiers and return a dictionary of modified values."""
    return {
        "offense_prob": apply_offense_modifiers(offense_prob, team_mods),
        "defense_prob": apply_defense_modifiers(defense_prob, team_mods),
        "run_pass_bias": apply_run_pass_shift(run_pass_bias, team_mods),
        "plays_per_game": apply_pace_modifiers(plays_per_game, team_mods),
        "rz_td_prob_off": apply_red_zone_modifiers(rz_td_prob_off, team_mods, True),
        "rz_td_prob_def": apply_red_zone_modifiers(rz_td_prob_def, team_mods, False),
        "two_min_td_prob": apply_two_minute_modifiers(two_min_td_prob, team_mods),
        "fourth_down_aggr": apply_fourth_down_modifiers(fourth_down_aggr, team_mods),
        "two_point_aggr": apply_two_point_modifiers(two_point_aggr, team_mods),
        "challenge_success": apply_challenge_modifiers(challenge_success, team_mods),
        "st_success": apply_special_teams_modifiers(st_success, team_mods),
        "penalty_rate": apply_penalty_modifiers(penalty_rate, team_mods),
        "blitz_bias": apply_blitz_modifiers(blitz_bias, team_mods),
        "coverage_efficiency": apply_coverage_modifiers(coverage_efficiency, team_mods),
        "fake_play_prob": apply_fake_trick_modifiers(fake_play_prob, team_mods),
    }


