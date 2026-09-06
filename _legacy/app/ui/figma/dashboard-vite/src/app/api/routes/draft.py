# app/api/routes/draft.py
from fastapi import APIRouter, HTTPException, Body
from sqlmodel import Session, select
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks
from app.models.draft import DraftClass, Prospect, DraftPick

router = APIRouter(prefix="/draft", tags=["draft"])

def _session(): 
    return Session(get_engine())

@router.post("/{season}/generate")
def post_generate_class(season: int, seed: int = 2025):
    with _session() as s:
        count = generate_draft_class(s, season, seed=seed)
        picks = assign_picks(s, season)
        return {"season": season, "prospects": count, "picks": picks}

@router.get("/{season}/class")
def get_class(season: int):
    with _session() as s:
        rows = s.exec(select(Prospect).where(Prospect.season == season).order_by(Prospect.pos, Prospect.overall.desc())).all()
        if not rows: 
            raise HTTPException(404, "No draft class")
        return [r.model_dump() for r in rows]

@router.get("/{season}/order")
def get_order(season: int):
    with _session() as s:
        picks = s.exec(select(DraftPick).where(DraftPick.season==season).order_by(DraftPick.overall_pick)).all()
        if not picks: 
            raise HTTPException(404, "No picks assigned")
        return [p.model_dump() for p in picks]

@router.post("/{season}/pick")
def post_pick(season: int, payload: dict = Body(...)):
    from app.services.draft import make_selection
    overall_pick = int(payload.get("overall_pick"))
    prospect_id = int(payload.get("prospect_id"))
    team_id = int(payload.get("team_id"))
    with _session() as s:
        try:
            return make_selection(s, season, overall_pick, prospect_id, team_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
