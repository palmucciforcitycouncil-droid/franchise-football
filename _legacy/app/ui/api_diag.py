from __future__ import annotations
import importlib, traceback
from fastapi import APIRouter
from app.engine.config import get_conf

router = APIRouter()

@router.get("/diag/health")
def health():
    conf, meta = get_conf()
    return {"ok": True, "calibration": meta}

@router.get("/diag/modules")
def modules():
    mods = ["app.engine.pbp", "app.engine.sim_v2", "app.engine.sim_v3", "app.engine.sim_v4"]
    out = {}
    for m in mods:
        try:
            importlib.import_module(m)
            out[m] = "imported"
        except Exception as e:
            out[m] = f"ERROR: {type(e).__name__}: {e}"
    return out

@router.get("/diag/calibration")
def calibration_preview():
    conf, meta = get_conf()
    return {
        "meta": meta, 
        "keys": list(conf.keys()), 
        "pace_q": conf.get("pace", {}).get("base_play_sec_q", {})
    }

@router.get("/diag/sim_smoke")
def sim_smoke():
    """
    Tries to run each engine variant one snap; returns first exception details inline.
    Uses the new standardized simulate_game(home: TeamStub, away: TeamStub, config: GameConfig) interface.
    """
    from app.engine.types import TeamStub, GameConfig
    
    home = TeamStub(id=1, name="Home Team", offense=75, defense=75)
    away = TeamStub(id=2, name="Away Team", offense=70, defense=70)
    config = GameConfig(season_year=2025, week=1, game_id=1)
    
    results = {}
    
    # Test each engine
    for mod_name in ("app.engine.sim_v1", "app.engine.sim_v2", "app.engine.sim_v3", "app.engine.sim_v4"):
        try:
            m = importlib.import_module(mod_name)
            simulate_game = getattr(m, "simulate_game", None)
            if not simulate_game:
                raise RuntimeError("Missing simulate_game function")
            
            # Run simulation
            result = simulate_game(home, away, config)
            
            # Validate result
            if not hasattr(result, 'final_home') or not hasattr(result, 'final_away'):
                raise RuntimeError("Invalid result format")
            
            results[mod_name] = f"ok - {result.final_home}-{result.final_away}"
        except Exception:
            results[mod_name] = traceback.format_exc()
    
    return results


# --- Calibration KPI (quick sim vs GDD targets) ------------------------------
import csv, json, pathlib, sys
from typing import Dict

BASE = pathlib.Path("data/model")
GDD = BASE / "gdd_pacing_scoring.csv"

def _load_gdd_rows() -> Dict[int, dict]:
    rows = []
    with open(GDD, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({k: (int(v) if k == "quarter" else float(v)) for k, v in r.items()})
    return {r["quarter"]: r for r in rows}

def _sim_quick(n_games: int = 64):
    # reload to pick up latest calibration
    if "app.engine.pbp" in sys.modules:
        del sys.modules["app.engine.pbp"]
    from app.engine.pbp import simulate_game, TeamStrategy
    plays = {1:0,2:0,3:0,4:0}
    runs  = {1:0,2:0,3:0,4:0}
    passes= {1:0,2:0,3:0,4:0}
    points= {1:0,2:0,3:0,4:0}
    drives= {1:0,2:0,3:0,4:0}

    home = TeamStrategy("HOME")
    away = TeamStrategy("AWAY")

    for i in range(n_games):
        out = simulate_game(2025, 1, f"KPI{i:05d}", home, away)
        # New PBP engine returns structured events with quarter/score info
        home_score = out["score"]["home"]
        away_score = out["score"]["away"]
        
        # Process events to get quarter-by-quarter stats
        for ev in out["events"]:
            q = int(ev.get("q", 1))
            ssum = int(ev.get("score_home",0)) + int(ev.get("score_away",0))
            pt = ev.get("play_type", "")
            
            if pt == "drive_start":
                drives[q] += 1
            if pt in ("run_in","run_out","scramble","pass_short","pass_mid","pass_deep","sack"):
                plays[q] += 1
                if pt in ("run_in","run_out","scramble"):
                    runs[q] += 1
                else:
                    passes[q] += 1
        
        # Distribute total score evenly across quarters (simplified)
        total_score = home_score + away_score
        for q in (1,2,3,4):
            points[q] += total_score / 4.0

    per_team = n_games * 2
    kpi = {}
    for q in (1,2,3,4):
        T = plays[q] / per_team
        R = runs[q] / max(1, runs[q] + passes[q])
        P = points[q] / per_team
        D = drives[q] / per_team
        kpi[q] = {"T": round(T, 2), "R": round(R, 3), "P": round(P, 2), "D": round(D, 2)}
    return kpi

@router.get("/diag/calibration_kpi")
def calibration_kpi(games: int = 64):
    """
    Quick KPI vs GDD targets.
    Returns per-quarter T (plays/team), R (run share), P (points/team), D (drives/team),
    with deltas: actual - target.
    """
    try:
        gdd = _load_gdd_rows()
    except FileNotFoundError:
        return {"ok": False, "error": "Missing data/model/gdd_pacing_scoring.csv"}
    actual = _sim_quick(n_games=max(8, min(512, games)))
    rows = []
    for q in (1,2,3,4):
        a = actual[q]
        t = gdd[q]
        row = {
            "quarter": q,
            "T_actual": a["T"], "T_target": round(t["T_q"], 2), "T_delta": round(a["T"] - t["T_q"], 2),
            "R_actual": a["R"], "R_target": round(t["R_q"], 3), "R_delta": round(a["R"] - t["R_q"], 3),
            "P_actual": a["P"], "P_target": round(t["P_q"], 2), "P_delta": round(a["P"] - t["P_q"], 2),
            "D_actual": a["D"], "D_target": round(t["D_q"], 2), "D_delta": round(a["D"] - t["D_q"], 2),
        }
        rows.append(row)
    return {"ok": True, "games": games, "rows": rows}
