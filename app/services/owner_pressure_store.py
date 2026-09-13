"""
Franchise-level OwnerWinPressure persistence (R3d spec Sec 3.2).

Deliberately NOT stored on the Coach row: OwnerWinPressure is a
FRANCHISE property, not a personal one -- settled decision #6 in
docs/R3d_COACHING_SYSTEM_SPECIFICATION.md says it "does NOT reset when
HC is fired" and Sec 6 says it "DOES transfer" to a newly hired HC. A
Coach row, by contrast, gets a blank-slate JSS history on every new
hire. So this needs its own store, keyed by team_abbr, independent of
who currently holds any coaching job there.

It also needs different lifetimes than a Coach row: persists across
season_state.start_new_season() (an existing franchise's ownership
patience doesn't reset just because a new year started), but resets on
season_state.reset_season() (a brand-new franchise starts every owner
at neutral, same as a fresh league). Same DEFAULT_PATH-resolved-at-
call-time JSON convention as power_rank_history.py / gameplan_store.py
-- a plain per-team dict, not a DB table, since nothing here needs
relational queries.

Schema on disk: {team_abbr: {"base": float, "buffers": [{"kind": str, "value": float}, ...]}}

`base` is the persistent core, updated once per season-end by
apply_season_end()'s annual adjustment (Sec 3.2's table). `buffers` are
recent-success protections (Sec 3.2's "Super Bowl -8 / Conference -5 /
Division -3 / Playoff -1", explicitly described as decaying but with no
rate given anywhere in the spec) -- this module's own documented choice
is to halve each buffer's magnitude at every subsequent season-end,
dropping it once it's negligible. A Super Bowl's -8 is worth -4 the
following year (matching Sec 12 narrative #5's "Super Bowl hangover"
protection), -2 the year after, gone by year 4 if no new success
renews it. `effective_pressure()` is `base + sum(buffer values)`,
clamped to the spec's 20-90 range.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json

DEFAULT_PATH = Path("data/saves/owner_pressure.json")

NEUTRAL_PRESSURE = 50.0
MIN_PRESSURE, MAX_PRESSURE = 20.0, 90.0

# Sec 3.2's annual adjustment table, keyed by the outcome-vs-expectation
# bucket coach_hiring.classify_season_outcome() produces.
ANNUAL_ADJUSTMENT: dict[str, float] = {
    "far_exceeded": -3.0,
    "exceeded": -2.0,
    "met": 0.0,
    "moderately_below": 2.0,
    "significantly_below": 4.0,
    "catastrophic": 6.0,
}

# Sec 3.2's recent-success buffers, granted the season a team achieves
# them (only the single BEST achievement of the season is granted --
# winning the Super Bowl subsumes the lesser tiers, it doesn't stack
# all four).
SUCCESS_BUFFERS: dict[str, float] = {
    "super_bowl": -8.0,
    "conference_title": -5.0,
    "division_title": -3.0,
    "playoff_appearance": -1.0,
}

BUFFER_DECAY = 0.5   # this module's own documented halving-per-season choice
BUFFER_FLOOR = 0.5   # drop a buffer once |value| decays below this


@dataclass
class TeamPressure:
    base: float = NEUTRAL_PRESSURE
    buffers: list[dict] = field(default_factory=list)

    @property
    def effective(self) -> float:
        total = self.base + sum(b["value"] for b in self.buffers)
        return max(MIN_PRESSURE, min(MAX_PRESSURE, total))


_cache: dict[str, TeamPressure] | None = None


def _load() -> dict[str, TeamPressure]:
    global _cache
    if _cache is not None:
        return _cache
    if DEFAULT_PATH.exists():
        raw = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        _cache = {
            abbr: TeamPressure(base=v.get("base", NEUTRAL_PRESSURE), buffers=list(v.get("buffers", [])))
            for abbr, v in raw.items()
        }
    else:
        _cache = {}
    return _cache


def _save() -> None:
    if _cache is None:
        return
    DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = {abbr: {"base": tp.base, "buffers": tp.buffers} for abbr, tp in _cache.items()}
    DEFAULT_PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def clear_cache() -> None:
    """Force the next read to reload from disk -- call after directly
    editing the file (tests) or after reset_all()/apply_season_end() in
    a different process."""
    global _cache
    _cache = None


def pressure_for(team_abbr: str) -> float:
    """Effective OwnerWinPressure (20-90) for one team. Neutral (50) for
    a team never recorded here yet -- every real franchise starts here."""
    return _load().get(team_abbr, TeamPressure()).effective


def reset_all() -> None:
    """season_state.reset_season(): a brand-new franchise starts every
    owner at neutral, same as a fresh league with no history."""
    global _cache
    _cache = {}
    _save()


def apply_season_end(team_abbr: str, outcome_bucket: str, achievement: str | None) -> float:
    """Sec 3.2's once-per-season roll for one team: adjusts `base` by
    the outcome bucket, decays existing buffers, then grants this
    season's own achievement buffer (if any) at full strength -- decay
    runs BEFORE the new grant so a buffer earned this season isn't
    already stale the moment it's created. Returns the new effective
    pressure. `outcome_bucket` must be one of ANNUAL_ADJUSTMENT's keys;
    `achievement` one of SUCCESS_BUFFERS' keys or None."""
    store = _load()
    tp = store.setdefault(team_abbr, TeamPressure())
    tp.base = max(MIN_PRESSURE, min(MAX_PRESSURE, tp.base + ANNUAL_ADJUSTMENT.get(outcome_bucket, 0.0)))

    decayed = []
    for b in tp.buffers:
        new_val = b["value"] * BUFFER_DECAY
        if abs(new_val) >= BUFFER_FLOOR:
            decayed.append({"kind": b["kind"], "value": new_val})
    tp.buffers = decayed

    if achievement in SUCCESS_BUFFERS:
        tp.buffers.append({"kind": achievement, "value": SUCCESS_BUFFERS[achievement]})

    _save()
    return tp.effective


def all_pressures() -> dict[str, float]:
    return {abbr: tp.effective for abbr, tp in _load().items()}


def buffers_for(team_abbr: str) -> list[dict]:
    """This team's current recent-success buffers (kind/value pairs) --
    used by coach_hiring.recent_success_modifier() to tell whether a
    success is still at full (i.e. "within 1 year") strength."""
    tp = _load().get(team_abbr)
    return list(tp.buffers) if tp is not None else []
