from __future__ import annotations
import json, os, gzip
from typing import Any, Dict, List, Type, Optional
from sqlmodel import Session, select
from app.db import get_engine
from app.services.save_models import SaveBundle, SCHEMA_VERSION

# Import model types with best-effort guards (some may not exist yet in your repo)
def _try_import(path: str, name: str):
    """Safely import a model class, returning None if it doesn't exist."""
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

# Core league models
Team = _try_import("app.models.team", "Team")

# Player models
Player = _try_import("app.models.player", "Player")
PlayerContract = _try_import("app.models.contracts", "PlayerContract")
PlayerContractAsk = _try_import("app.models.contracts", "PlayerContractAsk")
TeamTradeBlock = _try_import("app.models.contracts", "TeamTradeBlock")

# Coach models
Coach = _try_import("app.models.coach", "Coach")
CoachContract = _try_import("app.models.coach", "CoachContract")
CoachAsk = _try_import("app.models.coach", "CoachAsk")
CoachOffer = _try_import("app.models.coach", "CoachOffer")

# Coach focus models
CoachFocusAssignment = _try_import("app.models.coach_focus", "CoachFocusAssignment")
TeamWeeklyCoachEffects = _try_import("app.models.coach_focus", "TeamWeeklyCoachEffects")
TeamSeasonFocusTally = _try_import("app.models.coach_focus", "TeamSeasonFocusTally")

# Gameplan models
GameplanSelection = _try_import("app.models.gameplan", "GameplanSelection")
GameplanTrace = _try_import("app.models.gameplan_trace", "GameplanTrace")

# League structure models
Standings = _try_import("app.models.standings", "Standings")
Game = _try_import("app.models.schedule", "Game")
GameResult = _try_import("app.models.results", "GameResult")

# Awards and records models
AwardsWeekly = _try_import("app.models.awards", "AwardsWeekly")
AwardsAnnual = _try_import("app.models.awards", "AwardsAnnual")
HOF = _try_import("app.models.hof", "HallOfFameInductee")
RecordSeason = _try_import("app.models.records", "SingleSeasonRecord")
RecordCareer = _try_import("app.models.records", "CareerRecord")

# Meta model
LeagueMeta = _try_import("app.models.meta", "LeagueMeta")

DUMP_DIR = os.environ.get("FF_SAVE_DIR", "saves")

def _ensure_dir():
    """Ensure the save directory exists."""
    os.makedirs(DUMP_DIR, exist_ok=True)

def _dump_table(sess: Session, model: Any) -> List[Dict[str, Any]]:
    """Dump all rows from a table to a list of dictionaries."""
    if model is None: 
        return []
    
    rows = list(sess.exec(select(model)))
    out: List[Dict[str, Any]] = []
    
    for r in rows:
        # Use model_dump if pydantic/SQLModel v0.0.16+, else __dict__+cleanup
        try:
            d = r.model_dump()
        except Exception:
            d = {k: v for k, v in r.__dict__.items() if not k.startswith("_")}
        out.append(d)
    
    return out

def _insert_rows(sess: Session, model: Any, rows: List[Dict[str, Any]]):
    """Insert rows into a table."""
    if model is None or not rows: 
        return
    
    for d in rows:
        obj = model(**d)
        sess.add(obj)
    sess.commit()

def snapshot_league(sess: Session) -> SaveBundle:
    """Create a complete snapshot of the league state."""
    # Get meta data
    meta_row = None
    if LeagueMeta:
        meta_row = sess.exec(select(LeagueMeta).order_by(LeagueMeta.id.desc())).first()
    
    meta = meta_row.model_dump() if meta_row else dict(
        current_season=2031, 
        current_week=1, 
        primary_rng_seed=123456, 
        trade_rng_seed=654321, 
        injury_rng_seed=777777
    )

    # Create save bundle with all data
    bundle = SaveBundle(
        schema_version=SCHEMA_VERSION,
        meta=meta,
        
        # Core league data
        teams=_dump_table(sess, Team),
        players=_dump_table(sess, Player),
        player_contracts=_dump_table(sess, PlayerContract),
        player_contract_asks=_dump_table(sess, PlayerContractAsk),
        trade_block=_dump_table(sess, TeamTradeBlock),

        # Coaching data
        coaches=_dump_table(sess, Coach),
        coach_contracts=_dump_table(sess, CoachContract),
        coach_asks=_dump_table(sess, CoachAsk),
        coach_offers=_dump_table(sess, CoachOffer),

        # Coach focus system
        coach_focus_assignments=_dump_table(sess, CoachFocusAssignment),
        team_weekly_focus_effects=_dump_table(sess, TeamWeeklyCoachEffects),
        team_season_focus_tallies=_dump_table(sess, TeamSeasonFocusTally),

        # Gameplan system
        gameplan_selections=_dump_table(sess, GameplanSelection),
        gameplan_traces=_dump_table(sess, GameplanTrace),

        # League structure
        standings=_dump_table(sess, Standings),
        schedule=_dump_table(sess, Game),
        results=_dump_table(sess, GameResult),

        # Awards and records
        awards_weekly=_dump_table(sess, AwardsWeekly),
        awards_annual=_dump_table(sess, AwardsAnnual),
        hof_inductees=_dump_table(sess, HOF),
        records_single_season=_dump_table(sess, RecordSeason),
        records_career=_dump_table(sess, RecordCareer),
    )
    
    return bundle

