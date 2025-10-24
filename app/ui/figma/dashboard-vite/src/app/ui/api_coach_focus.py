from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_session
from app.models.coach_focus import CoachFocusAssignment, TeamWeeklyCoachEffects, TeamSeasonFocusTally, CoachFocus, CoachRole
from app.services.coach_focus_service import set_coach_focus, aggregate_weekly_effects

router = APIRouter(prefix="/api/v1/coach_focus", tags=["coach-focus"])

class SetFocusReq(BaseModel):
    coach_id: int
    team_id: int
    role: CoachRole
    focus: CoachFocus
    season: int
    week: int

@router.post("/set")
def set_focus(body: SetFocusReq, sess: Session = Depends(get_session)):
    set_coach_focus(sess, body.coach_id, body.team_id, body.season, body.week, body.role, body.focus)
    # return updated snapshot for the team/week
    bundle = aggregate_weekly_effects(sess, body.team_id, body.season, body.week)
    return {"ok": True, "bundle": bundle.__dict__}

class WeeklyEffectsDTO(BaseModel):
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

@router.get("/weekly_snapshot", response_model=WeeklyEffectsDTO)
def weekly_snapshot(team_id: int, season: int, week: int, sess: Session = Depends(get_session)):
    row = sess.exec(select(TeamWeeklyCoachEffects).where(
        TeamWeeklyCoachEffects.team_id==team_id,
        TeamWeeklyCoachEffects.season==season,
        TeamWeeklyCoachEffects.week==week
    )).first()
    if not row:
        # compute on-demand if not present
        bundle = aggregate_weekly_effects(sess, team_id, season, week)
        return WeeklyEffectsDTO(**bundle.__dict__)
    return WeeklyEffectsDTO(
        run_pass_tendency_delta=row.run_pass_tendency_delta,
        offensive_aggression_delta=row.offensive_aggression_delta,
        defensive_aggression_delta=row.defensive_aggression_delta,
        pace_delta=row.pace_delta,
        fourth_down_delta=row.fourth_down_delta,
        two_point_delta=row.two_point_delta,
        special_teams_quality_delta=row.special_teams_quality_delta,
        injury_prob_multiplier=row.injury_prob_multiplier,
        stamina_drain_multiplier=row.stamina_drain_multiplier,
        two_min_offense_success_delta=row.two_min_offense_success_delta,
    )

class SeasonTallyDTO(BaseModel):
    of_gameplan_points: float
    df_gameplan_points: float
    training_points: float
    development_points: float
    scouting_points: float
    special_teams_points: float
    two_min_offense_points: float

@router.get("/season_tally", response_model=SeasonTallyDTO)
def season_tally(team_id: int, season: int, sess: Session = Depends(get_session)):
    row = sess.exec(select(TeamSeasonFocusTally).where(
        TeamSeasonFocusTally.team_id==team_id, TeamSeasonFocusTally.season==season
    )).first()
    if not row:
        row = TeamSeasonFocusTally(team_id=team_id, season=season)
    return SeasonTallyDTO(**row.model_dump(exclude={"id", "team_id", "season"}))

class CoachFocusAssignmentDTO(BaseModel):
    id: int
    coach_id: int
    team_id: int
    season: int
    week: int
    role: CoachRole
    focus: CoachFocus

@router.get("/assignments", response_model=List[CoachFocusAssignmentDTO])
def get_assignments(team_id: int, season: int, week: int, sess: Session = Depends(get_session)):
    assignments = sess.exec(select(CoachFocusAssignment).where(
        CoachFocusAssignment.team_id==team_id,
        CoachFocusAssignment.season==season,
        CoachFocusAssignment.week==week
    )).all()
    return [CoachFocusAssignmentDTO(**assignment.model_dump()) for assignment in assignments]

@router.get("/development_bonus")
def get_development_bonus(team_id: int, season: int, sess: Session = Depends(get_session)):
    from app.services.coach_focus_service import development_progression_bonus
    bonus = development_progression_bonus(sess, team_id, season)
    return {"team_id": team_id, "season": season, "development_bonus": bonus}
