# scripts/api_score_app.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any
import json
import sys

# ensure repo root on sys.path (so 'app' package is importable)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.engine.targets import CalibrationTargets
from app.engine.calibration import calibrate

DEFAULT_SEED = 2025

app = FastAPI(title="Score Fidelity Calibration API", version="0.1.1")

class CalibrateRequest(BaseModel):
    year: int = Field(default=2025, ge=1900, le=3000)
    weeks: Optional[int] = Field(default=None, ge=1, le=30)
    max_iterations: Optional[int] = Field(default=None, ge=1, le=500)
    targets_path: str = "data/contracts/calibration_targets.yml"
    acceptance_path: str = "tests/spec/acceptance/scoring.yml"
    mirror_csv: bool = True  # <- default ON for convenience on Windows

def _load_acceptance(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)  # type: ignore
    except Exception:
        return json.loads(text)

@app.post("/calibrate/score")
def calibrate_score(req: CalibrateRequest):
    repo = REPO_ROOT
    targets_path = (repo / req.targets_path).resolve()
    accept_path = (repo / req.acceptance_path).resolve()
    reports_dir = (repo / "data" / "reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not targets_path.exists():
        return {"ok": False, "error": f"targets file not found: {targets_path}"}
    if not accept_path.exists():
        return {"ok": False, "error": f"acceptance file not found: {accept_path}"}

    acc = _load_acceptance(accept_path)
    weeks = int(req.weeks or acc.get("weeks", 18))
    max_iterations = int(req.max_iterations or acc.get("max_iterations", 60))

    out_path = reports_dir / f"season_kpis_{req.year}.parquet"

    ct = CalibrationTargets.load(targets_path)
    knobs, obs, hist = calibrate(
        targets=ct,
        weeks=weeks,
        seed=DEFAULT_SEED,
        max_iterations=max_iterations,
        kpi_out_path=out_path,
    )

    # Mirror CSV next to Parquet if requested
    csv_path = out_path.with_suffix(".csv")
    if req.mirror_csv:
        try:
            import pandas as pd
            df = pd.read_parquet(out_path)
            df.to_csv(csv_path, index=False)
            csv_ok = True
        except Exception as e:
            csv_ok = False
    else:
        csv_ok = False

    # Format compact response
    def _round(v):
        return round(v, 4) if isinstance(v, float) else v

    compact_obs = {k: _round(v) if not isinstance(v, dict) else {ik: _round(iv) for ik, iv in v.items()} for k, v in obs.items()}

    return {
        "ok": True,
        "year": req.year,
        "weeks": weeks,
        "iterations": len(hist),
        "report_parquet": str(out_path),
        "report_csv": str(csv_path) if csv_ok else None,
        "final_kpis": compact_obs,
        "final_knobs": knobs.model_dump(),
    }
