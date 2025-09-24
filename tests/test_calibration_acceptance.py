from app.core.seed import get_league_seed, make_rng
# tests/test_calibration_acceptance.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

import pytest

from app.engine.targets import CalibrationTargets
from app.engine.calibration import calibrate

# Deterministic seed for this project
get_league_seed() = 2025

# Resolve paths correctly:
# - This file lives in ...\franchise-football\tests\
# - The acceptance spec is in tests\spec\acceptance\scoring.yml (relative to THIS file)
# - The repo root is the parent of tests\
TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
ACCEPT_YAML = TESTS_DIR / "spec" / "acceptance" / "scoring.yml"
TARGETS_YAML = ROOT / "data" / "contracts" / "calibration_targets.yml"
REPORT_PATH = ROOT / "data" / "reports" / "season_kpis_2025.parquet"


def _load_acceptance(path: Path) -> Dict[str, Any]:
    """
    Parse YAML if available; otherwise parse as JSON (file contents are JSON-compatible).
    """
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)  # type: ignore
    except Exception:
        return json.loads(text)


def test_calibration_acceptance_converges(tmp_path: Path):
    """
    Acceptance: Using get_league_seed()=2025, run the proportional-nudge calibration loop
    for N weeks and up to max_iterations. Assert all tolerances are satisfied.
    """
    assert ACCEPT_YAML.exists(), f"Missing acceptance spec: {ACCEPT_YAML}"
    assert TARGETS_YAML.exists(), f"Missing calibration targets: {TARGETS_YAML}"

    # Read acceptance spec and targets
    acc = _load_acceptance(ACCEPT_YAML)
    weeks = int(acc.get("weeks", 18))
    max_iterations = int(acc.get("max_iterations", 60))

    targets = CalibrationTargets.load(TARGETS_YAML)

    # Run calibration
    knobs, obs, history = calibrate(
        targets=targets,
        weeks=weeks,
        seed=get_league_seed(),
        max_iterations=max_iterations,
        kpi_out_path=REPORT_PATH,
    )

    # Compute final observed KPIs (already returned) and assert within tolerances
    t = targets.targets
    tol = targets.tolerances

    ppg = float(obs["points_per_team_mean"])
    one = float(obs["one_score_rate"])
    ratio = float(obs["td_fg_ratio"])
    plays = float(obs["plays_per_game"])
    qs = obs["quarter_shares"]  # type: ignore
    q1, q2, q3, q4 = float(qs["q1"]), float(qs["q2"]), float(qs["q3"]), float(qs["q4"])

    failures = []

    # Relative tolerances
    def rel_ok(o: float, target: float, tol_pct: float) -> bool:
        if target == 0:
            return abs(o) < 1e-9
        return abs((o - target) / target) <= tol_pct

    # Absolute tolerances
    def abs_ok(o: float, target: float, tol_abs: float) -> bool:
        return abs(o - target) <= tol_abs

    if not rel_ok(ppg, t.points_per_team_mean, tol.points_per_team_mean_pct):
        failures.append(f"points_per_team_mean obs={ppg:.3f} target={t.points_per_team_mean:.3f} tol={tol.points_per_team_mean_pct:.3f} (rel)")

    if not abs_ok(one, t.one_score_rate_pp, tol.one_score_rate_pp):
        failures.append(f"one_score_rate obs={one:.3f} target={t.one_score_rate_pp:.3f} tol=Â±{tol.one_score_rate_pp:.3f} (abs pp)")

    if not rel_ok(ratio, t.td_fg_ratio, tol.td_fg_ratio_pct):
        failures.append(f"td_fg_ratio obs={ratio:.3f} target={t.td_fg_ratio:.3f} tol={tol.td_fg_ratio_pct:.3f} (rel)")

    if not rel_ok(plays, t.plays_per_game_mean, tol.plays_per_game_pct):
        failures.append(f"plays_per_game obs={plays:.3f} target={t.plays_per_game_mean:.3f} tol={tol.plays_per_game_pct:.3f} (rel)")

    if not abs_ok(q1, t.quarter_shares_pp.q1, tol.quarter_share_pp):
        failures.append(f"quarter_share q1 obs={q1:.3f} target={t.quarter_shares_pp.q1:.3f} tol=Â±{tol.quarter_share_pp:.3f}")
    if not abs_ok(q2, t.quarter_shares_pp.q2, tol.quarter_share_pp):
        failures.append(f"quarter_share q2 obs={q2:.3f} target={t.quarter_shares_pp.q2:.3f} tol=Â±{tol.quarter_share_pp:.3f}")
    if not abs_ok(q3, t.quarter_shares_pp.q3, tol.quarter_share_pp):
        failures.append(f"quarter_share q3 obs={q3:.3f} target={t.quarter_shares_pp.q3:.3f} tol=Â±{tol.quarter_share_pp:.3f}")
    if not abs_ok(q4, t.quarter_shares_pp.q4, tol.quarter_share_pp):
        failures.append(f"quarter_share q4 obs={q4:.3f} target={t.quarter_shares_pp.q4:.3f} tol=Â±{tol.quarter_share_pp:.3f}")

    if failures:
        msg = "Calibration failed to meet acceptance tolerances:\n  - " + "\n  - ".join(failures) + \
              f"\n\nFinal knobs: {knobs.model_dump()}\nLast history row: {history[-1] if history else 'none'}"
        pytest.fail(msg)

