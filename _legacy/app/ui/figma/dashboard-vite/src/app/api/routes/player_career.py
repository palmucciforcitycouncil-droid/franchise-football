# app/api/routes/player_career.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from sqlmodel import Session
from app.db import get_engine
from app.services.players import get_player_career_summary

router = APIRouter(prefix="/players", tags=["players"])

def _session() -> Session:
    return Session(get_engine())

@router.get("/{player_id}/career_summary")
def player_career_summary(player_id: int):
    with _session() as s:
        data = get_player_career_summary(s, player_id)
        if not data:
            raise HTTPException(status_code=404, detail="Player not found")
        return data