def export_league(path_name: str, gzip_enabled: bool = True) -> str:
    """
    Export league to ./saves/<path_name>.json[.gz]
    Returns absolute path of the written file.
    """
    _ensure_dir()
    
    with Session(get_engine()) as sess:
        bundle = snapshot_league(sess)
        payload = bundle.model_dump()
        
        out_path = os.path.join(DUMP_DIR, f"{path_name}.json")
        if gzip_enabled:
            out_path += ".gz"
            with gzip.open(out_path, "wt", encoding="utf-8") as f:
                json.dump(payload, f, separators=(",", ":"))
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        
        return os.path.abspath(out_path)

def _clear_all(sess: Session):
    """
    Truncate tables we manage, in safe dependency order.
    """
    # Order matters loosely (offers depend on coaches, etc.)
    for model in [
        GameplanTrace, GameplanSelection,
        CoachOffer, CoachAsk, CoachContract, Coach,
        TeamWeeklyCoachEffects, TeamSeasonFocusTally, CoachFocusAssignment,
        PlayerContractAsk, TeamTradeBlock, PlayerContract, Player,
        Standings, GameResult, Game,
        AwardsWeekly, AwardsAnnual, HOF, RecordSeason, RecordCareer,
        Team,
        LeagueMeta,
    ]:
        if model is None: 
            continue
        
        try:
            sess.exec(model.delete())  # type: ignore
            sess.commit()
        except Exception:
            # Fallback: iterate and delete
            try:
                rows = list(sess.exec(select(model)))
                for r in rows: 
                    sess.delete(r)
                sess.commit()
            except Exception:
                pass

def import_league(path_name: str) -> Dict[str, Any]:
    """
    Import league from ./saves/<path_name>.json[.gz]
    Clears existing data for managed tables first.
    """
    _ensure_dir()
    
    full = os.path.join(DUMP_DIR, f"{path_name}.json")
    gz = full + ".gz"
    file_path = gz if os.path.exists(gz) else full
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    # Read the file
    if file_path.endswith(".gz"):
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

    bundle = SaveBundle(**payload)
    
    if bundle.schema_version != SCHEMA_VERSION:
        # You can add migration logic here when you bump versions
        pass

    with Session(get_engine()) as sess:
        # Clear existing data
        _clear_all(sess)

        # Insert meta first
        if LeagueMeta and bundle.meta:
            sess.add(LeagueMeta(**bundle.meta))
            sess.commit()

        # Insert core tables
        _insert_rows(sess, Team, bundle.teams)
        _insert_rows(sess, Player, bundle.players)
        _insert_rows(sess, PlayerContract, bundle.player_contracts)
        _insert_rows(sess, PlayerContractAsk, bundle.player_contract_asks)
        _insert_rows(sess, TeamTradeBlock, bundle.trade_block)

        # Insert coaching data
        _insert_rows(sess, Coach, bundle.coaches)
        _insert_rows(sess, CoachContract, bundle.coach_contracts)
        _insert_rows(sess, CoachAsk, bundle.coach_asks)
        _insert_rows(sess, CoachOffer, bundle.coach_offers)

        # Insert coach focus data
        _insert_rows(sess, CoachFocusAssignment, bundle.coach_focus_assignments)
        _insert_rows(sess, TeamWeeklyCoachEffects, bundle.team_weekly_focus_effects)
        _insert_rows(sess, TeamSeasonFocusTally, bundle.team_season_focus_tallies)

        # Insert gameplan data
        _insert_rows(sess, GameplanSelection, bundle.gameplan_selections)
        _insert_rows(sess, GameplanTrace, bundle.gameplan_traces)

        # Insert league structure data
        _insert_rows(sess, Standings, bundle.standings)
        _insert_rows(sess, Game, bundle.schedule)
        _insert_rows(sess, GameResult, bundle.results)

        # Insert awards and records data
        _insert_rows(sess, AwardsWeekly, bundle.awards_weekly)
        _insert_rows(sess, AwardsAnnual, bundle.awards_annual)
        _insert_rows(sess, HOF, bundle.hof_inductees)
        _insert_rows(sess, RecordSeason, bundle.records_single_season)
        _insert_rows(sess, RecordCareer, bundle.records_career)

    return {
        "ok": True, 
        "schema_version": bundle.schema_version, 
        "meta": bundle.meta
    }

def list_saves() -> List[Dict[str, str]]:
    """List all available save files."""
    _ensure_dir()
    out = []
    
    for fn in sorted(os.listdir(DUMP_DIR)):
        if fn.endswith(".json") or fn.endswith(".json.gz"):
            out.append({
                "name": fn, 
                "path": os.path.abspath(os.path.join(DUMP_DIR, fn))
            })
    
    return out

def get_save_info(path_name: str) -> Dict[str, Any]:
    """Get information about a specific save file."""
    _ensure_dir()
    
    full = os.path.join(DUMP_DIR, f"{path_name}.json")
    gz = full + ".gz"
    file_path = gz if os.path.exists(gz) else full
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    # Read just the header info
    if file_path.endswith(".gz"):
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            # Read first few lines to get schema_version and meta
            content = f.read(1000)  # Read enough to get the header
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(1000)
    
    try:
        # Parse just enough to get the header
        data = json.loads(content + "}")  # Close the JSON
        return {
            "schema_version": data.get("schema_version", "unknown"),
            "meta": data.get("meta", {}),
            "file_size": os.path.getsize(file_path),
            "compressed": file_path.endswith(".gz")
        }
    except Exception:
        return {
            "schema_version": "unknown",
            "meta": {},
            "file_size": os.path.getsize(file_path),
            "compressed": file_path.endswith(".gz")
        }