# app/api/routes/coach_focus_api.py
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_engine
from app.models.coach import Coach, CoachRole, CoachFocus
from app.services.coach_focus import set_focus, compute_week_modifiers

router = APIRouter(prefix="/api/v1/coach", tags=["coach"])

def get_session():
    from sqlmodel import Session
    return Session(get_engine())

class SetFocusReq(BaseModel):
    team_id: int
    season: int
    week: int
    coach_id: int
    role: CoachRole
    focus: CoachFocus

@router.post("/set_focus")
def api_set_focus(req: SetFocusReq, sess: Session = Depends(get_session)):
    set_focus(sess, **req.model_dump())
    return {"ok": True}

class ModPreview(BaseModel):
    run_pass_shift: float
    off_success_mult: float
    def_success_mult: float
    rz_off_bonus: float
    rz_def_bonus: float
    pace_mult: float
    two_min_off_bonus: float
    fourth_down_bias: float
    two_point_bias: float
    challenge_edge: float
    st_eff_bonus: float
    penalty_rate_mult: float
    fake_trick_prob: float
    blitz_bias: float
    coverage_eff: float
    dev_off_week: float
    dev_def_week: float
    chemistry_boost: float

@router.get("/modifiers_preview", response_model=ModPreview)
def modifiers_preview(team_id: int, season: int, week: int, sess: Session = Depends(get_session)):
    m = compute_week_modifiers(sess, team_id, season, week)
    return ModPreview(**m.__dict__)

class CoachFocusDTO(BaseModel):
    coach_id: int
    coach_name: str
    role: CoachRole
    run_pass_tendency: int
    offensive_aggression: int
    defensive_aggression: int
    pace: int
    clock_management: int
    fourth_down_tendency: int
    two_point_tendency: int
    challenge_sense: int
    discipline: int
    motivation_chemistry: int
    player_dev_offense: int
    player_dev_defense: int
    red_zone_offense: int
    blitz_rate: int
    coverage_mix: int
    red_zone_defense: int
    special_teams_quality: int
    fake_trick_tendency: int
    current_focus: CoachFocus | None = None

@router.get("/team_focuses", response_model=list[CoachFocusDTO])
def get_team_focuses(team_id: int, season: int, week: int, sess: Session = Depends(get_session)):
    # Get team coaches
    coaches = list(sess.exec(select(Coach).where(Coach.team_id==team_id, Coach.active==True)).all())
    
    # Get current week's focus assignments
    from app.services.coach_focus import _focus_map
    focus_map = _focus_map(sess, team_id, season, week)
    
    result = []
    for coach in coaches:
        result.append(CoachFocusDTO(
            coach_id=coach.coach_id,
            coach_name=coach.coach_name,
            role=coach.role,
            run_pass_tendency=coach.run_pass_tendency,
            offensive_aggression=coach.offensive_aggression,
            defensive_aggression=coach.defensive_aggression,
            pace=coach.pace,
            clock_management=coach.clock_management,
            fourth_down_tendency=coach.fourth_down_tendency,
            two_point_tendency=coach.two_point_tendency,
            challenge_sense=coach.challenge_sense,
            discipline=coach.discipline,
            motivation_chemistry=coach.motivation_chemistry,
            player_dev_offense=coach.player_dev_offense,
            player_dev_defense=coach.player_dev_defense,
            red_zone_offense=coach.red_zone_offense,
            blitz_rate=coach.blitz_rate,
            coverage_mix=coach.coverage_mix,
            red_zone_defense=coach.red_zone_defense,
            special_teams_quality=coach.special_teams_quality,
            fake_trick_tendency=coach.fake_trick_tendency,
            current_focus=focus_map.get(coach.coach_id)
        ))
    
    return result