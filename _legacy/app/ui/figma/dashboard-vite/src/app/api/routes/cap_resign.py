# app/api/routes/cap_resign.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Body
from sqlmodel import Session, select
from app.db import get_engine

from app.services.contracts import (
    init_season_cap_for_all_teams, compute_and_persist_team_cap, team_contracts_in_season,
    resign_candidates, submit_resign_offer, simulate_resign_window, DEFAULT_CAP_LIMIT
)
from app.models.contracts import Contract
from app.models.core_min import Player

router = APIRouter(tags=["cap","resign"])

def _session(): return Session(get_engine())

# ---- Auto-cap rows ----
@router.post("/cap/{season}/init")
def post_cap_init(season: int, cap_limit: int = DEFAULT_CAP_LIMIT):
    with _session() as s:
        return init_season_cap_for_all_teams(s, season, cap_limit)

@router.get("/cap/{season}/team/{team_id}")
def get_cap_for_team(season: int, team_id: int, cap_limit: int = DEFAULT_CAP_LIMIT):
    with _session() as s:
        row = compute_and_persist_team_cap(s, team_id, season, cap_limit)
        contracts = [c.model_dump() | {"end_season": c.end_season} for c in team_contracts_in_season(s, team_id, season)]
        return {"cap": row.model_dump(), "contracts": contracts}

# ---- Re-sign window ----
@router.get("/contracts/{season}/resign/candidates")
def get_resign_candidates(season: int):
    with _session() as s:
        pairs = resign_candidates(s, season)
        out = []
        for (p, c) in pairs:
            out.append({
                "player_id": getattr(p,"player_id",getattr(p,"id")),
                "name": getattr(p,"name", f"{getattr(p,'first_name','')} {getattr(p,'last_name','')}".strip()),
                "team_id": getattr(p,"team_id",None),
                "contract": {"start_season": c.start_season, "end_season": c.end_season, "aav": c.aav, "years": c.years}
            })
        return out

@router.post("/contracts/{season}/resign/bid")
def post_resign_bid(season: int, payload: dict = Body(...)):
    team_id = int(payload.get("team_id"))
    player_id = int(payload.get("player_id"))
    aav = int(payload.get("aav"))
    years = int(payload.get("years", 1))
    with _session() as s:
        try:
            return submit_resign_offer(s, season, team_id, player_id, aav, years)
        except ValueError as e:
            raise HTTPException(400, str(e))

@router.post("/contracts/{season}/resign/simulate")
def post_resign_simulate(season: int, cap_limit: int = DEFAULT_CAP_LIMIT):
    with _session() as s:
        return simulate_resign_window(s, season, cap_limit=cap_limit)


