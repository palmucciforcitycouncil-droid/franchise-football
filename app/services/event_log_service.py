from __future__ import annotations
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlmodel import Session, select
from app.models.event_log import EventLog

def emit_event(sess: Session, *, season: int, week: int, event_type: str,
               team_id: Optional[int] = None, player_id: Optional[int] = None,
               coach_id: Optional[int] = None, game_id: Optional[int] = None,
               payload: Optional[Dict[str, Any]] = None) -> EventLog:
    row = EventLog(season=season, week=week, event_type=event_type,
                   team_id=team_id, player_id=player_id, coach_id=coach_id, game_id=game_id,
                   payload_json=json.dumps(payload or {}))
    sess.add(row); sess.commit(); sess.refresh(row)
    return row

def feed_since(sess: Session, *, since_id: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
    q = select(EventLog).order_by(EventLog.id.desc())
    if since_id:
        q = q.where(EventLog.id > since_id)
    rows = list(sess.exec(q))[:limit]
    out = []
    for r in rows:
        out.append({
            "id": r.id, "ts": r.ts.isoformat(), "season": r.season, "week": r.week, "event_type": r.event_type,
            "team_id": r.team_id, "player_id": r.player_id, "coach_id": r.coach_id, "game_id": r.game_id,
            "payload": json.loads(r.payload_json or "{}")
        })
    return out
