# app/api/routes/contracts_fa.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Body
from sqlmodel import Session, select
from app.db import get_engine
from app.models.contracts import Contract
from app.models.cap import TeamCap
from app.models.core_min import Player
from app.services.contracts import (
    expire_contracts, compute_and_persist_team_cap, team_contracts_in_season,
    list_free_agents, submit_bid, simulate_free_agency, DEFAULT_CAP_LIMIT
)

router = APIRouter(tags=["contracts","free_agency"])

def _session(): return Session(get_engine())

@router.get("/contracts/{season}/team/{team_id}")
def get_team_contracts(season: int, team_id: int, cap_limit: int = DEFAULT_CAP_LIMIT):
    with _session() as s:
        contracts = [c.model_dump() | {"end_season": c.end_season} for c in team_contracts_in_season(s, team_id, season)]
        cap = compute_and_persist_team_cap(s, team_id, season, cap_limit)
        return {"season": season, "team_id": team_id, "cap": cap.model_dump() if cap else {}, "contracts": contracts}

@router.post("/contracts/{season}/expire")
def post_expire_contracts(season: int):
    with _session() as s:
        return expire_contracts(s, season)

@router.get("/free_agency/{season}/players")
def get_free_agents(season: int):
    with _session() as s:
        rows = list_free_agents(s, season)
        return [
            {
                "player_id": getattr(p,"player_id",getattr(p,"id")),
                "name": getattr(p, "name", f"{getattr(p,'first_name','')} {getattr(p,'last_name','')}".strip()),
                "position": getattr(p, "position", getattr(p,"pos",None)),
                "overall": getattr(p, "overall", None),
                "potential": getattr(p, "potential", None),
            } for p in rows
        ]

@router.post("/free_agency/{season}/bid")
def post_fa_bid(season: int, payload: dict = Body(...)):
    team_id = int(payload.get("team_id"))
    player_id = int(payload.get("player_id"))
    aav = int(payload.get("aav"))
    years = int(payload.get("years", 1))
    with _session() as s:
        # quick checks
        p = s.get(Player, player_id)
        if not p: raise HTTPException(404, "Player not found")
        if getattr(p, "team_id", None) is not None:
            raise HTTPException(400, "Player is not a free agent")
        return submit_bid(s, season, team_id, player_id, aav, years)

@router.post("/free_agency/{season}/simulate")
def post_fa_simulate(season: int, seed: int = 2025, cap_limit: int = DEFAULT_CAP_LIMIT):
    with _session() as s:
        return simulate_free_agency(s, season, seed=seed, cap_limit=cap_limit)
