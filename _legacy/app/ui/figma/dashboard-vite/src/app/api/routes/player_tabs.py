# app/api/routes/player_tabs.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.db import get_engine

from app.models.core_min import Player
from app.models.awards import AwardResult
from app.models.progression import PlayerProgression

import json

router = APIRouter(prefix="/players", tags=["players"])

def _session() -> Session:
    return Session(get_engine())

def _ensure_player(s: Session, player_id: int) -> Player:
    p = s.get(Player, player_id)
    if not p:
        raise HTTPException(404, "Player not found")
    return p

@router.get("/{player_id}/awards")
def get_player_awards(player_id: int):
    with _session() as s:
        _ensure_player(s, player_id)
        rows = s.exec(
            select(AwardResult)
            .where(AwardResult.player_id == player_id)
            .order_by(AwardResult.season, AwardResult.award, AwardResult.rank)
        ).all()
        # Return lean JSON for the UI
        return [
            {
                "season": r.season,
                "award": r.award,
                "rank": r.rank,
                "score": r.score,
                "team_id": r.team_id,
                "player_name": r.player_name,
                "position": r.position,
            }
            for r in rows
        ]

@router.get("/{player_id}/progression")
def get_player_progression(player_id: int):
    with _session() as s:
        _ensure_player(s, player_id)
        rows = s.exec(
            select(PlayerProgression)
            .where(PlayerProgression.player_id == player_id)
            .order_by(PlayerProgression.season)
        ).all()
        out = []
        for r in rows:
            try:
                before = json.loads(r.before_json)
                after = json.loads(r.after_json)
                components = json.loads(r.components_json) if r.components_json else {}
            except Exception:
                before, after, components = {}, {}, {}
            out.append({
                "season": r.season,
                "before": before,
                "after": after,
                "components": components,
                "total_delta": sum(int(after.get(k,0))-int(before.get(k,0)) for k in [
                    "awareness","throw_accuracy","throw_power","catching","tackling","speed","agility","strength","stamina","morale"
                ]),
            })
        return out


