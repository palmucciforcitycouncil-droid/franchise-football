from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from app.data.session import get_db
from app.services.import_service import import_players, import_coaches, rebuild_caps
from app.services.season_service import init_season, advance_week
from app.services.schedule_service import generate_round_robin_16
from app.models.sim_models import Team, Game
from app.models.player_models import Player
from app.models.contract_models import PlayerContract, CapSummary
from app.models.stats_models import TeamGameStats

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/import/players")
def import_players_api(session: Session = Depends(get_db)):
    count = import_players(session)
    rebuild_caps(session)
    return {"ok": True, "players": count}

@router.post("/import/coaches")
def import_coaches_api(session: Session = Depends(get_db)):
    count = import_coaches(session)
    return {"ok": True, "coaches": count}

@router.post("/season/init/{season}")
def season_init(season: int, seed: int = 2025, session: Session = Depends(get_db)):
    s = init_season(session, season, seed)
    generate_round_robin_16(session, season=season, seed=seed)
    return {"ok": True, "season": s.season, "week": s.current_week}

@router.post("/season/{season}/advance")
def season_advance(season: int, session: Session = Depends(get_db)):
    s = advance_week(session, season)
    return {"ok": True, "week": s.current_week}

@router.get("/diagnostics")
def diagnostics(session: Session = Depends(get_db)):
    counts = {
        "teams": session.exec(select(func.count(Team.id))).one(),
        "players": session.exec(select(func.count(Player.id))).one(),
        "games": session.exec(select(func.count(Game.id))).one(),
        "contracts": session.exec(select(func.count(PlayerContract.id))).one(),
        "caps": session.exec(select(func.count(CapSummary.id))).one(),
        "team_game_stats": session.exec(select(func.count(TeamGameStats.id))).one(),
    }
    # quick sanity: all scheduled games have season set, and scores are non-null only when is_played
    g = session.exec(select(Game)).all()
    played_consistent = all([(not x.is_played) or (x.home_score is not None and x.away_score is not None) for x in g])
    return {"ok": True, "counts": counts, "played_consistent": played_consistent}

@router.get("/readiness")
def readiness(session: Session = Depends(get_db)):
    # basic health snapshot (mirror of /api/health semantics)
    try:
        team_count = session.exec(select(func.count(Team.id))).one()
        db_ok = True
    except Exception:
        team_count = -1
        db_ok = False

    health = {
        "ok": db_ok,
        "db_ok": db_ok,
        "teams": team_count,
        "status": "healthy" if db_ok else "degraded",
    }

    modules = {
        # lightweight readiness of major subsystems
        "engine": {"loaded": True},
        "services": {"loaded": True},
        "routers": {"loaded": True},
    }

    calibration = {
        # placeholder signals; real values can be populated from calibration runs
        "status": "ok",
        "notes": "using default MVP tuning",
    }

    thresholds = {
        "abs_delta_ppg": 0.7,
        "quarter_share_rel_error": 0.10,
        "composition_run_pass_diff": 0.02,
    }

    # determinism basic check placeholder
    determinism_check = "ok" if db_ok else "fail"

    return {
        "ready": db_ok,
        "checks": {
            "health": health,
            "modules": modules,
            "calibration": calibration,
        },
        "thresholds": thresholds,
        "determinism_check": determinism_check,
    }
