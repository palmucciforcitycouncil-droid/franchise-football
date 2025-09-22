# app/engine/calibration.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from .batch_sim import Knobs, run_league_slate
from .targets import CalibrationTargets


def _rel_err(obs: float, tgt: float) -> float:
    if tgt == 0:
        return 0.0 if obs == 0 else float("inf")
    return (obs - tgt) / tgt


def _within_rel(obs: float, tgt: float, tol_pct: float) -> bool:
    return abs(_rel_err(obs, tgt)) <= tol_pct


def _within_abs(obs: float, tgt: float, tol_abs: float) -> bool:
    return abs(obs - tgt) <= tol_abs


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _apply_bounds(knobs: Knobs, kb) -> Knobs:
    """Clamp all knobs to their bounds, EXCEPT quarter_shape (weights are normalized later)."""
    return Knobs(
        pace_factor=kb.pace_factor.clamp(knobs.pace_factor),
        red_zone_td_bias=kb.red_zone_td_bias.clamp(knobs.red_zone_td_bias),
        fg_make_bias_by_bucket=type(knobs.fg_make_bias_by_bucket)(
            short=kb.fg_make_bias_by_bucket.short.clamp(knobs.fg_make_bias_by_bucket.short),
            mid=kb.fg_make_bias_by_bucket.mid.clamp(knobs.fg_make_bias_by_bucket.mid),
            long=kb.fg_make_bias_by_bucket.long.clamp(knobs.fg_make_bias_by_bucket.long),
        ),
        pat_make_bias=kb.pat_make_bias.clamp(knobs.pat_make_bias),
        two_point_attempt_bias=kb.two_point_attempt_bias.clamp(knobs.two_point_attempt_bias),
        two_point_make_bias=kb.two_point_make_bias.clamp(knobs.two_point_make_bias),
        turnover_bias=kb.turnover_bias.clamp(knobs.turnover_bias),
        # quarter_shape: pass-through (we normalize when computing KPIs)
        quarter_shape=type(knobs.quarter_shape)(
            q1=knobs.quarter_shape.q1,
            q2=knobs.quarter_shape.q2,
            q3=knobs.quarter_shape.q3,
            q4=knobs.quarter_shape.q4,
        ),
    )


def _nudge_mult(err_ratio: float, step_min: float = 0.005, step_max: float = 0.015) -> float:
    """
    Convert an error ratio (target/observed - 1 for relative metrics, or delta for absolute)
    into a bounded multiplicative nudge in ~0.5–1.5% increments.
    Positive value → scale up; negative → scale down.
    """
    mag = _clamp(abs(err_ratio), step_min, step_max)
    return 1.0 + (mag if err_ratio > 0 else -mag)


def _normalize_quarter_weights(qw: Dict[str, float]) -> Dict[str, float]:
    s = sum(qw.values())
    if s <= 0:
        return {"q1": 1, "q2": 1, "q3": 1, "q4": 1}
    return {k: v / s for k, v in qw.items()}


