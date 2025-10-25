# app/services/coach_modifiers.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
from sqlmodel import Session, select
from app.models.coach import Coach, CoachRole

@dataclass
class CoachSeasonModifiers:
    off_gameplan: float = 0.0
    def_gameplan: float = 0.0
    two_min_offense: float = 0.0
    special_teams: float = 0.0
    discipline: float = 0.0          # fewer penalties
    stamina_injury: float = 0.0      # better stamina / fewer/shorter injuries
    development: float = 0.0         # end-of-year player progression

ROLE_WEIGHT = {"HC": 2.0, "OC": 1.5, "DC": 1.5, "AC": 1.0}

def compute_team_modifiers(sess: Session, team_id: int) -> CoachSeasonModifiers:
    """
    Uses each coach's weeks_focus_bank and role weight to compute team-wide modifiers.
    Normalize by total possible weeks (e.g., 18 = 17 + bye).
    """
    staff = list(sess.exec(select(Coach).where(Coach.team_id == team_id)).all())
    if not staff:
        return CoachSeasonModifiers()

    total_weeks = max(1, max(c.weeks_focus_bank for c in staff))
    mod = CoachSeasonModifiers()

    def add(weight, amt): 
        return (weight * amt) / (total_weeks * 2.0)  # scale down for MVP safety

    for c in staff:
        w = ROLE_WEIGHT.get(c.role, 1.0)
        if c.focus == "OFF_GAMEPLAN":
            mod.off_gameplan += add(w, (c.off_rating-70)/30.0 + 0.5)
        elif c.focus == "DEF_GAMEPLAN":
            mod.def_gameplan += add(w, (c.def_rating-70)/30.0 + 0.5)
        elif c.focus == "TWO_MIN_OFFENSE":
            mod.two_min_offense += add(w, (c.off_rating-70)/30.0 + 0.5)
        elif c.focus == "SPECIAL_TEAMS":
            mod.special_teams += add(w, (c.st_rating-70)/30.0 + 0.5)
        elif c.focus == "TRAINING":
            mod.stamina_injury += add(w, (c.discipline-70)/30.0 + 0.5)
        elif c.focus == "DEVELOPMENT":
            mod.development += add(w, (c.dev_rating-70)/30.0 + 0.5)
        elif c.focus == "SCOUTING":
            # MVP: apply small discipline/st penalties bump via scouting preparedness
            mod.discipline += add(w, 0.25)
            mod.special_teams += add(w, 0.15)

    # general HC oversight grants a small global discipline bonus
    for c in staff:
        if c.role == "HC":
            mod.discipline += 0.05 * ROLE_WEIGHT["HC"] * ((c.discipline-70)/30.0 + 0.5) / 2.0
            break

    return mod


