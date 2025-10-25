from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db import get_session
from app.services.gameplan_presets import (
    apply_preset_balanced, apply_preset_air_it_out, apply_preset_ground_pound,
    apply_preset_heat_qb, apply_preset_bend_rz, get_available_presets, apply_preset
)
from app.services.gameplan_cpu_ai import (
    choose_cpu_gameplan, choose_cpu_gameplan_for_week, choose_cpu_gameplan_for_team,
    get_cpu_gameplan_reasoning
)
from app.models.gameplan import GameplanSelection

router = APIRouter(prefix="/api/v1/gameplan/tools", tags=["gameplan-tools"])

class PresetReq(BaseModel):
    preset: str
    season: int
    week: int
    team_id: int
    opponent_team_id: int

PRESET_FUN = {
    "balanced": apply_preset_balanced,
    "air_it_out": apply_preset_air_it_out,
    "ground_pound": apply_preset_ground_pound,
    "heat_qb": apply_preset_heat_qb,
    "bend_rz": apply_preset_bend_rz,
}

@router.post("/apply_preset")
def apply_preset_endpoint(body: PresetReq, sess: Session = Depends(get_session)):
    """Apply a preset gameplan to a specific matchup."""
    f = PRESET_FUN.get(body.preset)
    if not f:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {body.preset}")
    
    try:
        row = f(sess, body.season, body.week, body.team_id, body.opponent_team_id)
        return {"ok": True, "selection": row.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply preset: {str(e)}")

@router.get("/presets")
def get_presets():
    """Get list of available presets."""
    return {"presets": get_available_presets()}

class PresetInfo(BaseModel):
    name: str
    description: str
    offensive_aggressiveness: str
    defensive_aggressiveness: str
    coverage_scheme: str
    blitz_strategy: str
    red_zone_offense: str
    red_zone_defense: str

@router.get("/presets/info", response_model=list[PresetInfo])
def get_preset_info():
    """Get detailed information about all presets."""
    return [
        PresetInfo(
            name="balanced",
            description="Neutral approach across all areas - safe default",
            offensive_aggressiveness="Balanced",
            defensive_aggressiveness="Balanced",
            coverage_scheme="Hybrid",
            blitz_strategy="Standard",
            red_zone_offense="Balanced",
            red_zone_defense="Balanced"
        ),
        PresetInfo(
            name="air_it_out",
            description="Aggressive passing offense with conservative defense",
            offensive_aggressiveness="Very Aggressive",
            defensive_aggressiveness="Conservative",
            coverage_scheme="Zone-Heavy",
            blitz_strategy="Selective",
            red_zone_offense="Spread/Shot",
            red_zone_defense="Bend-Don't-Break"
        ),
        PresetInfo(
            name="ground_pound",
            description="Conservative run-heavy offense with run-stopping defense",
            offensive_aggressiveness="Very Conservative",
            defensive_aggressiveness="Balanced",
            coverage_scheme="Hybrid",
            blitz_strategy="Standard",
            red_zone_offense="Power Run",
            red_zone_defense="Run-Sellout"
        ),
        PresetInfo(
            name="heat_qb",
            description="Balanced offense with aggressive pass rush defense",
            offensive_aggressiveness="Balanced",
            defensive_aggressiveness="Aggressive",
            coverage_scheme="Hybrid",
            blitz_strategy="Blitz Heavy",
            red_zone_offense="Balanced",
            red_zone_defense="Pressure QB"
        ),
        PresetInfo(
            name="bend_rz",
            description="Conservative approach with bend-don't-break red zone defense",
            offensive_aggressiveness="Conservative",
            defensive_aggressiveness="Conservative",
            coverage_scheme="Zone-Heavy",
            blitz_strategy="Selective",
            red_zone_offense="Play-Action Heavy",
            red_zone_defense="Bend-Don't-Break"
        )
    ]

class CpuPickReq(BaseModel):
    season: int
    week: int
    team_id: int
    opponent_team_id: int
    seed: Optional[int] = None

@router.post("/cpu_pick")
def cpu_pick(body: CpuPickReq, sess: Session = Depends(get_session)):
    """Have CPU AI choose a gameplan for a specific matchup."""
    try:
        row = choose_cpu_gameplan(sess, body.season, body.week, body.team_id, body.opponent_team_id, seed=body.seed)
        return {"ok": True, "selection": row.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CPU gameplan: {str(e)}")

@router.get("/cpu_pick/reasoning")
def cpu_pick_reasoning(season: int, week: int, team_id: int, opponent_team_id: int, sess: Session = Depends(get_session)):
    """Get the reasoning behind a CPU gameplan choice."""
    try:
        reasoning = get_cpu_gameplan_reasoning(sess, season, week, team_id, opponent_team_id)
        return {"ok": True, "reasoning": reasoning}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reasoning: {str(e)}")

class CpuWeekReq(BaseModel):
    season: int
    week: int
    seed: Optional[int] = None

@router.post("/cpu_pick_week")
def cpu_pick_week(body: CpuWeekReq, sess: Session = Depends(get_session)):
    """Have CPU AI choose gameplans for all matchups in a week."""
    try:
        choose_cpu_gameplan_for_week(sess, body.season, body.week, seed=body.seed)
        return {"ok": True, "message": f"CPU gameplans generated for season {body.season}, week {body.week}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CPU gameplans for week: {str(e)}")

class CpuTeamReq(BaseModel):
    season: int
    week: int
    team_id: int
    opponents: list[int]
    seed: Optional[int] = None

@router.post("/cpu_pick_team")
def cpu_pick_team(body: CpuTeamReq, sess: Session = Depends(get_session)):
    """Have CPU AI choose gameplans for a specific team against multiple opponents."""
    try:
        choose_cpu_gameplan_for_team(sess, body.season, body.week, body.team_id, body.opponents, seed=body.seed)
        return {"ok": True, "message": f"CPU gameplans generated for team {body.team_id} vs {len(body.opponents)} opponents"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CPU gameplans for team: {str(e)}")

class BatchPresetReq(BaseModel):
    preset: str
    season: int
    week: int
    matchups: list[dict]  # [{"team_id": 1, "opponent_team_id": 2}, ...]

@router.post("/apply_preset_batch")
def apply_preset_batch(body: BatchPresetReq, sess: Session = Depends(get_session)):
    """Apply a preset to multiple matchups at once."""
    f = PRESET_FUN.get(body.preset)
    if not f:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {body.preset}")
    
    try:
        results = []
        for matchup in body.matchups:
            row = f(sess, body.season, body.week, matchup["team_id"], matchup["opponent_team_id"])
            results.append(row.model_dump())
        return {"ok": True, "selections": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply preset batch: {str(e)}")

class GameplanStatsReq(BaseModel):
    season: int
    week: int
    team_id: Optional[int] = None

@router.get("/stats")
def get_gameplan_stats(season: int, week: int, team_id: Optional[int] = None, sess: Session = Depends(get_session)):
    """Get statistics about gameplan usage for a season/week."""
    from sqlmodel import select
    from collections import Counter
    
    query = select(GameplanSelection).where(
        GameplanSelection.season == season,
        GameplanSelection.week == week
    )
    if team_id is not None:
        query = query.where(GameplanSelection.team_id == team_id)
    
    selections = list(sess.exec(query))
    
    if not selections:
        return {"ok": True, "stats": {"total_selections": 0}}
    
    # Count usage of each option
    stats = {
        "total_selections": len(selections),
        "offensive_aggressiveness": dict(Counter(s.off_agg.value for s in selections)),
        "defensive_aggressiveness": dict(Counter(s.def_agg.value for s in selections)),
        "coverage_scheme": dict(Counter(s.coverage.value for s in selections)),
        "blitz_strategy": dict(Counter(s.blitz_strategy.value for s in selections)),
        "red_zone_offense": dict(Counter(s.rz_off.value for s in selections)),
        "red_zone_defense": dict(Counter(s.rz_def.value for s in selections)),
    }
    
    return {"ok": True, "stats": stats}

