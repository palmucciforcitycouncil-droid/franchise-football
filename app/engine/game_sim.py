from dataclasses import dataclass
from typing import List
from .rng import RNG
from .rating import TeamRatings
from .game_state import DriveEvent, GameResult
from .drive_sim import simulate_drive

@dataclass
class TeamSim:
    name: str
    abbr: str
    ratings: TeamRatings

@dataclass
class TeamTotals:
    points: int = 0
    plays: int = 0
    yards: int = 0
    pass_yards: int = 0
    rush_yards: int = 0
    turnovers: int = 0

def simulate_game(rng: RNG, home: TeamSim, away: TeamSim) -> GameResult:
    drives_total = int((home.ratings.pace_drives() + away.ratings.pace_drives()) / 2)
    home_first = rng.prob(0.5)
    field_pos = 65
    events: List[DriveEvent] = []
    h = a = 0
    htot = TeamTotals(); atot = TeamTotals()

    for i in range(drives_total):
        side_home = (i % 2 == 0) == home_first
        off = home if side_home else away
        defn = away if side_home else home

        # rough clock proxy
        drives_left = drives_total - i - 1
        is_two_min = drives_left <= 2
        trailing = (h < a) if side_home else (a < h)
        fourth_ok = (is_two_min or trailing) and off.ratings.aggression >= 0.55

        pts, txt, field_pos, plays, yards, tos = simulate_drive(
            rng, off.ratings, defn.ratings, field_pos,
            is_two_minute=is_two_min, trailing=trailing, fourth_down_ok=fourth_ok
        )
        if side_home:
            h += pts
            htot.points += pts; htot.plays += plays; htot.yards += yards; htot.turnovers += tos
            py = int((1 - off.ratings.run_bias) * max(0, yards))
            htot.pass_yards += py; htot.rush_yards += max(0, yards - py)
        else:
            a += pts
            atot.points += pts; atot.plays += plays; atot.yards += yards; atot.turnovers += tos
            py = int((1 - off.ratings.run_bias) * max(0, yards))
            atot.pass_yards += py; atot.rush_yards += max(0, yards - py)

        events.append(DriveEvent(
            desc=f"{off.abbr} {txt}",
            clock_left=max(0, drives_left * 180),
            home_score=h, away_score=a
        ))

    winner = "home" if h >= a else "away"
    res = GameResult(home_score=h, away_score=a, winner=winner, events=events)
    res.home_totals = htot  # type: ignore[attr-defined]
    res.away_totals = atot  # type: ignore[attr-defined]
    return res
