# app/api/routes/progression.py
from __future__ import annotations
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select
import json

from app.db import get_engine
from app.models.progression import PlayerProgression
from app.models.core_min import Player
from app.api.dto import (
    ProgressionDelta, ProgressionLeagueView,
    PlayerProgressionAudit, ProgressionAuditItem
)

router = APIRouter(prefix="/progression", tags=["progression"])

def _session() -> Session:
    return Session(get_engine())

_ATTRS = ["awareness","throw_accuracy","throw_power","catching","tackling","speed","agility","strength","stamina","morale"]

def _name(p: Player) -> str:
    return f"{getattr(p,'first_name','').strip()} {getattr(p,'last_name','').strip()}".strip() or getattr(p,"name","")

def _delta(before: Dict[str,int], after: Dict[str,int]) -> Dict[str,int]:
    return {k: int(after.get(k,0)) - int(before.get(k,0)) for k in _ATTRS}

def _total(d: Dict[str,int]) -> int:
    return sum(d.values())

@router.get("/{season}", response_model=ProgressionLeagueView)
def league_progression_view(
    season: int,
    top_n: int = Query(15, ge=1, le=100)
) -> ProgressionLeagueView:
    with _session() as s:
        rows = s.exec(select(PlayerProgression).where(PlayerProgression.season == season)).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No progression data for season")

        items: List[ProgressionDelta] = []
        for r in rows:
            p = s.get(Player, r.player_id)
            if not p:
                continue
            try:
                b = json.loads(r.before_json); a = json.loads(r.after_json)
            except Exception:
                continue
            d = _delta(b, a)
            items.append(ProgressionDelta(
                player_id=r.player_id,
                season=season,
                name=_name(p),
                position=getattr(p,"position",None) or getattr(p,"pos",None),
                team_id=getattr(p,"team_id",None),
                total_delta=_total(d),
                deltas=d
            ))

        if not items:
            raise HTTPException(status_code=404, detail="No valid progression items")

        risers = sorted(items, key=lambda x: x.total_delta, reverse=True)[:top_n]
        fallers = sorted(items, key=lambda x: x.total_delta)[:top_n]
        return ProgressionLeagueView(season=season, top_n=top_n, risers=risers, fallers=fallers)

@router.get("/player/{player_id}", response_model=PlayerProgressionAudit)
def player_progression_audit(player_id: int) -> PlayerProgressionAudit:
    with _session() as s:
        p = s.get(Player, player_id)
        if not p:
            raise HTTPException(status_code=404, detail="Player not found")

        rows = s.exec(select(PlayerProgression).where(PlayerProgression.player_id == player_id).order_by(PlayerProgression.season)).all()
        if not rows:
            return PlayerProgressionAudit(player_id=player_id, name=_name(p), position=getattr(p,"position",None) or getattr(p,"pos",None), audits=[])

        audits: List[ProgressionAuditItem] = []
        for r in rows:
            try:
                b = json.loads(r.before_json); a = json.loads(r.after_json); c = json.loads(r.components_json)
            except Exception:
                b, a, c = {}, {}, {}
            audits.append(ProgressionAuditItem(
                season=r.season,
                components=c,
                before=b,
                after=a,
                total_delta=_total({k: a.get(k,0) - b.get(k,0) for k in _ATTRS})
            ))
        return PlayerProgressionAudit(
            player_id=player_id,
            name=_name(p),
            position=getattr(p,"position",None) or getattr(p,"pos",None),
            audits=audits
        )
