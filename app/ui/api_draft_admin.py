from __future__ import annotations
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session
from app.core.db import get_session
from app.services.draft_admin import draft_status, pause, resume, list_owned_picks, add_pick_to_block, remove_pick_from_block, transfer_pick_ownership
from app.services.team_needs_service import team_needs, league_starter_averages, team_starter_averages

router = APIRouter(prefix="/api/v1/draft/admin", tags=["draft-admin"])

@router.get("/status")
def api_status(season: int, sess: Session = Depends(get_session)):
    return draft_status(sess, season)

@router.post("/pause")
def api_pause(season: int, sess: Session = Depends(get_session)):
    return pause(sess, season)

@router.post("/resume")
def api_resume(season: int, sess: Session = Depends(get_session)):
    return resume(sess, season)

# Picks: list & trade block
class PickDTO(BaseModel):
    season: int
    round: int
    slot: int
    owning_team_id: int
    original_team_id: int

@router.get("/picks", response_model=List[PickDTO])
def api_picks(season: int, team_id: int, sess: Session = Depends(get_session)):
    rows = list_owned_picks(sess, season, team_id)
    return [PickDTO(season=r.season, round=r.round, slot=r.slot, owning_team_id=r.owning_team_id, original_team_id=r.original_team_id) for r in rows]

class BlockReq(BaseModel):
    season: int
    team_id: int
    round: int
    slot: int
    note: Optional[str] = ""

@router.post("/picks/block")
def api_block_add(body: BlockReq, sess: Session = Depends(get_session)):
    return add_pick_to_block(sess, body.season, body.team_id, body.round, body.slot, body.note or "")

@router.post("/picks/unblock")
def api_block_remove(body: BlockReq, sess: Session = Depends(get_session)):
    return remove_pick_from_block(sess, body.season, body.team_id, body.round, body.slot)

# Helper for Trade Engine to finalize pick transfer
class TransferReq(BaseModel):
    season: int
    round: int
    slot: int
    to_team_id: int

@router.post("/picks/transfer")
def api_transfer(body: TransferReq, sess: Session = Depends(get_session)):
    return transfer_pick_ownership(sess, body.season, body.round, body.slot, body.to_team_id)

# ---- Team needs
@router.get("/needs")
def api_team_needs(season: int, team_id: int, sess: Session = Depends(get_session)):
    return team_needs(sess, season, team_id)

@router.get("/needs/league_avg")
def api_league_avgs(season: int, sess: Session = Depends(get_session)):
    return league_starter_averages(sess, season)

@router.get("/needs/team_avg")
def api_team_avgs(season: int, team_id: int, sess: Session = Depends(get_session)):
    return team_starter_averages(sess, season, team_id)
