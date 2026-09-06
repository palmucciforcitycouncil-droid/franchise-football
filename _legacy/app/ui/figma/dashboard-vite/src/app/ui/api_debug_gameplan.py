from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlmodel import Session, select
from app.db import get_session
from app.models.gameplan_trace import GameplanTrace

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])

class TraceDTO(BaseModel):
    team_id: int
    opponent_team_id: int
    season: int
    week: int
    created_at: str
    hc: str
    focus: str
    user: str
    final_cfg: str

class TraceSummaryDTO(BaseModel):
    game_id: int
    traces: List[TraceDTO]

@router.get("/gameplan_trace", response_model=List[TraceDTO])
def gameplan_trace(game_id: int, sess: Session = Depends(get_session)):
    """
    Get gameplan traces for a specific game.
    Returns the composition details for both teams.
    """
    rows = list(sess.exec(select(GameplanTrace).where(GameplanTrace.game_id==game_id)))
    if not rows:
        raise HTTPException(status_code=404, detail=f"No gameplan traces found for game_id {game_id}")
    
    return [
        TraceDTO(
            team_id=r.team_id, 
            opponent_team_id=r.opponent_team_id,
            season=r.season,
            week=r.week,
            created_at=r.created_at.isoformat(),
            hc=r.hc, 
            focus=r.focus, 
            user=r.user, 
            final_cfg=r.final_cfg
        ) 
        for r in rows
    ]

@router.get("/gameplan_trace/summary", response_model=TraceSummaryDTO)
def gameplan_trace_summary(game_id: int, sess: Session = Depends(get_session)):
    """
    Get a summary of gameplan traces for a specific game.
    """
    traces = gameplan_trace(game_id, sess)
    return TraceSummaryDTO(game_id=game_id, traces=traces)

@router.get("/gameplan_trace/team", response_model=List[TraceDTO])
def gameplan_trace_by_team(team_id: int, season: Optional[int] = None, week: Optional[int] = None, sess: Session = Depends(get_session)):
    """
    Get gameplan traces for a specific team, optionally filtered by season/week.
    """
    query = select(GameplanTrace).where(GameplanTrace.team_id==team_id)
    
    if season is not None:
        query = query.where(GameplanTrace.season==season)
    if week is not None:
        query = query.where(GameplanTrace.week==week)
    
    rows = list(sess.exec(query))
    if not rows:
        raise HTTPException(status_code=404, detail=f"No gameplan traces found for team_id {team_id}")
    
    return [
        TraceDTO(
            team_id=r.team_id, 
            opponent_team_id=r.opponent_team_id,
            season=r.season,
            week=r.week,
            created_at=r.created_at.isoformat(),
            hc=r.hc, 
            focus=r.focus, 
            user=r.user, 
            final_cfg=r.final_cfg
        ) 
        for r in rows
    ]

@router.get("/gameplan_trace/season", response_model=List[TraceDTO])
def gameplan_trace_by_season(season: int, week: Optional[int] = None, sess: Session = Depends(get_session)):
    """
    Get gameplan traces for a specific season, optionally filtered by week.
    """
    query = select(GameplanTrace).where(GameplanTrace.season==season)
    
    if week is not None:
        query = query.where(GameplanTrace.week==week)
    
    rows = list(sess.exec(query))
    if not rows:
        raise HTTPException(status_code=404, detail=f"No gameplan traces found for season {season}")
    
    return [
        TraceDTO(
            team_id=r.team_id, 
            opponent_team_id=r.opponent_team_id,
            season=r.season,
            week=r.week,
            created_at=r.created_at.isoformat(),
            hc=r.hc, 
            focus=r.focus, 
            user=r.user, 
            final_cfg=r.final_cfg
        ) 
        for r in rows
    ]

class GameplanCompositionDTO(BaseModel):
    """Human-readable breakdown of gameplan composition."""
    team_id: int
    opponent_team_id: int
    season: int
    week: int
    
    # HC Influence
    hc_pass_bias: float
    hc_offensive_aggression: float
    hc_defensive_aggression: float
    hc_coverage_mix: float
    
    # User Gameplan
    user_offensive_aggressiveness: str
    user_defensive_aggressiveness: str
    user_coverage_scheme: str
    user_blitz_strategy: str
    user_red_zone_offense: str
    user_red_zone_defense: str
    
    # Coach Focus Effects
    focus_run_pass_tendency: float
    focus_offensive_aggression: float
    focus_defensive_aggression: float
    focus_fourth_down: float
    focus_two_point: float
    
    # Final Configuration
    final_pass_bias: float
    final_blitz_rate: float
    final_coverage_mix: float
    final_rz_pass_bias: float

@router.get("/gameplan_trace/composition", response_model=List[GameplanCompositionDTO])
def gameplan_trace_composition(game_id: int, sess: Session = Depends(get_session)):
    """
    Get a human-readable breakdown of gameplan composition for a game.
    """
    import json
    
    traces = gameplan_trace(game_id, sess)
    compositions = []
    
    for trace in traces:
        try:
            hc_data = json.loads(trace.hc)
            focus_data = json.loads(trace.focus)
            user_data = json.loads(trace.user)
            final_data = json.loads(trace.final_cfg)
            
            composition = GameplanCompositionDTO(
                team_id=trace.team_id,
                opponent_team_id=trace.opponent_team_id,
                season=trace.season,
                week=trace.week,
                
                # HC Influence
                hc_pass_bias=hc_data.get("run_pass_tendency", 0.0),
                hc_offensive_aggression=hc_data.get("offensive_aggression", 0.5),
                hc_defensive_aggression=hc_data.get("defensive_aggression", 0.5),
                hc_coverage_mix=hc_data.get("coverage_mix", 0.5),
                
                # User Gameplan (would need to parse from user_data)
                user_offensive_aggressiveness="Unknown",  # Would need to store this separately
                user_defensive_aggressiveness="Unknown",
                user_coverage_scheme="Unknown",
                user_blitz_strategy="Unknown",
                user_red_zone_offense="Unknown",
                user_red_zone_defense="Unknown",
                
                # Coach Focus Effects
                focus_run_pass_tendency=focus_data.get("run_pass_tendency_delta", 0.0),
                focus_offensive_aggression=focus_data.get("offensive_aggression_delta", 0.0),
                focus_defensive_aggression=focus_data.get("defensive_aggression_delta", 0.0),
                focus_fourth_down=focus_data.get("fourth_down_delta", 0.0),
                focus_two_point=focus_data.get("two_point_delta", 0.0),
                
                # Final Configuration
                final_pass_bias=final_data.get("pass_bias", 0.0),
                final_blitz_rate=final_data.get("blitz_rate", 0.12),
                final_coverage_mix=final_data.get("coverage_mix", 0.5),
                final_rz_pass_bias=final_data.get("rz_off_pass_bias", 0.0),
            )
            compositions.append(composition)
        except (json.JSONDecodeError, KeyError) as e:
            # Skip malformed traces
            continue
    
    return compositions

