# app/api/routes/draft_pipeline.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query, Body
from sqlmodel import Session, select
from app.db import get_engine
from app.models.draft import Prospect
from app.services.draft_pipeline import seed_four_year_pipeline, rollover_draft_pipeline, finalize_draft_year
from typing import List

router = APIRouter(prefix="/draft", tags=["draft"])

def _session(): return Session(get_engine())

@router.post("/{season}/pipeline/seed")
def post_seed_pipeline(season:int, seed:int=2025):
    with _session() as s:
        return seed_four_year_pipeline(s, season, master_seed=seed)

@router.post("/{season}/pipeline/rollover")
def post_rollover(season:int, seed:int=2025):
    with _session() as s:
        return rollover_draft_pipeline(s, season, master_seed=seed)

@router.post("/{season}/pipeline/finalize")
def post_finalize(season:int):
    with _session() as s:
        return finalize_draft_year(s, season)

@router.get("/{season}/pipeline")
def get_pipeline_overview(season:int):
    with _session() as s:
        rows = s.exec(select(Prospect)).all()
        data = {"SR":0,"JR":0,"SO":0,"FR":0}
        by_pos = {k:0 for k in ["QB","RB","WR","TE","OL","DL","LB","DB","K","P"]}
        for r in rows:
            if r.class_year in data: data[r.class_year]+=1
            if r.pos in by_pos: by_pos[r.pos]+=1
        return {"season": season, "counts": data, "by_pos": by_pos}

@router.get("/{season}/class/{year}")
def list_class(season:int, year:str, pos:str|None=None, name:str|None=None, min_overall:int=0, min_potential:int=0, drafted:bool|None=None, limit:int=50, offset:int=0, sort:str="overall_desc"):
    year = year.upper()
    if year not in {"SR","JR","SO","FR"}:
        raise HTTPException(422, "year must be SR|JR|SO|FR")
    with _session() as s:
        q = select(Prospect).where(Prospect.class_year==year)
        # SR class is those eligible this season
        if year=="SR":
            q = q.where(Prospect.eligible_season==season)
        else:
            q = q.where(Prospect.expected_draft_season== (season + ({"JR":1,"SO":2,"FR":3}[year])) )
        rows = s.exec(q).all()
        # filters
        if pos: rows = [r for r in rows if r.pos==pos.upper()]
        if name: 
            needle=name.lower(); rows=[r for r in rows if needle in (r.name or "").lower()]
        if drafted is True: rows=[r for r in rows if r.drafted_by_team_id is not None]
        if drafted is False: rows=[r for r in rows if r.drafted_by_team_id is None]
        rows = [r for r in rows if (r.overall or 0)>=min_overall and (r.potential or 0)>=min_potential]
        # sort
        key = sort.lower()
        if key=="overall_desc": rows.sort(key=lambda r:(r.overall,r.potential), reverse=True)
        elif key=="potential_desc": rows.sort(key=lambda r:(r.potential,r.overall), reverse=True)
        elif key=="speed_desc": rows.sort(key=lambda r:(r.speed,r.overall), reverse=True)
        elif key=="awareness_desc": rows.sort(key=lambda r:(r.awareness,r.overall), reverse=True)
        else: rows.sort(key=lambda r:(r.overall,r.potential), reverse=True)
        return [r.model_dump() for r in rows[offset:offset+limit]]

@router.post("/{season}/watchlist")
def post_watchlist(season:int, ids: List[int] = Body(..., embed=True)):
    with _session() as s:
        updated=0
        for pid in ids:
            p = s.get(Prospect, pid)
            if p:
                p.watchlist = True
                s.add(p); updated+=1
        s.commit()
        return {"updated":updated}

@router.get("/{season}/watchlist")
def get_watchlist(season:int):
    with _session() as s:
        rows = s.exec(select(Prospect).where(Prospect.watchlist==True)).all()
        return [r.model_dump() for r in rows]


