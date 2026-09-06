from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import random
import math


# ===== DTOs =====

@dataclass(frozen=True)
class TeamStub:
    id: int
    name: str
    power_rating: int  # 0-100; default mid if missing


@dataclass(frozen=True)
class GameConfigV1:
    seed: int = 42
    home_advantage: int = 2
    pace: float = 1.0           # 1.0 = normal, >1 faster (less clock per play), <1 slower
    drives_cap_per_team: int = 20  # hard cap safety; game is usually clock-limited


@dataclass
class SimResultV1:
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    plays: List[str]   # detailed text incl. quarter/clock/field pos
    total_seconds: int # seconds elapsed (<= 3600)
    finished_by_clock: bool


# ===== Utilities =====

FIELD_GOAL_POST_YARDLINE = 100
HALF_FIELD = 50
GAME_SECONDS = 60 * 60
QUARTER_SECONDS = 15 * 60


def _fmt_clock(seconds_left: int) -> Tuple[int, str]:
    seconds_left = max(0, seconds_left)
    q = 4 - (seconds_left // QUARTER_SECONDS)
    # cap Q at 4, handle 0 properly
    q = min(4, max(1, q))
    sec_in_q = seconds_left % QUARTER_SECONDS
    mm = sec_in_q // 60
    ss = sec_in_q % 60
    return q, f"Q{q} {mm:02d}:{ss:02d}"


def _fmt_pos(yardline: int, offense_is_home: bool) -> str:
    # yardline is 0..100 going toward opponent end zone
    if yardline < HALF_FIELD:
        return f"OWN {yardline}"
    else:
        return f"OPP {FIELD_GOAL_POST_YARDLINE - yardline}"


def _rating_swing(off: int, deff: int) -> float:
    diff = max(-30, min(30, off - deff))
    return diff / 30.0  # -1..+1


def _play_time_secs(rng: random.Random, pace: float) -> int:
    # base 28s +/- 8s, clamped 18..40, adjusted by pace (higher pace -> less time)
    base = 28 + rng.randint(-8, 8)
    base = max(18, min(40, base))
    adj = base / max(0.5, min(2.0, pace))
    return int(round(adj))


def _yard_gain(rng: random.Random, swing: float, to_go: int) -> int:
    # base gain ~ 3.5y, swing adds +/- 2y, situational tweak for short to-go
    mu = 3.5 + 2.0 * swing + (1.0 if to_go <= 2 else 0.0)
    # add randomness; prevent wild extremes
    gain = rng.gauss(mu, 4.0)
    # allow occasional chunk plays but clamp
    gain = max(-10.0, min(45.0, gain))
    return int(round(gain))


def _fg_make_prob(kick_distance: int) -> float:
    # very rough model: 25yd ~ 92%, 45yd ~ 75%, 55yd ~ 50%, 60yd ~ 35%
    # clamp to [0.1, 0.98]
    p = 1.06 - 0.014 * kick_distance
    return max(0.10, min(0.98, p))


def _turnover_happens(rng: random.Random, swing: float) -> Tuple[bool, str]:
    # base ~3%, worse offense vs defense increases risk up to ~9%
    p = 0.03 + 0.03 * max(0.0, -swing)
    if rng.random() < p:
        return True, ("Interception" if rng.random() < 0.6 else "Fumble")
    return False, ""


# ===== Drive simulation with downs/clock/field position =====

def _simulate_drive(
    rng: random.Random,
    off_name: str,
    def_name: str,
    off_power: int,
    def_power: int,
    start_yardline: int,
    seconds_left: int,
    pace: float,
) -> Tuple[int, int, List[str], int]:
    """
    Returns: points_scored, new_seconds_left, play_lines, end_yardline (for logging only)
    """
    lines: List[str] = []
    yardline = start_yardline  # 0..100 toward opponent EZ
    down = 1
    to_go = 10
    points = 0

    swing = _rating_swing(off_power, def_power)

    # estimate a typical drive has up to ~12 plays; stop early if clock runs out
    plays_this_drive = 0
    while seconds_left > 0 and plays_this_drive < 20:
        q, clk = _fmt_clock(seconds_left)
        pos = _fmt_pos(yardline, True)

        # Try a play
        # Turnover check first (rare)
        tov, tov_type = _turnover_happens(rng, swing)
        if tov:
            secs = _play_time_secs(rng, pace)
            seconds_left -= secs
            lines.append(f"{clk} {off_name} {down}&{to_go} at {pos}: {tov_type}! Drive ends.")
            break

        gain = _yard_gain(rng, swing, to_go)
        secs = _play_time_secs(rng, pace)
        seconds_left -= secs

        new_yl = max(0, min(100, yardline + gain))

        # Touchdown?
        if new_yl >= 100:
            points += 7
            lines.append(f"{clk} {off_name} {down}&{to_go} at {pos}: +{max(0,gain)}y — TOUCHDOWN. (+7)")
            break

        # Update downs/yardline
        if gain >= to_go:
            # First down
            yardline = new_yl
            to_go = 10 if yardline <= 90 else (100 - yardline)
            down = 1
            lines.append(f"{clk} {off_name} {down}st down at {_fmt_pos(yardline, True)} after {gain}y")
        else:
            yardline = new_yl
            to_go = max(1, to_go - max(0, gain))
            down += 1
            if down <= 3:
                suffix = {2: "2nd", 3: "3rd"}[down]
                lines.append(f"{clk} {off_name} {suffix}&{to_go} at {_fmt_pos(yardline, True)} (gain {gain}y)")
            else:
                # 4th down decision: punt or field goal
                # compute kick distance if FG: uprights are 10y deep, add 17 for placement
                kick_dist = (100 - yardline) + 17
                in_fg_range = kick_dist <= 60  # try up to 60 yards
                # prefer FG if decent chance and we're inside ~OPP 40
                if in_fg_range and yardline >= 60:
                    make_p = _fg_make_prob(kick_dist)
                    made = rng.random() < make_p
                    if made:
                        points += 3
                        lines.append(f"{clk} {off_name} 4th&{to_go} at {_fmt_pos(yardline, True)}: FG {kick_dist} is GOOD. (+3)")
                    else:
                        lines.append(f"{clk} {off_name} 4th&{to_go} at {_fmt_pos(yardline, True)}: FG {kick_dist} is NO GOOD.")
                    break
                else:
                    # Punt: net ~40 +/- 7, but clamp to leave ball at least at OPP 20 if close
                    net = int(round(40 + rng.gauss(0, 7)))
                    net = max(25, min(55, net))
                    # punt target yardline from offense perspective
                    punt_to = max(0, yardline - net)
                    lines.append(f"{clk} {off_name} 4th&{to_go} at {_fmt_pos(yardline, True)}: Punt to { _fmt_pos(punt_to, True) }. Drive ends.")
                    break

        plays_this_drive += 1

    end_yardline = yardline
    return points, max(0, seconds_left), lines, end_yardline


# ===== Public Game simulation =====

def simulate_game_v1(home: TeamStub, away: TeamStub, cfg: GameConfigV1) -> SimResultV1:
    """
    Deterministic game sim with:
      - Field position (OWN/OPP yard markers)
      - Downs & distance
      - Possession clock per play and quarter/clock display
      - FG attempts and punts on 4th down
      - Simple turnover model

    Alternate possessions: AWAY receives first (common), then HOME, etc.
    Clock starts at 60:00 and runs down. Game can end by clock or when hitting
    a drive cap safety (should be clock in practice).
    """
    rng = random.Random(cfg.seed)

    home_pow = (home.power_rating if home.power_rating is not None else 50) + cfg.home_advantage
    away_pow = away.power_rating if away.power_rating is not None else 50

    seconds_left = GAME_SECONDS
    plays: List[str] = []
    home_score = 0
    away_score = 0

    # start every drive at own 25 (touchbacks); this keeps kickoff logic simple
    start_yl = 25

    total_drives = 0
    while seconds_left > 0 and total_drives < cfg.drives_cap_per_team * 2:
        offense_is_home = (total_drives % 2 == 1)  # away starts (0)
        if offense_is_home:
            q, clk = _fmt_clock(seconds_left)
            plays.append(f"{clk} {home.name} ball — starts at OWN {start_yl}")
            pts, seconds_left, drive_lines, end_yl = _simulate_drive(
                rng, home.name, away.name, home_pow, away_pow, start_yl, seconds_left, cfg.pace
            )
            home_score += pts
            plays.extend(drive_lines)
        else:
            q, clk = _fmt_clock(seconds_left)
            plays.append(f"{clk} {away.name} ball — starts at OWN {start_yl}")
            pts, seconds_left, drive_lines, end_yl = _simulate_drive(
                rng, away.name, home.name, away_pow, home_pow, start_yl, seconds_left, cfg.pace
            )
            away_score += pts
            plays.extend(drive_lines)

        total_drives += 1

    plays.append(f"FINAL — {away.name} {away_score} @ {home.name} {home_score}")
    return SimResultV1(
        home_team_id=home.id,
        away_team_id=away.id,
        home_score=home_score,
        away_score=away_score,
        plays=plays,
        total_seconds=(GAME_SECONDS - seconds_left),
        finished_by_clock=(seconds_left == 0),
    )
