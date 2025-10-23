# app/services/records.py
from __future__ import annotations
from typing import List, Dict, Iterable
import csv
from sqlmodel import Session, select, delete
from app.models.records import SingleSeasonRecord, CareerRecord
from app.models.season_stats import PlayerSeasonStats
from app.models.core_min import Player

STAT_FIELDS = {
    "pass_yards": "pass_yards", "pass_tds": "pass_tds",
    "rush_yards": "rush_yards", "rush_tds": "rush_tds",
    "recv_yards": "recv_yards", "recv_tds": "recv_tds",
    "sacks": "sacks", "interceptions_def": "interceptions_def",
    "tackles": "tackles",
}

def _pname(session: Session, pid: int) -> str:
    p = session.get(Player, pid)
    if not p: return ""
    fn = getattr(p,"first_name","") or ""; ln = getattr(p,"last_name","") or ""
    return (fn+" "+ln).strip() or getattr(p,"name","")

def rebuild_single_season_records(session: Session, season: int, top_n: int = 25) -> None:
    session.exec(delete(SingleSeasonRecord).where(SingleSeasonRecord.season == season))
    rows = session.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.season == season)).all()
    if not rows: session.commit(); return
    for stat, field in STAT_FIELDS.items():
        ranked = sorted(rows, key=lambda r: getattr(r, field, 0), reverse=True)[:top_n]
        for i, r in enumerate(ranked, start=1):
            session.add(SingleSeasonRecord(
                season=season, stat=stat, rank=i, player_id=r.player_id, team_id=r.team_id,
                player_name=_pname(session, r.player_id), value=float(getattr(r, field, 0))
            ))
    session.commit()

def rebuild_career_records(session: Session, top_n: int = 25) -> None:
    session.exec(delete(CareerRecord))
    # aggregate across seasons
    by_player: Dict[int, Dict[str, float]] = {}
    rows = session.exec(select(PlayerSeasonStats)).all()
    for r in rows:
        d = by_player.setdefault(r.player_id, {k:0.0 for k in STAT_FIELDS})
        for stat, field in STAT_FIELDS.items():
            d[stat] += float(getattr(r, field, 0))
    for stat in STAT_FIELDS:
        pairs = [(pid, vals[stat]) for pid, vals in by_player.items()]
        ranked = sorted(pairs, key=lambda t: t[1], reverse=True)[:top_n]
        for i, (pid, val) in enumerate(ranked, start=1):
            session.add(CareerRecord(stat=stat, rank=i, player_id=pid, player_name=_pname(session, pid), value=float(val)))
    session.commit()

def import_single_season_seed(session: Session, csv_path: str, season: int) -> int:
    session.exec(delete(SingleSeasonRecord).where(SingleSeasonRecord.season==season))
    c = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            session.add(SingleSeasonRecord(
                season=season, stat=row["stat"], rank=int(row["rank"]),
                player_id=int(row["player_id"]), player_name=row.get("player_name"),
                team_id=int(row["team_id"]) if row.get("team_id") else None,
                value=float(row["value"])
            )); c += 1
    session.commit(); return c

def import_career_seed(session: Session, csv_path: str) -> int:
    session.exec(delete(CareerRecord)); c = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            session.add(CareerRecord(
                stat=row["stat"], rank=int(row["rank"]),
                player_id=int(row["player_id"]), player_name=row.get("player_name"),
                value=float(row["value"])
            )); c += 1
    session.commit(); return c
