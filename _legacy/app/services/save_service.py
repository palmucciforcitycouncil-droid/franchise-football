from __future__ import annotations
from typing import Any, Dict, List, Type
from sqlmodel import SQLModel, Session, select
from contextlib import contextmanager

# Import all models we persist
from app.models.sim_models import SimTeam as Team, SimGame as Game, SimGameEvent as GameEvent
from app.models.player_models import Player, DepthChart, PlayerInjury
from app.models.contract_models import PlayerContract, CapSummary
from app.models.season_models import Season
from app.models.stats_models import TeamGameStats
from app.models.playoffs_models import PlayoffRound, PlayoffMatchup
from app.models.coach_models import Coach

# Export/import order matters (children first on delete; parents first on insert where needed).
DELETE_ORDER = [
    GameEvent, TeamGameStats,
    PlayoffMatchup, PlayoffRound,
    PlayerInjury, DepthChart, PlayerContract, CapSummary,
    Coach, Player,
    Game,
    Team,
    Season,
]
INSERT_ORDER = [
    Season,
    Team,
    Coach,
    Player,
    CapSummary,
    PlayerContract,
    DepthChart,
    Game,
    GameEvent,
    TeamGameStats,
    PlayoffRound,
    PlayoffMatchup,
    PlayerInjury,
]

def _rows(session: Session, model: Type[SQLModel]) -> List[SQLModel]:
    return session.query(model).all()

def export_league(session: Session) -> Dict[str, Any]:
    def dump(model):
        name = model.__tablename__  # type: ignore[attr-defined]
        return name, [r.model_dump(mode='json') for r in _rows(session, model)]
    out: Dict[str, Any] = {"version": "mvp-1", "tables": {}}
    for model in INSERT_ORDER:
        n, data = dump(model)
        out["tables"][n] = data
    return out

def clear_league(session: Session):
    # Delete in FK-safe order
    for model in DELETE_ORDER:
        session.query(model).delete()  # type: ignore[attr-defined]
    session.commit()

def import_league(session: Session, data: Dict[str, Any], drop_all: bool = True):
    from datetime import datetime
    tables: Dict[str, List[Dict[str, Any]]] = data.get("tables", {})
    if drop_all:
        clear_league(session)
    # Insert preserving primary keys (assumes DB allows explicit PK insert)
    name_to_model = {m.__tablename__: m for m in INSERT_ORDER}  # type: ignore[attr-defined]
    for model in INSERT_ORDER:
        name = model.__tablename__  # type: ignore[attr-defined]
        rows = tables.get(name, [])
        for r in rows:
            # Convert datetime strings back to datetime objects
            if 'created_at' in r and isinstance(r['created_at'], str):
                dt_str = r['created_at']
                try:
                    # Try parsing with microseconds first
                    if '.' in dt_str and 'T' in dt_str:
                        # Ensure microseconds are exactly 6 digits
                        base_part, micro_part = dt_str.split('.', 1)
                        micro_part = micro_part[:6].ljust(6, '0')
                        dt_str = f"{base_part}.{micro_part}"
                        r['created_at'] = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f')
                    else:
                        # No microseconds
                        r['created_at'] = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    # Final fallback - try fromisoformat
                    try:
                        r['created_at'] = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    except ValueError:
                        # Last resort - try parsing without microseconds
                        if '.' in dt_str:
                            r['created_at'] = datetime.strptime(dt_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                        else:
                            r['created_at'] = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
            obj = model(**r)
            session.add(obj)
        session.commit()
