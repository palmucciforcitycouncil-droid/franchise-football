from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.db import get_session
from app.services import draft_service
from app.api.dto_draft import (
    ProspectDTO, PickRowDTO, DraftBoardDTO, DraftResultsDTO, ActionResult
)

router = APIRouter(prefix="/api/v1/draft", tags=["draft"])

@router.get("/results", response_model=DraftResultsDTO)
def get_draft_results_api(
    season: int,
    round: int,
    sess: Session = Depends(get_session)
):
    if not (1 <= round <= 7):
        raise HTTPException(status_code=400, detail="Round must be between 1 and 7.")
    return draft_service.get_draft_results(sess, season, round)

@router.get("/prospects", response_model=List[ProspectDTO])
def get_prospects_api(
    q: Optional[str] = None,
    top: bool = False,
    limit: int = 50,
    sess: Session = Depends(get_session)
):
    return draft_service.get_prospects(sess, q=q, top_only=top, limit=limit)

@router.get("/board", response_model=DraftBoardDTO)
def get_draft_board_api(
    user_team_id: int = 1,  # TODO: Get from auth context
    sess: Session = Depends(get_session)
):
    return draft_service.get_draft_board(sess, user_team_id)

@router.post("/board:add", response_model=ActionResult)
def add_to_board_api(
    prospect_id: int,
    user_team_id: int = 1,  # TODO: Get from auth context
    sess: Session = Depends(get_session)
):
    return draft_service.add_to_board(sess, user_team_id, prospect_id)

@router.post("/pick:make", response_model=ActionResult)
def make_pick_api(
    prospect_id: int,
    season: int,
    team_id: int = 1,  # TODO: Get from auth context
    sess: Session = Depends(get_session)
):
    # The overall_pick is determined by the current draft state, not passed in
    state = draft_service._get_draft_state(sess, season)
    return draft_service.make_pick(sess, season, prospect_id, team_id)

@router.post("/sim:next-user", response_model=ActionResult)
def sim_until_next_user_pick_api(
    season: int,
    user_team_id: int = 1,  # TODO: Get from auth context
    sess: Session = Depends(get_session)
):
    return draft_service.sim_until_next_user_pick(sess, season, user_team_id)
