# app/services/progression.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional, Callable
from time import time
import math
import random

from sqlmodel import Session, select, delete

from app.models.core_min import Player
from app.models.stats_models import PlayerSeasonStats
from app.models.awards import AwardResult
from app.models.progression import PlayerProgression

# ----------------------------
# Tunable constants (documented, GDD v3.2 aligned)
# ----------------------------

# Peak age bands by bucket
AGE_PEAKS: Dict[str, Tuple[int, int]] = {
    "QB": (28, 32),
    "RB": (24, 27),
    "WR": (25, 28),
    "TE": (25, 29),
    "OL": (26, 30),
    "DL": (25, 29),
    "LB": (25, 29),
    "DB": (24, 28),
    "K":  (30, 34),
    "P":  (30, 34),
}

# Per-season clamp on attribute change
DELTA_MIN = -6
DELTA_MAX = +6

# Absolute rating bounds
RATING_MIN = 30
RATING_MAX = 99

# Awards additive bonuses (applied to a composite perf delta before attribute mapping)
AWARD_BONUS = {
    "MVP":  +2.0,
    "OPOY": +1.5,
    "DPOY": +1.5,
    "ROY":  +1.0,
}

# Injury drag factors
INJURY_MISSED_GM_DRAG = 0.15   # -15% per missed game influence on positive growth
HIGH_INJURY_PRONENESS_DRAG = 0.20  # -20% if injury_proneness >= 80

# Usage (snaps) scaling
USAGE_LOW_SNAP_CEILING = 0.6   # cap positive change when snaps are below league median
USAGE_HIGH_SNAP_MULT = 1.15    # boost positive change modestly for heavy usage

# Potential scaling: center 50 means neutral, <50 dampens, >50 amplifies
def potential_multiplier(potential: int) -> float:
    p = max(0, min(100, potential))
    return 0.6 + (p / 100.0)  # 0.6 .. 1.6

# ----------------------------
# Utility: position bucket
# ----------------------------
def _bucket(pos: str) -> str:
    pos = (pos or "").upper()
    if pos in AGE_PEAKS:
        return pos
    # map unknowns heuristically
    if pos in {"FB", "HB"}:
        return "RB"
    if pos in {"C", "G", "T"}:
        return "OL"
    if pos in {"DE", "DT", "NT"}:
        return "DL"
    if pos in {"CB", "S"}:
        return "DB"
    return "WR"

# ----------------------------
# Compute age curve multiplier (growth/regression)
# ----------------------------
def age_multiplier(position: str, age: int) -> float:
    b = _bucket(position)
    low, high = AGE_PEAKS.get(b, (26, 29))
    if age < low:
        # younger than peak → gentle growth up to +10% approaching peak
        gap = low - age
        return 1.0 + min(0.10, 0.03 * gap)
    if low <= age <= high:
        return 1.0
    # older than peak → regression growing with distance; up to -20%
    gap = age - high
    return max(0.80, 1.0 - 0.04 * gap)

# ----------------------------
# Performance composite by position bucket
# Uses PlayerSeasonStats; robust to missing fields via getattr.
# Returns a signed "performance_delta" roughly in [-3, +3] before scaling.
# ----------------------------
def performance_delta_for(pss: PlayerSeasonStats, position: str) -> float:
    pos = _bucket(position)
    # Offense aggregates
    off_y = getattr(pss, "pass_yards", 0) + getattr(pss, "rush_yards", 0) + getattr(pss, "receiving_yards", 0)
    off_td = getattr(pss, "pass_touchdowns", 0) + getattr(pss, "rush_touchdowns", 0) + getattr(pss, "receiving_touchdowns", 0)
    to = getattr(pss, "interceptions", 0) + getattr(pss, "fumbles", 0)

    # Defense aggregates
    df_tk = getattr(pss, "tackles", 0)
    df_sk = getattr(pss, "sacks", 0.0)
    df_int = getattr(pss, "interceptions_caught", 0)
    df_pd = getattr(pss, "pass_deflections", 0)

    if pos == "QB":
        core = off_y * 0.0012 + off_td * 0.6 - to * 0.9
    elif pos in {"RB"}:
        core = (getattr(pss, "rush_yards", 0) * 0.0020 + getattr(pss, "rush_touchdowns", 0) * 0.7
                + getattr(pss, "receptions", 0) * 0.1 - to * 0.4)
    elif pos in {"WR", "TE"}:
        core = (getattr(pss, "receiving_yards", 0) * 0.0016 + getattr(pss, "receiving_touchdowns", 0) * 0.8
                + getattr(pss, "receptions", 0) * 0.05 - to * 0.4)
    elif pos in {"OL"}:
        # Proxy via team plays and sacks allowed are at team level; use snaps as usage proxy
        total_snaps = getattr(pss, "snaps_offense", 0) + getattr(pss, "snaps_defense", 0) + getattr(pss, "snaps_special_teams", 0)
        core = total_snaps * 0.002 - getattr(pss, "sacks", 0) * 0.2
    elif pos in {"DL", "LB"}:
        core = df_tk * 0.08 + float(df_sk) * 1.5 + df_int * 2.0
    elif pos in {"DB"}:
        core = df_tk * 0.05 + df_int * 2.5 + df_pd * 0.3
    else:
        core = off_y * 0.001 + off_td * 0.5 - to * 0.5

    # Squash to ~[-3, +3]
    return max(-3.0, min(3.0, core / 10.0))