def calibrate(
    targets: CalibrationTargets,
    weeks: int,
    seed: int,
    max_iterations: int,
    kpi_out_path: Path | str = Path("data/reports/season_kpis_2025.parquet"),
) -> Tuple[Knobs, Dict[str, float | Dict[str, float]], List[Dict[str, float]]]:
    """
    Proportional-nudge calibration loop.

    Returns:
        (final_knobs, final_kpis, history_rows)
    """
    kb = targets.knob_bounds
    tol = targets.tolerances
    tgt = targets.targets

    knobs = Knobs()  # neutral start
    history: List[Dict[str, float]] = []

    # Ensure out dir exists
    out_path = Path(kpi_out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    for iteration in range(1, max_iterations + 1):
        obs = run_league_slate(weeks=weeks, seed=seed, knobs=knobs)

        # Extract values
        ppg_obs = float(obs["points_per_team_mean"])
        one_obs = float(obs["one_score_rate"])
        ratio_obs = float(obs["td_fg_ratio"])
        plays_obs = float(obs["plays_per_game"])
        q_obs = obs["quarter_shares"]  # type: ignore
        q1_obs, q2_obs, q3_obs, q4_obs = (float(q_obs["q1"]), float(q_obs["q2"]), float(q_obs["q3"]), float(q_obs["q4"]))

        # Check acceptance
        ok_ppg = _within_rel(ppg_obs, tgt.points_per_team_mean, tol.points_per_team_mean_pct)
        ok_one = _within_abs(one_obs, tgt.one_score_rate_pp, tol.one_score_rate_pp)
        ok_ratio = _within_rel(ratio_obs, tgt.td_fg_ratio, tol.td_fg_ratio_pct)
        ok_plays = _within_rel(plays_obs, tgt.plays_per_game_mean, tol.plays_per_game_pct)
        qs = tgt.quarter_shares_pp
        ok_q = (
            _within_abs(q1_obs, qs.q1, tol.quarter_share_pp)
            and _within_abs(q2_obs, qs.q2, tol.quarter_share_pp)
            and _within_abs(q3_obs, qs.q3, tol.quarter_share_pp)
            and _within_abs(q4_obs, qs.q4, tol.quarter_share_pp)
        )

        history.append(
            {
                "iteration": iteration,
                "points_per_team_mean": ppg_obs,
                "one_score_rate": one_obs,
                "td_fg_ratio": ratio_obs,
                "plays_per_game": plays_obs,
                "q1": q1_obs,
                "q2": q2_obs,
                "q3": q3_obs,
                "q4": q4_obs,
                "ok_ppg": float(ok_ppg),
                "ok_one": float(ok_one),
                "ok_ratio": float(ok_ratio),
                "ok_plays": float(ok_plays),
                "ok_q": float(ok_q),
            }
        )

        # Save snapshot table each iteration (Parquet preferred; CSV fallback)
        df = pd.DataFrame(history)
        try:
            import pyarrow  # noqa: F401
            df.to_parquet(out_path, index=False)
        except Exception:
            csv_path = out_path.with_suffix(".csv")
            df.to_csv(csv_path, index=False)

        if ok_ppg and ok_one and ok_ratio and ok_q and ok_plays:
            return knobs, obs, history

        # -------------------------
        # Proportional nudges
        # -------------------------

        # 1) Plays per game → pace_factor
        pace_err_ratio = (tgt.plays_per_game_mean / max(plays_obs, 1e-9)) - 1.0
        knobs.pace_factor *= _nudge_mult(pace_err_ratio)

        # 2) Points per team → red_zone_td_bias (primary)
        ppg_err_ratio = (tgt.points_per_team_mean / max(ppg_obs, 1e-9)) - 1.0
        knobs.red_zone_td_bias *= _nudge_mult(ppg_err_ratio)

        # 3) TD/FG ratio → FG make biases (all buckets proportionally)
        ratio_err_ratio = (ratio_obs - tgt.td_fg_ratio) / max(tgt.td_fg_ratio, 1e-9)
        fg_scale = _nudge_mult(+ratio_err_ratio)  # positive error → scale up FG make
        knobs.fg_make_bias_by_bucket.short *= fg_scale
        knobs.fg_make_bias_by_bucket.mid *= fg_scale
        knobs.fg_make_bias_by_bucket.long *= fg_scale

        # 4) One-score rate → turnover_bias (higher turnovers → fewer one-score games)
        one_err = one_obs - tgt.one_score_rate_pp
        knobs.turnover_bias *= _nudge_mult(+one_err)

        # 5) Quarter shares → quarter_shape weights (proportional then normalize)
        qw = {
            "q1": knobs.quarter_shape.q1,
            "q2": knobs.quarter_shape.q2,
            "q3": knobs.quarter_shape.q3,
            "q4": knobs.quarter_shape.q4,
        }
        for k, obs_v, tgt_v in [("q1", q1_obs, qs.q1), ("q2", q2_obs, qs.q2), ("q3", q3_obs, qs.q3), ("q4", q4_obs, qs.q4)]:
            err_ratio = (tgt_v / max(obs_v, 1e-9)) - 1.0
            qw[k] *= _nudge_mult(err_ratio)
        qw = _normalize_quarter_weights(qw)
        knobs.quarter_shape.q1 = qw["q1"]
        knobs.quarter_shape.q2 = qw["q2"]
        knobs.quarter_shape.q3 = qw["q3"]
        knobs.quarter_shape.q4 = qw["q4"]

        # 6) Minor: PAT and 2PT biases gently track points if far off
        if not ok_ppg:
            knobs.pat_make_bias *= _nudge_mult(ppg_err_ratio * 0.3)
            knobs.two_point_make_bias *= _nudge_mult(ppg_err_ratio * 0.2)

        # Enforce bounds (no clamp for quarter_shape)
        knobs = _apply_bounds(knobs, kb)

    obs = run_league_slate(weeks=weeks, seed=seed, knobs=knobs)
    return knobs, obs, history
