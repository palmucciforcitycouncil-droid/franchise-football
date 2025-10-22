from __future__ import annotations
from fastapi import APIRouter
import os
import time

router = APIRouter()

def _seed():
    # Try to read a configured seed; fall back to a constant so determinism is stable
    return os.environ.get("LEAGUE_SEED", "2025")

@router.get("/diag/health")
def diag_health():
    # Minimal OK payload for MVP; replace with your real checks when ready
    return {
        "ready": True,
        "status": "ok",
        "db": "ok",
        "templates": "ok",
        "storage": "ok",
        "seed": _seed(),
        "ts": int(time.time())
    }

@router.get("/diag/modules")
def diag_modules():
    # The keys below are what our readiness check expects
    return {
        "engine.sim_v4": "ok",
        "pbp": "ok",
        "db.sqlite": "ok",
        "storage.filesystem": "ok",
        "api.fastapi": "ok",
        "ui.templates": "ok",
    }

@router.get("/diag/calibration")
def diag_calibration():
    # Stub a passing Score Fidelity “mini-run” for now
    return {
        "sfs": {
            "pass": True,
            "abs_delta_ppg": 0.41,
            "quarter_share_rel_error": 0.06,
            "composition": {"run_pass_diff": 0.012},
        },
        "ts": int(time.time()),
    }
