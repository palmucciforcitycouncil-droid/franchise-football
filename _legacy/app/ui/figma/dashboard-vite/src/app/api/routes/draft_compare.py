# app/api/routes/draft_compare.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session
from app.db import get_engine
from app.services.draft_compare import compare_prospects

router = APIRouter(prefix="/draft", tags=["draft"])

def _session() -> Session:
    return Session(get_engine())

@router.get("/{season}/board/compare")
def draft_compare(season: int, ids: str = Query(..., description="Comma-separated prospect IDs")):
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except Exception:
        raise HTTPException(422, "Invalid ids parameter")
    if not id_list or len(id_list) < 2:
        raise HTTPException(400, "Provide at least two prospect ids")
    with _session() as s:
        data = compare_prospects(s, season, id_list)
        if not data["items"]:
            raise HTTPException(404, "No matching prospects")
        return data


