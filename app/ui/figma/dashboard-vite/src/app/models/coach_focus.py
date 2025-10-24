from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field

class CoachFocus(str, Enum):
    OF_GAMEPLAN = "OF_GAMEPLAN"
    DF_GAMEPLAN = "DF_GAMEPLAN"
    TRAINING = "TRAINING"
    DEVELOPMENT = "DEVELOPMENT"
    SCOUTING = "SCOUTING"
    SPECIAL_TEAMS = "SPECIAL_TEAMS"
    TWO_MIN_OFFENSE = "TWO_MIN_OFFENSE"

class CoachRole(str, Enum):
    HC = "HC"
    OC = "OC"
    DC = "DC"
    AC1 = "AC1"
    AC2 = "AC2"

class CoachFocusAssignment(SQLModel, table=True):
    """
    One row per (coach_id, season, week). Allows history/audit and UI review.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    coach_id: int = Field(index=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    role: CoachRole
    focus: CoachFocus

class TeamWeeklyCoachEffects(SQLModel, table=True):
    """
    Snapshot of combined team modifiers after aggregating coaches' focuses for a week.
    Used by the sim engine; persisted for replay/debug.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    week: int = Field(index=True)

    # Offense/Defense gameplan knobs (additive deltas; see service for ranges)
    run_pass_tendency_delta: float = 0.0      # + favors pass; - favors run
    offensive_aggression_delta: float = 0.0
    defensive_aggression_delta: float = 0.0
    pace_delta: float = 0.0
    fourth_down_delta: float = 0.0
    two_point_delta: float = 0.0
    special_teams_quality_delta: float = 0.0

    # Injuries / stamina
    injury_prob_multiplier: float = 1.0
    stamina_drain_multiplier: float = 1.0

    # Two-minute offense
    two_min_offense_success_delta: float = 0.0  # additive to base success prob

class TeamSeasonFocusTally(SQLModel, table=True):
    """
    Tally of how many weeks a team spent on each focus (weighted by role).
    Used to apply end-of-season DEVELOPMENT bonuses.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)

    of_gameplan_points: float = 0.0
    df_gameplan_points: float = 0.0
    training_points: float = 0.0
    development_points: float = 0.0
    scouting_points: float = 0.0
    special_teams_points: float = 0.0
    two_min_offense_points: float = 0.0
