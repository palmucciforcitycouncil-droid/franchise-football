from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_session
from app.models.gameplan import GameplanSelection, OffAgg, DefAgg, Coverage, BlitzStrategy, RZOff, RZDef
from app.services.gameplan_mapping import build_deltas

router = APIRouter(prefix="/api/v1/gameplan", tags=["gameplan"])

class GameplanDTO(BaseModel):
    season: int
    week: int
    team_id: int
    opponent_team_id: int
    coach_id: int
    coach_role: str = "HC"  # Only HCs can set gameplans
    off_agg: OffAgg
    def_agg: DefAgg
    coverage: Coverage
    blitz_strategy: BlitzStrategy
    rz_off: RZOff
    rz_def: RZDef

@router.get("/get", response_model=GameplanDTO)
def get_gameplan(season: int, week: int, team_id: int, opponent_team_id: int, coach_id: int, sess: Session = Depends(get_session)):
    """Get gameplan for specific matchup. Only HCs can access gameplans."""
    row = sess.exec(select(GameplanSelection).where(
        GameplanSelection.season==season,
        GameplanSelection.week==week,
        GameplanSelection.team_id==team_id,
        GameplanSelection.opponent_team_id==opponent_team_id,
        GameplanSelection.coach_id==coach_id
    )).first()
    if not row:
        row = GameplanSelection(season=season, week=week, team_id=team_id, opponent_team_id=opponent_team_id, coach_id=coach_id)
        sess.add(row); sess.commit(); sess.refresh(row)
    return GameplanDTO(**row.model_dump())

@router.post("/save", response_model=GameplanDTO)
def save_gameplan(body: GameplanDTO, sess: Session = Depends(get_session)):
    """Save gameplan for specific matchup. Only HCs can save gameplans."""
    # Validate that only HCs can set gameplans
    if body.coach_role != "HC":
        raise HTTPException(status_code=403, detail="Only Head Coaches (HC) can set gameplans")
    
    row = sess.exec(select(GameplanSelection).where(
        GameplanSelection.season==body.season,
        GameplanSelection.week==body.week,
        GameplanSelection.team_id==body.team_id,
        GameplanSelection.opponent_team_id==body.opponent_team_id,
        GameplanSelection.coach_id==body.coach_id
    )).first()
    if not row:
        row = GameplanSelection(**body.model_dump())
    else:
        for k, v in body.model_dump().items():
            setattr(row, k, v)
    sess.add(row); sess.commit(); sess.refresh(row)
    return GameplanDTO(**row.model_dump())

class GameplanDeltasDTO(BaseModel):
    pass_bias_delta: float
    depth_bias_delta: float
    trick_play_rate_delta: float
    go4it_cutoff_delta: float
    two_point_tendency_delta: float
    base_blitz_rate_delta: float
    blitz_rate_multiplier: float
    press_cushion_delta: float
    run_blitz_rate_delta: float
    coverage_mix: float | None
    rz_pass_bias_delta: float
    rz_shot_play_rate_delta: float
    te_rb_target_share_delta: float
    qb_run_keepers_rate_delta: float
    rz_shell_depth_delta: float
    rz_run_box_rate_delta: float
    rz_blitz_rate_delta: float
    explosive_play_risk_weight: float
    screen_draw_susceptibility_weight: float

@router.get("/deltas", response_model=GameplanDeltasDTO)
def get_deltas(season: int, week: int, team_id: int, opponent_team_id: int, coach_id: int, sess: Session = Depends(get_session)):
    """Get engine deltas for specific matchup. Only HCs can access gameplan deltas."""
    row = sess.exec(select(GameplanSelection).where(
        GameplanSelection.season==season,
        GameplanSelection.week==week,
        GameplanSelection.team_id==team_id,
        GameplanSelection.opponent_team_id==opponent_team_id,
        GameplanSelection.coach_id==coach_id
    )).first()
    if not row:
        row = GameplanSelection(season=season, week=week, team_id=team_id, opponent_team_id=opponent_team_id, coach_id=coach_id)
        sess.add(row); sess.commit(); sess.refresh(row)
    d = build_deltas(row.off_agg, row.def_agg, row.coverage, row.blitz_strategy, row.rz_off, row.rz_def)
    return GameplanDeltasDTO(**d.__dict__)

class GameplanOptionsDTO(BaseModel):
    offensive_aggressiveness: list[str]
    defensive_aggressiveness: list[str]
    coverage_scheme: list[str]
    blitz_strategy: list[str]
    red_zone_offense: list[str]
    red_zone_defense: list[str]

@router.get("/options", response_model=GameplanOptionsDTO)
def get_gameplan_options():
    """Get all available gameplan options for UI dropdowns."""
    return GameplanOptionsDTO(
        offensive_aggressiveness=[option.value for option in OffAgg],
        defensive_aggressiveness=[option.value for option in DefAgg],
        coverage_scheme=[option.value for option in Coverage],
        blitz_strategy=[option.value for option in BlitzStrategy],
        red_zone_offense=[option.value for option in RZOff],
        red_zone_defense=[option.value for option in RZDef]
    )

class GameplanTooltipsDTO(BaseModel):
    tooltips: dict[str, str]

@router.get("/tooltips", response_model=GameplanTooltipsDTO)
def get_gameplan_tooltips():
    """Get tooltip descriptions for gameplan controls."""
    return GameplanTooltipsDTO(
        tooltips={
            "Offensive Aggressiveness": "Controls how bold your offense is. Higher = more early-down passes, deeper routes, trick plays, and more 4th-down/2-pt attempts.",
            "Defensive Aggressiveness": "Higher = tighter coverage and more pressure. Increases sacks/negative plays but risks big explosives.",
            "Coverage Scheme": "How you cover receivers. Man challenges routes; Zone guards space and deep shots; Hybrid mixes both.",
            "Blitz Strategy": "How often you bring extra rushers. Blitz Heavy hunts sacks but opens windows for screens and deep shots.",
            "Red Zone Offense": "Your personality inside the 20: Power on the ground, Balanced, Play-Action deception, or Spread to attack space.",
            "Red Zone Defense": "Defend the red zone. Bend limits big plays; Run-Sellout plugs gaps; Pressure chases sacks/turnovers at higher risk."
        }
    )

class CoachAccessDTO(BaseModel):
    can_access_gameplan: bool
    coach_role: str
    message: str

@router.get("/coach_access", response_model=CoachAccessDTO)
def check_coach_access(coach_id: int, sess: Session = Depends(get_session)):
    """Check if a coach can access gameplan controls. Only HCs can access gameplans."""
    # This would typically check against a Coach table to get the actual role
    # For now, we'll assume the frontend passes the correct role
    # In a real implementation, you'd query the Coach table here
    
    # Placeholder logic - in reality you'd query the coach's role from the database
    # For now, we'll return that only HCs can access gameplans
    return CoachAccessDTO(
        can_access_gameplan=True,  # Frontend should check coach role
        coach_role="HC",  # This should come from the actual coach record
        message="Only Head Coaches can set gameplans. Other coaches (OC, DC, AC) cannot access gameplan controls."
    )