# ----------------------------
# Awards bonus lookup
# ----------------------------
def awards_bonus(session: Session, season: int, player_id: int) -> float:
    rows = session.exec(select(AwardResult).where(AwardResult.season == season, AwardResult.player_id == player_id)).all()
    bonus = 0.0
    for r in rows:
        bonus += AWARD_BONUS.get(r.award, 0.0)
    return bonus

# ----------------------------
# Injury drag computation
# ----------------------------
def injury_drag(pss: PlayerSeasonStats, injury_proneness: int) -> float:
    games = max(1, getattr(pss, "games_played", 0))
    # If PlayerSeasonStats doesn't store games, estimate from snaps; treat 60 snaps ~ 1 game
    if games == 0:
        total_snaps = getattr(pss, "snaps_offense", 0) + getattr(pss, "snaps_defense", 0) + getattr(pss, "snaps_special_teams", 0)
        games = max(1, total_snaps // 60)
    played = games  # assume they counted played games; missed = 0 if unknown
    missed = max(0, 17 - played)  # NFL-style baseline
    drag = 1.0
    if missed > 0:
        drag *= max(0.0, 1.0 - INJURY_MISSED_GM_DRAG * missed)
    if injury_proneness >= 80:
        drag *= (1.0 - HIGH_INJURY_PRONENESS_DRAG)
    return drag

# ----------------------------
# Usage multiplier
# ----------------------------
def usage_multiplier(pss: PlayerSeasonStats, league_median_snaps: int) -> float:
    total_snaps = getattr(pss, "snaps_offense", 0) + getattr(pss, "snaps_defense", 0) + getattr(pss, "snaps_special_teams", 0)
    if total_snaps <= 0:
        return USAGE_LOW_SNAP_CEILING
    if total_snaps < league_median_snaps:
        # scale between ceiling and 1.0 as snaps approach median
        frac = max(0.0, min(1.0, total_snaps / max(1, league_median_snaps)))
        return USAGE_LOW_SNAP_CEILING + (1.0 - USAGE_LOW_SNAP_CEILING) * frac
    # modest boost for heavy usage
    return USAGE_HIGH_SNAP_MULT

# ----------------------------
# Attribute mapping per position bucket
# Map a scalar delta (signed) to individual attribute adjustments.
# ----------------------------
def map_delta_to_attributes(pos_bucket: str, base_delta: float) -> Dict[str, int]:
    # Convert a float delta into discrete rating changes per attribute.
    # We bias attributes that matter most for a bucket.
    d = int(round(base_delta))
    if d == 0:
        return {}
    if pos_bucket == "QB":
        return {"awareness": d, "throw_accuracy": d, "throw_power": max(-1, min(1, d))}
    if pos_bucket == "RB":
        return {"agility": d, "speed": d, "awareness": max(-1, d-1)}
    if pos_bucket in {"WR", "TE"}:
        return {"catching": d, "agility": d, "speed": max(-1, min(1, d))}
    if pos_bucket == "OL":
        return {"strength": d, "awareness": d}
    if pos_bucket in {"DL", "LB"}:
        return {"tackling": d, "strength": d, "awareness": max(-1, min(1, d))}
    if pos_bucket == "DB":
        return {"agility": d, "awareness": d, "catching": max(-1, min(1, d))}
    if pos_bucket in {"K", "P"}:
        return {"awareness": d}
    return {"awareness": d}

# ----------------------------
# Clamp utility
# ----------------------------
def clamp_rating(v: int) -> int:
    return max(RATING_MIN, min(RATING_MAX, v))

def clamp_delta(d: int) -> int:
    return max(DELTA_MIN, min(DELTA_MAX, d))

# ----------------------------
# Orchestrator
# ----------------------------
def apply_progression_for_season(session: Session, season: int, seed: int = 2025, force: bool = False) -> None:
    """
    Compute and persist progression for all players present in PlayerSeasonStats for given season.
    Idempotent unless force=True. Updates Player attributes after writing audit row.
    """
    rng = random.Random(seed)

    # Load all PlayerSeasonStats for season
    pss_rows: List[PlayerSeasonStats] = session.exec(
        select(PlayerSeasonStats).where(PlayerSeasonStats.season == season)
    ).all()
    if not pss_rows:
        return

    # League median snaps for usage scaling
    snaps_list = []
    for r in pss_rows:
        total_snaps = getattr(r, "snaps_offense", 0) + getattr(r, "snaps_defense", 0) + getattr(r, "snaps_special_teams", 0)
        snaps_list.append(total_snaps)
    snaps_list.sort()
    league_median_snaps = snaps_list[len(snaps_list)//2] if snaps_list else 0

    # Build quick index
    pss_by_pid: Dict[int, PlayerSeasonStats] = {r.player_id: r for r in pss_rows}

    for pid, r in pss_by_pid.items():
        # idempotency check
        existing = session.exec(select(PlayerProgression).where(
            PlayerProgression.player_id == pid, PlayerProgression.season == season
        )).first()
        if existing and not force:
            continue

        p: Optional[Player] = session.get(Player, pid)
        if not p:
            continue

        pos = getattr(p, "position", getattr(p, "pos", ""))
        pos_bucket = _bucket(pos)
        pot = int(getattr(p, "potential", 50))
        age = int(getattr(p, "age", 26))
        inj_prone = int(getattr(p, "injury_proneness", 50))

        # Base performance delta
        perf = performance_delta_for(r, pos_bucket)

        # Deterministic tiny noise to avoid mass ties (±0.25)
        noise = (rng.random() - 0.5) * 0.5

        # Combine components
        delta = perf
        delta += awards_bonus(session, season, pid)
        delta *= potential_multiplier(pot)
        delta *= age_multiplier(pos_bucket, age)
        delta *= usage_multiplier(r, league_median_snaps)
        delta *= injury_drag(r, inj_prone)
        delta += noise

        # Map to attributes
        attr_map = map_delta_to_attributes(pos_bucket, delta)
        # Include tiny morale/stamina drift
        stamina_d = int(round(max(-1.0, min(1.0, delta * 0.2))))
        morale_d = int(round(max(-1.0, min(1.0, delta * 0.1))))
        if stamina_d:
            attr_map["stamina"] = attr_map.get("stamina", 0) + stamina_d
        if morale_d:
            attr_map["morale"] = attr_map.get("morale", 0) + morale_d

        # Snapshot before
        before = _snapshot_player_ratings(p)

        # Apply clamped deltas
        for k, v in attr_map.items():
            if hasattr(p, k):
                cur = int(getattr(p, k))
                nd = clamp_delta(v)
                setattr(p, k, clamp_rating(cur + nd))

        # Snapshot after
        after = _snapshot_player_ratings(p)

        # Persist audit row (delete if force)
        if existing and force:
            session.delete(existing)

        session.add(PlayerProgression(
            player_id=pid,
            season=season,
            before_json=PlayerProgression.as_json(before),
            after_json=PlayerProgression.as_json(after),
            components_json=PlayerProgression.as_json({
                "pos_bucket": pos_bucket,
                "perf": perf,
                "awards_bonus": awards_bonus(session, season, pid),
                "potential_mult": potential_multiplier(pot),
                "age_mult": age_multiplier(pos_bucket, age),
                "usage_mult": usage_multiplier(r, league_median_snaps),
                "injury_drag": injury_drag(r, inj_prone),
                "noise": noise,
                "applied_attr_map_raw": attr_map,
            }),
            applied_at_ts=int(time()),
            seed_used=seed,
        ))

    session.commit()

# ----------------------------
# Helpers
# ----------------------------
def _snapshot_player_ratings(p: Player) -> Dict[str, int]:
    keys = [
        "awareness","speed","strength","agility",
        "throw_power","throw_accuracy","catching","tackling",
        "stamina","morale"
    ]
    snap: Dict[str, int] = {}
    for k in keys:
        if hasattr(p, k):
            snap[k] = int(getattr(p, k))
    return snap
