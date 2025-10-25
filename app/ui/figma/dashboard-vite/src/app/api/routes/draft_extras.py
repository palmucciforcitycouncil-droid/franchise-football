# app/api/routes/draft_extras.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select
from app.db import get_engine
from app.models.draft import Prospect
from app.models.draft_audit import ProspectProgressAudit
from app.services.fa_cleanup import drop_uifas_without_contracts

router = APIRouter(prefix="/draft", tags=["draft"])

def _session(): return Session(get_engine())

@router.get("/{season}/pipeline/sparkline")
def get_watchlist_sparkline(season: int, max_points: int = Query(3, ge=1, le=5)):
    """
    Return last up-to-`max_points` OVRs for each watchlisted prospect.
    Uses ProspectProgressAudit rows (ovr_after) going backward from `season`.
    Falls back to the current Prospect.overall if no audit rows exist yet.
    """
    with _session() as s:
        watch = s.exec(select(Prospect).where(Prospect.watchlist == True)).all()
        if not watch:
            return []
        out = []
        for p in watch:
            pid = p.id
            # recent audits up to `season`, newest first
            audits = s.exec(
                select(ProspectProgressAudit)
                .where(ProspectProgressAudit.prospect_id == pid, ProspectProgressAudit.season <= season)
                .order_by(ProspectProgressAudit.season.desc())
            ).all()
            points = []
            for a in audits[:max_points]:
                points.append({"season": a.season, "ovr": a.ovr_after})
            if not points:
                # No audits yet → seed with current
                points.append({"season": season, "ovr": int(p.overall or 0)})
            out.append({
                "prospect_id": pid,
                "name": p.name,
                "pos": p.pos,
                "class_year": p.class_year,
                "expected_draft_season": p.expected_draft_season,
                "eligible_season": p.eligible_season,
                "sparkline": list(reversed(points))  # oldest→newest for UI charts
            })
        return out

@router.post("/{season}/fa_cleanup")
def post_fa_cleanup(season: int):
    with _session() as s:
        return drop_uifas_without_contracts(s, season)


