from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_session
from app.models.injury import Injury, InjuryStatus, InjuryType
from app.services.injury_service import (
    get_team_injuries, get_injury_stats, weekly_heal,
    compute_player_injury_odds, simulate_injury_odds
)
from app.engine.injury_hooks import (
    get_player_availability_status, get_team_availability,
    apply_injury_penalties_to_rating, get_depth_chart_adjustments
)

router = APIRouter(prefix="/api/v1/injuries", tags=["injuries"])

class InjuryDTO(BaseModel):
    injury_id: int
    season: int
    week: int
    player_id: int
    team_id: int
    injury_type: str
    severity: int
    weeks_out_total: int
    weeks_out_remaining: int
    placed_on_ir: bool
    status: InjuryStatus
    rtp_penalty_overall: float
    rtp_penalty_pos: float
    created_at: str
    resolved: bool

@router.get("/team", response_model=List[InjuryDTO])
def team_injuries(team_id: int, season: Optional[int] = None, resolved_only: bool = False, sess: Session = Depends(get_session)):
    """Get all injuries for a team."""
    try:
        injuries = get_team_injuries(sess, team_id, season, resolved_only)
        return [
            InjuryDTO(
                injury_id=r.injury_id, season=r.season, week=r.week, player_id=r.player_id, team_id=r.team_id,
                injury_type=r.injury_type.value, severity=r.severity, weeks_out_total=r.weeks_out_total,
                weeks_out_remaining=r.weeks_out_remaining, placed_on_ir=r.placed_on_ir, status=r.status,
                rtp_penalty_overall=r.rtp_penalty_overall, rtp_penalty_pos=r.rtp_penalty_pos,
                created_at=r.created_at.isoformat(), resolved=r.resolved
            ) for r in injuries
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team injuries: {str(e)}")

class IRReq(BaseModel):
    injury_id: int
    place_on_ir: bool

@router.post("/ir")
def place_on_ir(body: IRReq, sess: Session = Depends(get_session)):
    """Place a player on IR or remove from IR."""
    try:
        r = sess.get(Injury, body.injury_id)
        if not r:
            raise HTTPException(status_code=404, detail="Injury not found")
        
        r.placed_on_ir = bool(body.place_on_ir)
        sess.add(r)
        sess.commit()
        return {"ok": True, "message": f"Player {'placed on' if body.place_on_ir else 'removed from'} IR"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update IR status: {str(e)}")

class HealReq(BaseModel):
    season: int
    week: int
    team_id: Optional[int] = None

@router.post("/advance_week")
def advance_week(body: HealReq, sess: Session = Depends(get_session)):
    """Advance week for injury healing."""
    try:
        weekly_heal(sess, body.season, body.week, team_id=body.team_id)
        return {"ok": True, "message": "Week advanced, injuries healed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to advance week: {str(e)}")

class PlayerAvailabilityRes(BaseModel):
    player_id: int
    is_available: bool
    injury_status: str
    overall_penalty: float
    positional_penalty: float
    total_penalty: float

@router.get("/player/{player_id}/availability", response_model=PlayerAvailabilityRes)
def get_player_availability(player_id: int, sess: Session = Depends(get_session)):
    """Get player availability status."""
    try:
        status = get_player_availability_status(sess, player_id)
        return PlayerAvailabilityRes(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get player availability: {str(e)}")

class TeamAvailabilityRes(BaseModel):
    team_id: int
    season: int
    active_injuries: int
    ir_players: int
    stats: dict

@router.get("/team/{team_id}/availability", response_model=TeamAvailabilityRes)
def get_team_availability_status(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get team availability status."""
    try:
        availability = get_team_availability(sess, team_id, season)
        return TeamAvailabilityRes(**availability)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team availability: {str(e)}")

class DepthChartAdjustmentsRes(BaseModel):
    injured_players: List[int]
    ir_players: List[int]
    questionable_players: List[int]
    probable_players: List[int]

@router.get("/team/{team_id}/depth_chart_adjustments", response_model=DepthChartAdjustmentsRes)
def get_depth_chart_adjustments(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get depth chart adjustments based on injuries."""
    try:
        adjustments = get_depth_chart_adjustments(sess, team_id, season)
        return DepthChartAdjustmentsRes(**adjustments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get depth chart adjustments: {str(e)}")

class RatingPenaltyReq(BaseModel):
    player_id: int
    base_overall: int
    base_positional: int

class RatingPenaltyRes(BaseModel):
    player_id: int
    adjusted_overall: int
    adjusted_positional: int
    overall_penalty: float
    positional_penalty: float

@router.post("/apply_penalties", response_model=RatingPenaltyRes)
def apply_rating_penalties(body: RatingPenaltyReq, sess: Session = Depends(get_session)):
    """Apply injury penalties to player ratings."""
    try:
        adjusted_overall, adjusted_positional = apply_injury_penalties_to_rating(
            sess, body.player_id, body.base_overall, body.base_positional
        )
        
        from app.engine.injury_hooks import rtp_overall_penalty, rtp_positional_penalty
        overall_penalty = rtp_overall_penalty(sess, body.player_id)
        positional_penalty = rtp_positional_penalty(sess, body.player_id)
        
        return RatingPenaltyRes(
            player_id=body.player_id,
            adjusted_overall=adjusted_overall,
            adjusted_positional=adjusted_positional,
            overall_penalty=overall_penalty,
            positional_penalty=positional_penalty
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply rating penalties: {str(e)}")

class InjuryOddsReq(BaseModel):
    season: int
    week: int
    game_id: int
    team_id: int
    opponent_id: int
    pos: str
    base_minutes: float = 60.0

class InjuryOddsRes(BaseModel):
    base_per_game: float
    focus_injury_mult: float
    gameplan_aggr_bump: float
    fatigue_bump: float
    effective_rate: float

@router.post("/odds", response_model=InjuryOddsRes)
def get_injury_odds(body: InjuryOddsReq, sess: Session = Depends(get_session)):
    """Get injury odds for a player."""
    try:
        ctx = compute_player_injury_odds(
            sess, body.season, body.week, body.game_id, 
            body.team_id, body.opponent_id, body.pos, body.base_minutes
        )
        
        effective_rate = ctx.base_per_game * ctx.focus_injury_mult + ctx.gameplan_aggr_bump + ctx.fatigue_bump
        
        return InjuryOddsRes(
            base_per_game=ctx.base_per_game,
            focus_injury_mult=ctx.focus_injury_mult,
            gameplan_aggr_bump=ctx.gameplan_aggr_bump,
            fatigue_bump=ctx.fatigue_bump,
            effective_rate=effective_rate
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get injury odds: {str(e)}")

class InjurySimulationReq(BaseModel):
    season: int
    week: int
    game_id: int
    team_id: int
    opponent_id: int
    pos: str
    simulations: int = 1000

class InjurySimulationRes(BaseModel):
    simulated_rate: float
    calculated_rate: float
    base_rate: float
    focus_multiplier: float
    aggression_bump: float
    fatigue_bump: float

@router.post("/simulate", response_model=InjurySimulationRes)
def simulate_injury_odds(body: InjurySimulationReq, sess: Session = Depends(get_session)):
    """Simulate injury odds for analysis."""
    try:
        results = simulate_injury_odds(
            sess, body.season, body.week, body.game_id,
            body.team_id, body.opponent_id, body.pos, body.simulations
        )
        return InjurySimulationRes(**results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to simulate injury odds: {str(e)}")

class InjuryStatsRes(BaseModel):
    total_injuries: int
    active_injuries: int
    ir_players: int
    by_status: dict
    by_type: dict
    avg_severity: float
    total_weeks_lost: int

@router.get("/team/{team_id}/stats", response_model=InjuryStatsRes)
def get_team_injury_stats(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get injury statistics for a team."""
    try:
        stats = get_injury_stats(sess, team_id, season)
        return InjuryStatsRes(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get injury stats: {str(e)}")

class InjuryTypeStatsRes(BaseModel):
    injury_type: str
    frequency: float
    avg_weeks: float
    avg_severity: float
    rtp_overall: float
    rtp_positional: float

@router.get("/types/stats", response_model=List[InjuryTypeStatsRes])
def get_injury_type_stats(sess: Session = Depends(get_session)):
    """Get statistics for different injury types."""
    try:
        from app.services.injury_service import TYPE_PROFILE, RTP_MULTIPLIER
        
        stats = []
        for injury_type, (frequency, (min_weeks, max_weeks)) in TYPE_PROFILE.items():
            rtp_overall, rtp_positional = RTP_MULTIPLIER.get(injury_type, (0.05, 0.08))
            
            stats.append(InjuryTypeStatsRes(
                injury_type=injury_type.value,
                frequency=frequency,
                avg_weeks=(min_weeks + max_weeks) / 2,
                avg_severity=5.0,  # Rough estimate
                rtp_overall=rtp_overall,
                rtp_positional=rtp_positional
            ))
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get injury type stats: {str(e)}")

class PositionInjuryRatesRes(BaseModel):
    position: str
    base_rate: float
    description: str

@router.get("/positions/rates", response_model=List[PositionInjuryRatesRes])
def get_position_injury_rates(sess: Session = Depends(get_session)):
    """Get injury rates by position."""
    try:
        from app.services.injury_service import BASE_INJURY_PER_GAME
        
        rates = []
        position_descriptions = {
            "QB": "Quarterback - Low injury risk",
            "RB": "Running Back - High injury risk",
            "WR": "Wide Receiver - Medium injury risk",
            "TE": "Tight End - Medium injury risk",
            "OL": "Offensive Line - Medium injury risk",
            "DL": "Defensive Line - Medium injury risk",
            "EDGE": "Edge Rusher - High injury risk",
            "LB": "Linebacker - Medium injury risk",
            "CB": "Cornerback - Medium injury risk",
            "S": "Safety - Medium injury risk",
            "K": "Kicker - Low injury risk",
            "P": "Punter - Low injury risk",
            "LS": "Long Snapper - Low injury risk"
        }
        
        for position, rate in BASE_INJURY_PER_GAME.items():
            rates.append(PositionInjuryRatesRes(
                position=position,
                base_rate=rate,
                description=position_descriptions.get(position, "Unknown position")
            ))
        
        return rates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get position injury rates: {str(e)}")

