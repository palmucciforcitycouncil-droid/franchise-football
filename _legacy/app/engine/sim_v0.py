from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import random

# ---- Data structures (DTOs) ----

@dataclass(frozen=True)
class TeamStub:
    id: int
    name: str
    power_rating: int  # 0-100; default mid if missing


@dataclass(frozen=True)
class GameConfig:
    seed: int = 42
    drives_per_team: int = 10   # MVP: fixed number of drives each
    home_advantage: int = 2     # bump to home power
    pace: float = 1.0           # reserved, not used in v0
    aggression: float = 1.0     # reserved, not used in v0
    pass_bias: float = 0.5      # reserved, not used in v0


@dataclass
class SimResult:
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    plays: List[str]  # text play-by-play (drive summaries in v0)
    drives: int


# ---- Pure simulation helpers ----

def _rating(off: int, defn: int) -> float:
    """
    Convert offense/defense power ratings (0-100-ish) into an expected points
    modifier. In v0 we just normalize the difference to a small scalar.
    """
    diff = max(-30, min(30, (off - defn)))  # clamp to +/-30 to avoid extremes
    # ~3.0 points swing at max difference across the game
    return diff / 30.0


def _drive_points(rng: random.Random, off_rating: int, def_rating: int) -> Tuple[int, str]:
    """
    Simulate a single drive. Return (points_scored, summary_text).

    Extremely simple outcome model:
      - base scores: {TD: 7, FG: 3, None: 0}
      - probabilities shifted by _rating(off, def)
    """
    swing = _rating(off_rating, def_rating)  # -1..+1
    # Base probabilities (approximate NFL drive outcome)
    p_td = 0.22 + 0.10 * swing     # 12%..32%
    p_fg = 0.17 + 0.07 * swing     # 10%..24%
    p_to = 0.12 - 0.06 * swing     # 6%..18% turnovers modeled in "no score"
    # Sanity: keep probabilities in [0,1] and sum<=1
    p_td = max(0.05, min(0.50, p_td))
    p_fg = max(0.05, min(0.40, p_fg))
    # residual is punt/turnover on downs/TO/clock
    roll = rng.random()
    if roll < p_td:
        return 7, "Touchdown drive"
    elif roll < p_td + p_fg:
        return 3, "Field goal drive"
    else:
        # small chance to log a turnover flavor
        if rng.random() < (0.30 + 0.20 * max(0.0, p_to)):
            return 0, "Drive ends on turnover"
        return 0, "Drive stalls and punts"


# ---- Public API ----

def simulate_game(home: TeamStub, away: TeamStub, cfg: GameConfig) -> SimResult:
    """
    Seedable, deterministic (given inputs) drive-based sim. Returns text output.

    Rules v0:
      - Each team gets cfg.drives_per_team drives, alternating starting with AWAY.
      - Home team power gets +cfg.home_advantage.
      - No clock model, penalties, special teams nuance, etc. (MVP).
    """
    # seed
    rng = random.Random(cfg.seed)

    # effective ratings
    home_pow = (home.power_rating if home.power_rating is not None else 50) + cfg.home_advantage
    away_pow = away.power_rating if away.power_rating is not None else 50

    # Alternate possessions, AWAY starts (common NFL pattern)
    total_drives = cfg.drives_per_team * 2
    plays: List[str] = []
    home_score = 0
    away_score = 0

    for i in range(total_drives):
        offense_is_home = (i % 2 == 1)  # away starts (i=0)
        if offense_is_home:
            pts, text = _drive_points(rng, home_pow, away_pow)
            home_score += pts
            plays.append(f"Drive {i+1}: {home.name} — {text} (+{pts})")
        else:
            pts, text = _drive_points(rng, away_pow, home_pow)
            away_score += pts
            plays.append(f"Drive {i+1}: {away.name} — {text} (+{pts})")

    plays.append(f"FINAL — {away.name} {away_score} @ {home.name} {home_score}")
    return SimResult(
        home_team_id=home.id,
        away_team_id=away.id,
        home_score=home_score,
        away_score=away_score,
        plays=plays,
        drives=total_drives,
    )
