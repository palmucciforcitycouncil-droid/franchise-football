# app/engine/batch_sim.py
from __future__ import annotations

from typing import Dict

from pydantic import BaseModel


class QuarterShape(BaseModel):
    """
    Relative weights for scoring distribution by quarter.
    These are normalized to sum to 1.0 when KPIs are computed.
    """
    q1: float = 1.0
    q2: float = 1.0
    q3: float = 1.0
    q4: float = 1.0

    def normalized(self) -> "QuarterShape":
        s = self.q1 + self.q2 + self.q3 + self.q4
        if s <= 0:
            return QuarterShape(q1=1, q2=1, q3=1, q4=1)
        return QuarterShape(q1=self.q1 / s, q2=self.q2 / s, q3=self.q3 / s, q4=self.q4 / s)


class FGBuckets(BaseModel):
    """
    Field goal make bias by distance bucket.
    This is a synthetic average used to affect td_fg_ratio and ppg slightly.
    """
    short: float = 1.0
    mid: float = 1.0
    long: float = 1.0

    def mean(self) -> float:
        return (self.short + self.mid + self.long) / 3.0


class Knobs(BaseModel):
    """
    Tunable synthetic 'knobs' for the calibration loop.
    Defaults are neutral (1.0) and quarter shape is even distribution.
    """
    pace_factor: float = 1.0
    red_zone_td_bias: float = 1.0
    fg_make_bias_by_bucket: FGBuckets = FGBuckets()
    pat_make_bias: float = 1.0
    two_point_attempt_bias: float = 1.0
    two_point_make_bias: float = 1.0
    turnover_bias: float = 1.0
    quarter_shape: QuarterShape = QuarterShape()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_kpis(knobs: Knobs) -> Dict[str, float | Dict[str, float]]:
    """
    Synthetic KPI generator mapping knobs → KPIs.
    Deterministic; no external data. Quarter shares sum to 1.0.
    """
    qshape = knobs.quarter_shape.normalized()
    fg_mean = knobs.fg_make_bias_by_bucket.mean()

    # Plays per game: base ~120, scaled by pace
    plays_per_game = 120.0 * knobs.pace_factor

    # TD/FG ratio: ~1.6 at neutral; more TD bias ↑, better FG make ↓ ratio
    td_fg_ratio = 1.6 * (knobs.red_zone_td_bias) / max(fg_mean, 1e-6)

    # Points per team mean:
    # - Center neutral at 23.0 so the loop can converge within bounds.
    # - Weighting term sums to 1.0 at neutral (0.85 + 0.10 + 0.05).
    base_points = 23.0
    scoring_term = (0.85 * knobs.red_zone_td_bias) + (0.10 * knobs.pat_make_bias) + (0.05 * knobs.two_point_make_bias)
    ppg = base_points
    ppg *= knobs.pace_factor
    ppg *= scoring_term
    # small adjustments: FG makes add a touch; turnovers subtract a bit
    ppg *= (1.0 + 0.03 * (fg_mean - 1.0) - 0.04 * (knobs.turnover_bias - 1.0))
    ppg = _clamp(ppg, 10.0, 45.0)

    # One-score rate (within 8 pts): tighter with neutral pace/low turnovers
    tight = 0.50
    tight -= 0.12 * abs(knobs.pace_factor - 1.0)
    tight -= 0.10 * abs(knobs.red_zone_td_bias - 1.0)
    tight -= 0.08 * (knobs.turnover_bias - 1.0)
    tight += 0.02 * (fg_mean - 1.0)
    one_score_rate = _clamp(tight, 0.30, 0.70)

    quarter_shares = {
        "q1": qshape.q1,
        "q2": qshape.q2,
        "q3": qshape.q3,
        "q4": qshape.q4,
    }

    return {
        "points_per_team_mean": ppg,
        "one_score_rate": one_score_rate,
        "td_fg_ratio": td_fg_ratio,
        "quarter_shares": quarter_shares,
        "plays_per_game": plays_per_game,
    }


def run_league_slate(weeks: int, seed: int, knobs: Knobs) -> Dict[str, float | Dict[str, float]]:
    """
    Deterministic harness stub: compute KPIs from knobs.
    Parameters accepted for contract compatibility; no RNG is required here.
    """
    return compute_kpis(knobs)
