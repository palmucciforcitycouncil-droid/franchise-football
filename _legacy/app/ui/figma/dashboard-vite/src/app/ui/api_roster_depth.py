from __future__ import annotations
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db import get_session
from app.models.roster import DepthChart
from app.services.depth_chart_service import (
    list_depth_chart, set_depth_chart, auto_fill, lineup_for_game, 
    ORDERED_SLOTS, ELIGIBILITY, get_depth_chart_by_slot, validate_depth_chart,
    get_available_players_for_slot, update_single_slot, clear_depth_chart,
    get_depth_chart_summary, get_injured_players_in_lineup, get_depth_chart_with_player_info
)

router = APIRouter(prefix="/api/v1/roster", tags=["roster-depth"])

class DepthRowDTO(BaseModel):
    slot: str
    order_index: int
    player_id: int | None

@router.get("/depth_chart", response_model=List[DepthRowDTO])
def get_depth_chart(team_id: int, sess: Session = Depends(get_session)):
    """Get depth chart for a team."""
    try:
        rows = list_depth_chart(sess, team_id)
        return [DepthRowDTO(slot=r.slot, order_index=r.order_index, player_id=r.player_id) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get depth chart: {str(e)}")

class SetDepthReq(BaseModel):
    team_id: int
    items: List[DepthRowDTO]

@router.post("/depth_chart")
def post_depth_chart(body: SetDepthReq, sess: Session = Depends(get_session)):
    """Set depth chart for a team."""
    try:
        items = [(it.slot, it.order_index, it.player_id) for it in body.items if it.slot in ORDERED_SLOTS]
        set_depth_chart(sess, body.team_id, items)
        return {"ok": True, "team_id": body.team_id, "slots_updated": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set depth chart: {str(e)}")

@router.post("/auto_fill")
def post_auto_fill(team_id: int, season: int, week: int, game_id: int, opponent_id: int, sess: Session = Depends(get_session)):
    """Auto-fill depth chart for a team."""
    try:
        auto_fill(sess, team_id, season, week, game_id, opponent_id)
        return {"ok": True, "team_id": team_id, "season": season, "week": week}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to auto-fill depth chart: {str(e)}")

class LineupDTO(BaseModel):
    slots: Dict[str, List[int]]

@router.get("/lineup_for_game", response_model=LineupDTO)
def get_lineup(team_id: int, season: int, week: int, game_id: int, opponent_id: int, sess: Session = Depends(get_session)):
    """Get lineup for a game."""
    try:
        slots = lineup_for_game(sess, team_id, season, week, game_id, opponent_id)
        return LineupDTO(slots=slots)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get lineup: {str(e)}")

@router.get("/eligibility")
def get_eligibility():
    """Get position eligibility rules."""
    return {"slots": ORDERED_SLOTS, "eligibility": ELIGIBILITY}

@router.get("/depth_chart/by_slot")
def get_depth_chart_by_slot_endpoint(team_id: int, sess: Session = Depends(get_session)):
    """Get depth chart organized by slot."""
    try:
        return get_depth_chart_by_slot(sess, team_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get depth chart by slot: {str(e)}")

@router.get("/depth_chart/validate")
def validate_depth_chart_endpoint(team_id: int, sess: Session = Depends(get_session)):
    """Validate depth chart for issues."""
    try:
        return validate_depth_chart(sess, team_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate depth chart: {str(e)}")

@router.get("/depth_chart/available_players")
def get_available_players(team_id: int, slot: str, sess: Session = Depends(get_session)):
    """Get available players for a specific slot."""
    try:
        players = get_available_players_for_slot(sess, team_id, slot)
        return [
            {
                "player_id": p.player_id,
                "name": getattr(p, "name", f"Player {p.player_id}"),
                "pos": getattr(p, "pos", ""),
                "overall": getattr(p, "overall", 0),
                "age": getattr(p, "age", 0)
            }
            for p in players
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available players: {str(e)}")

class UpdateSlotReq(BaseModel):
    team_id: int
    slot: str
    order_index: int
    player_id: int | None

@router.post("/depth_chart/update_slot")
def update_single_slot_endpoint(body: UpdateSlotReq, sess: Session = Depends(get_session)):
    """Update a single depth chart slot."""
    try:
        success = update_single_slot(sess, body.team_id, body.slot, body.order_index, body.player_id)
        return {"ok": success, "team_id": body.team_id, "slot": body.slot}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update slot: {str(e)}")

@router.post("/depth_chart/clear")
def clear_depth_chart_endpoint(team_id: int, sess: Session = Depends(get_session)):
    """Clear entire depth chart for a team."""
    try:
        clear_depth_chart(sess, team_id)
        return {"ok": True, "team_id": team_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear depth chart: {str(e)}")

@router.get("/depth_chart/summary")
def get_depth_chart_summary_endpoint(team_id: int, sess: Session = Depends(get_session)):
    """Get depth chart summary statistics."""
    try:
        return get_depth_chart_summary(sess, team_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get depth chart summary: {str(e)}")

@router.get("/depth_chart/injured_players")
def get_injured_players_endpoint(team_id: int, season: int, week: int, game_id: int, opponent_id: int, sess: Session = Depends(get_session)):
    """Get list of injured players currently in the depth chart."""
    try:
        return get_injured_players_in_lineup(sess, team_id, season, week, game_id, opponent_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get injured players: {str(e)}")

@router.get("/depth_chart/with_player_info")
def get_depth_chart_with_player_info_endpoint(team_id: int, sess: Session = Depends(get_session)):
    """Get depth chart with player information."""
    try:
        return get_depth_chart_with_player_info(sess, team_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get depth chart with player info: {str(e)}")

@router.get("/depth_chart/offense")
def get_offense_lineup(team_id: int, sess: Session = Depends(get_session)):
    """Get offensive lineup."""
    try:
        rows = list_depth_chart(sess, team_id)
        offense_slots = ["QB", "RB", "WR1", "WR2", "WR3", "TE", "LT", "LG", "C", "RG", "RT"]
        
        offense = {}
        for slot in offense_slots:
            slot_rows = [r for r in rows if r.slot == slot]
            offense[slot] = [r.player_id for r in slot_rows if r.player_id]
        
        return offense
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get offense lineup: {str(e)}")

@router.get("/depth_chart/defense")
def get_defense_lineup(team_id: int, sess: Session = Depends(get_session)):
    """Get defensive lineup."""
    try:
        rows = list_depth_chart(sess, team_id)
        defense_slots = ["EDGE1", "EDGE2", "DL1", "DL2", "LB1", "LB2", "CB1", "CB2", "S1", "S2"]
        
        defense = {}
        for slot in defense_slots:
            slot_rows = [r for r in rows if r.slot == slot]
            defense[slot] = [r.player_id for r in slot_rows if r.player_id]
        
        return defense
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get defense lineup: {str(e)}")

@router.get("/depth_chart/special_teams")
def get_special_teams_lineup(team_id: int, sess: Session = Depends(get_session)):
    """Get special teams lineup."""
    try:
        rows = list_depth_chart(sess, team_id)
        special_slots = ["K", "P", "LS", "KR", "PR"]
        
        special = {}
        for slot in special_slots:
            slot_rows = [r for r in rows if r.slot == slot]
            special[slot] = [r.player_id for r in slot_rows if r.player_id]
        
        return special
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get special teams lineup: {str(e)}")

@router.get("/depth_chart/starters")
def get_starters(team_id: int, sess: Session = Depends(get_session)):
    """Get starting lineup (order_index = 0)."""
    try:
        rows = list_depth_chart(sess, team_id)
        starters = {}
        
        for row in rows:
            if row.order_index == 0:
                starters[row.slot] = row.player_id
        
        return starters
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get starters: {str(e)}")

@router.get("/depth_chart/backups")
def get_backups(team_id: int, sess: Session = Depends(get_session)):
    """Get backup players (order_index > 0)."""
    try:
        rows = list_depth_chart(sess, team_id)
        backups = {}
        
        for row in rows:
            if row.order_index > 0:
                if row.slot not in backups:
                    backups[row.slot] = []
                backups[row.slot].append(row.player_id)
        
        return backups
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backups: {str(e)}")

@router.get("/depth_chart/position/{position}")
def get_position_depth(team_id: int, position: str, sess: Session = Depends(get_session)):
    """Get depth chart for a specific position."""
    try:
        rows = list_depth_chart(sess, team_id)
        position_rows = [r for r in rows if r.slot.startswith(position)]
        
        result = []
        for row in position_rows:
            result.append({
                "slot": row.slot,
                "order_index": row.order_index,
                "player_id": row.player_id
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get position depth: {str(e)}")

@router.get("/depth_chart/empty_slots")
def get_empty_slots(team_id: int, sess: Session = Depends(get_session)):
    """Get empty slots in depth chart."""
    try:
        rows = list_depth_chart(sess, team_id)
        empty_slots = []
        
        for row in rows:
            if row.player_id is None:
                empty_slots.append({
                    "slot": row.slot,
                    "order_index": row.order_index
                })
        
        return empty_slots
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get empty slots: {str(e)}")

@router.get("/depth_chart/filled_slots")
def get_filled_slots(team_id: int, sess: Session = Depends(get_session)):
    """Get filled slots in depth chart."""
    try:
        rows = list_depth_chart(sess, team_id)
        filled_slots = []
        
        for row in rows:
            if row.player_id is not None:
                filled_slots.append({
                    "slot": row.slot,
                    "order_index": row.order_index,
                    "player_id": row.player_id
                })
        
        return filled_slots
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get filled slots: {str(e)}")

