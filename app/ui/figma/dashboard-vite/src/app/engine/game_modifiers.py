# app/engine/game_modifiers.py
from __future__ import annotations
from sqlmodel import Session
from app.services.coach_focus import compute_week_modifiers, TeamWeekModifiers

def get_team_mods_for_week(sess: Session, team_id: int, season: int, week: int) -> TeamWeekModifiers:
    return compute_week_modifiers(sess, team_id, season, week)

def apply_offense_modifiers(off_success_prob: float, team_mods: TeamWeekModifiers) -> float:
    """Apply offense efficiency modifiers to success probability."""
    return off_success_prob * (1.0 + team_mods.offense_eff)

def apply_defense_modifiers(opp_off_success_prob: float, team_mods: TeamWeekModifiers) -> float:
    """Apply defense efficiency modifiers to opponent offense success probability."""
    return opp_off_success_prob * (1.0 - team_mods.defense_eff)

def apply_special_teams_modifiers(fg_make_prob: float, punt_net_yards: float, team_mods: TeamWeekModifiers) -> tuple[float, float]:
    """Apply special teams modifiers to FG make probability and punt net yards."""
    fg_prob = fg_make_prob * (1.0 + team_mods.st_eff)
    punt_yards = punt_net_yards * (1.0 + 0.5 * team_mods.st_eff)
    return fg_prob, punt_yards

def apply_two_minute_modifiers(td_prob: float, team_mods: TeamWeekModifiers, is_two_minute: bool) -> float:
    """Apply two-minute offense modifiers to touchdown probability."""
    if is_two_minute:
        return td_prob * (1.0 + team_mods.two_min_score_boost)
    return td_prob

def apply_injury_modifiers(injury_prob: float, team_mods: TeamWeekModifiers) -> float:
    """Apply injury probability modifiers."""
    return injury_prob * (1.0 + team_mods.injury_prob_mult)

def apply_stamina_modifiers(stamina_decay: float, team_mods: TeamWeekModifiers) -> float:
    """Apply stamina decay modifiers."""
    return stamina_decay * (1.0 + team_mods.stamina_decay_mult)

def apply_penalty_modifiers(penalty_rate: float, team_mods: TeamWeekModifiers) -> float:
    """Apply penalty rate modifiers."""
    return penalty_rate * (1.0 + team_mods.penalty_rate_mult)

def apply_all_modifiers(
    off_success_prob: float,
    opp_off_success_prob: float,
    fg_make_prob: float,
    punt_net_yards: float,
    td_prob: float,
    injury_prob: float,
    stamina_decay: float,
    penalty_rate: float,
    team_mods: TeamWeekModifiers,
    is_two_minute: bool = False
) -> dict[str, float]:
    """Apply all modifiers and return a dictionary of modified values."""
    return {
        "off_success_prob": apply_offense_modifiers(off_success_prob, team_mods),
        "opp_off_success_prob": apply_defense_modifiers(opp_off_success_prob, team_mods),
        "fg_make_prob": apply_special_teams_modifiers(fg_make_prob, punt_net_yards, team_mods)[0],
        "punt_net_yards": apply_special_teams_modifiers(fg_make_prob, punt_net_yards, team_mods)[1],
        "td_prob": apply_two_minute_modifiers(td_prob, team_mods, is_two_minute),
        "injury_prob": apply_injury_modifiers(injury_prob, team_mods),
        "stamina_decay": apply_stamina_modifiers(stamina_decay, team_mods),
        "penalty_rate": apply_penalty_modifiers(penalty_rate, team_mods),
    }


