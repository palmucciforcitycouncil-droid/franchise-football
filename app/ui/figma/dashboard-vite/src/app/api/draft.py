from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.core.db import get_session
from app.services.draft_service import (
    get_draft_results, get_prospects, get_draft_board, add_to_board,
    make_pick, sim_until_next_user_pick, advance_clock
)
from app.api.dto_draft import (
    ProspectDTO, DraftBoardDTO, DraftResultsDTO, ActionResult
)

router = APIRouter(prefix="/api/draft", tags=["draft"])

class AddToBoardRequest(BaseModel):
    prospect_id: int

class MakePickRequest(BaseModel):
    prospect_id: int

@router.get("/results", response_model=DraftResultsDTO)
def get_draft_results_endpoint(
    round: int,
    sess: Session = Depends(get_session)
):
    """Get draft results for a specific round."""
    if round < 1 or round > 7:
        raise HTTPException(status_code=400, detail="Round must be between 1 and 7")
    
    # Advance clock before returning results
    advance_clock(sess)
    
    return get_draft_results(sess, round)

@router.get("/prospects", response_model=List[ProspectDTO])
def get_prospects_endpoint(
    top: bool = False,
    q: Optional[str] = None,
    limit: int = 50,
    sess: Session = Depends(get_session)
):
    """Get prospects with optional search and filtering."""
    if limit > 100:
        limit = 100  # Cap limit
    
    return get_prospects(sess, q=q, top_only=top, limit=limit)

@router.get("/board", response_model=DraftBoardDTO)
def get_draft_board_endpoint(sess: Session = Depends(get_session)):
    """Get user's draft board."""
    # For MVP, assume user team ID is 1
    # TODO: Get from authentication/session
    user_team_id = 1
    return get_draft_board(sess, user_team_id)

@router.post("/board/add", response_model=ActionResult)
def add_to_board_endpoint(
    request: AddToBoardRequest,
    sess: Session = Depends(get_session)
):
    """Add prospect to user's draft board."""
    # For MVP, assume user team ID is 1
    # TODO: Get from authentication/session
    user_team_id = 1
    
    try:
        add_to_board(sess, user_team_id, request.prospect_id)
        return ActionResult(ok=True, message="Prospect added to board")
    except Exception as e:
        return ActionResult(ok=False, message=str(e))

@router.post("/pick/make", response_model=ActionResult)
def make_pick_endpoint(
    request: MakePickRequest,
    sess: Session = Depends(get_session)
):
    """Make a draft pick."""
    # For MVP, assume user team ID is 1
    # TODO: Get from authentication/session
    user_team_id = 1
    
    # Get current pick number from draft state
    from sqlmodel import select
    from app.models.draft import DraftState
    
    state = sess.exec(select(DraftState)).first()
    if not state:
        return ActionResult(ok=False, message="No draft state found")
    
    return make_pick(sess, state.current_pick_overall, request.prospect_id, user_team_id)

@router.post("/sim/next-user", response_model=ActionResult)
def sim_next_user_pick_endpoint(sess: Session = Depends(get_session)):
    """Simulate AI picks until next user pick."""
    return sim_until_next_user_pick(sess)