# app/engine/targets.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from pydantic import BaseModel, Field, ValidationError, field_validator


def _load_text(path: Path) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Calibration targets file not found: {path}")
    return path.read_text(encoding="utf-8")


def _parse_yaml_or_json(text: str) -> Dict[str, Any]:
    """
    Parse YAML if PyYAML is available; otherwise parse as JSON.
    Keeping the file contents JSON-compatible avoids a hard dependency on PyYAML.
    """
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)  # type: ignore
    except Exception:
        import json
        return json.loads(text)


class QuarterShares(BaseModel):
    """Quarter shares (probabilities) for Q1..Q4."""
    q1: float
    q2: float
    q3: float
    q4: float

    def normalized(self) -> "QuarterShares":
        s = self.q1 + self.q2 + self.q3 + self.q4
        if s <= 0:
            return QuarterShares(q1=0.25, q2=0.25, q3=0.25, q4=0.25)
        return QuarterShares(q1=self.q1 / s, q2=self.q2 / s, q3=self.q3 / s, q4=self.q4 / s)


class Targets(BaseModel):
    """Target KPI values used by the calibration loop."""
    points_per_team_mean: float = Field(..., alias="points_per_team_mean")
    one_score_rate_pp: float
    td_fg_ratio: float
    quarter_shares_pp: QuarterShares
    plays_per_game_mean: float

    @field_validator("quarter_shares_pp")
    @classmethod
    def _normalize_qshares(cls, v: QuarterShares) -> QuarterShares:
        return v.normalized()


class Tolerances(BaseModel):
    """Tolerance bands (relative or absolute as specified)."""
    points_per_team_mean_pct: float
    one_score_rate_pp: float
    td_fg_ratio_pct: float
    quarter_share_pp: float
    plays_per_game_pct: float


class FloatBounds(BaseModel):
    """Inclusive [lo, hi] bounds for a single knob."""
    lo: float
    hi: float

    @classmethod
    def from_value(cls, v: Any) -> "FloatBounds":
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return FloatBounds(lo=float(v[0]), hi=float(v[1]))
        if isinstance(v, Mapping) and "lo" in v and "hi" in v:
            return FloatBounds(lo=float(v["lo"]), hi=float(v["hi"]))
        raise ValueError(f"Unrecognized bounds format: {v!r}")

    def clamp(self, x: float) -> float:
        return max(self.lo, min(self.hi, x))


class FGMakeBucketsBounds(BaseModel):
    short: FloatBounds
    mid: FloatBounds
    long: FloatBounds

    @classmethod
    def from_value(cls, v: Mapping[str, Any]) -> "FGMakeBucketsBounds":
        return FGMakeBucketsBounds(
            short=FloatBounds.from_value(v["short"]),
            mid=FloatBounds.from_value(v["mid"]),
            long=FloatBounds.from_value(v["long"]),
        )


class QuarterShapeBounds(BaseModel):
    q1: FloatBounds
    q2: FloatBounds
    q3: FloatBounds
    q4: FloatBounds

    @classmethod
    def from_value(cls, v: Mapping[str, Any]) -> "QuarterShapeBounds":
        return QuarterShapeBounds(
            q1=FloatBounds.from_value(v["q1"]),
            q2=FloatBounds.from_value(v["q2"]),
            q3=FloatBounds.from_value(v["q3"]),
            q4=FloatBounds.from_value(v["q4"]),
        )


class KnobBounds(BaseModel):
    """Bounds for every tunable knob."""
    pace_factor: FloatBounds
    red_zone_td_bias: FloatBounds
    fg_make_bias_by_bucket: FGMakeBucketsBounds
    pat_make_bias: FloatBounds
    two_point_attempt_bias: FloatBounds
    two_point_make_bias: FloatBounds
    turnover_bias: FloatBounds
    quarter_shape: QuarterShapeBounds

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "KnobBounds":
        return KnobBounds(
            pace_factor=FloatBounds.from_value(raw["pace_factor"]),
            red_zone_td_bias=FloatBounds.from_value(raw["red_zone_td_bias"]),
            fg_make_bias_by_bucket=FGMakeBucketsBounds.from_value(raw["fg_make_bias_by_bucket"]),
            pat_make_bias=FloatBounds.from_value(raw["pat_make_bias"]),
            two_point_attempt_bias=FloatBounds.from_value(raw["two_point_attempt_bias"]),
            two_point_make_bias=FloatBounds.from_value(raw["two_point_make_bias"]),
            turnover_bias=FloatBounds.from_value(raw["turnover_bias"]),
            quarter_shape=QuarterShapeBounds.from_value(raw["quarter_shape"]),
        )


class CalibrationTargets(BaseModel):
    """
    Root DTO:
    - targets: KPI targets
    - tolerances: acceptance tolerances
    - knob_bounds: bounds for tunable knobs (enforced every iteration)
    """
    targets: Targets
    tolerances: Tolerances
    knob_bounds: KnobBounds

    @classmethod
    def load(cls, path: Path | str) -> "CalibrationTargets":
        raw = _parse_yaml_or_json(_load_text(Path(path)))
        kb = KnobBounds.from_raw(raw["knob_bounds"])
        try:
            return CalibrationTargets(
                targets=Targets(**raw["targets"]),
                tolerances=Tolerances(**raw["tolerances"]),
                knob_bounds=kb,
            )
        except ValidationError as e:
            raise ValueError(f"Invalid calibration_targets.yml schema: {e}") from e
