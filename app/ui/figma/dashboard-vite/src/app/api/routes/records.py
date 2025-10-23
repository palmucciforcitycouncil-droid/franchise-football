# app/api/routes/records.py
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select
from app.db import get_engine
from app.models.records import SingleSeasonRecord, CareerRecord
from typing import List

router = APIRouter(prefix="/records", tags=["records"])

def _session(): 
    return Session(get_engine())

@router.get("/single/{stat}")
def get_single_season_leaders(stat: str, season: int | None = None, top_n: int = Query(25, ge=1, le=100)):
    with _session() as s:
        q = select(SingleSeasonRecord).where(SingleSeasonRecord.stat == stat)
        if season is not None:
            q = q.where(SingleSeasonRecord.season == season)
        rows = s.exec(q.order_by(SingleSeasonRecord.season, SingleSeasonRecord.rank)).all()
        if not rows: 
            raise HTTPException(404, "No single-season records")
        # slice top_n per season if season is provided; else return all seasons
        if season is not None:
            rows = rows[:top_n]
        return [r.model_dump() for r in rows]

@router.get("/career/{stat}")
def get_career_leaders(stat: str, top_n: int = Query(25, ge=1, le=100)):
    with _session() as s:
        rows = s.exec(select(CareerRecord).where(CareerRecord.stat==stat).order_by(CareerRecord.rank)).all()
        if not rows: 
            raise HTTPException(404, "No career records")
        return [r.model_dump() for r in rows[:top_n]]

@router.post("/rebuild/single")
def post_rebuild_single(season: int, top_n: int = 25):
    from app.services.records import rebuild_single_season_records
    with _session() as s:
        rebuild_single_season_records(s, season, top_n=top_n)
        return {"status":"ok","season":season}

@router.post("/rebuild/career")
def post_rebuild_career(top_n: int = 25):
    from app.services.records import rebuild_career_records
    with _session() as s:
        rebuild_career_records(s, top_n=top_n)
        return {"status":"ok"}
