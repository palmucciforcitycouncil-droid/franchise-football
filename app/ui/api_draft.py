from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session
from app.core.db import get_session
from app.services.draft_service import (
    generate_draft_class, list_prospects, team_scout_view, upsert_scouting,
    set_draft_board, get_board, start_draft, pick_on_clock, cpu_pick, run_to_end
)

router = APIRouter(prefix="/api/v1/draft", tags=["draft"])

@router.post("/generate")
def api_generate(season: int, seed: int = 4242, sess: Session = Depends(get_session)):
    n = generate_draft_class(sess, season, seed)
    return {"ok": True, "prospects": n}

class ProspectDTO(BaseModel):
    prospect_id: int
    name: str
    pos: str
    age: int
    overall: int
    archetype: str
    college: str
    drafted_by_team_id: int | None
    drafted_round: int | None
    drafted_slot: int | None

@router.get("/prospects", response_model=List[ProspectDTO])
def api_prospects(season: int, pos: Optional[str] = None, sess: Session = Depends(get_session)):
    rows = list_prospects(sess, season, pos)
    out = []
    for p in rows:
        out.append(ProspectDTO(
            prospect_id=p.prospect_id, name=p.name, pos=p.pos.value, age=p.age,
            overall=p.overall, archetype=p.archetype, college=p.college,
            drafted_by_team_id=p.drafted_by_team_id, drafted_round=p.drafted_round, drafted_slot=p.drafted_slot
        ))
    return out

@router.get("/scout_view")
def api_scout_view(season: int, team_id: int, prospect_id: int, sess: Session = Depends(get_session)):
    return team_scout_view(sess, season, team_id, prospect_id)

class ScoutReq(BaseModel):
    season: int
    team_id: int
    prospect_id: int
    bias_overall: int
    confidence: int
    notes: str = ""

@router.post("/scout")
def api_scout(body: ScoutReq, sess: Session = Depends(get_session)):
    upsert_scouting(sess, body.season, body.team_id, body.prospect_id, body.bias_overall, body.confidence, body.notes)
    return {"ok": True}

class BoardReq(BaseModel):
    season: int
    team_id: int
    ordered_prospect_ids: List[int]

@router.post("/board")
def api_board(body: BoardReq, sess: Session = Depends(get_session)):
    set_draft_board(sess, body.season, body.team_id, body.ordered_prospect_ids)
    return {"ok": True}

@router.get("/board")
def api_get_board(season: int, team_id: int, sess: Session = Depends(get_session)):
    return {"ordered_prospect_ids": get_board(sess, season, team_id)}

@router.post("/start")
def api_start(season: int, seed: int = 4242, sess: Session = Depends(get_session)):
    start_draft(sess, season, seed)
    return {"ok": True}

class PickReq(BaseModel):
    season: int
    team_id: int
    prospect_id: int

@router.post("/pick")
def api_pick(body: PickReq, sess: Session = Depends(get_session)):
    return pick_on_clock(sess, body.season, body.team_id, body.prospect_id)

@router.post("/cpu_pick")
def api_cpu_pick(season: int, sess: Session = Depends(get_session)):
    return cpu_pick(sess, season)

@router.post("/run_to_end")
def api_run_to_end(season: int, sess: Session = Depends(get_session)):
    return run_to_end(sess, season)
