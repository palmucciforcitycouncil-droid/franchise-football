from dataclasses import dataclass
from typing import List
from .rng import RNG
from .rating import TeamRatings
from .game_state import DriveEvent, GameResult, PlayEvent
from .drive_sim import simulate_drive
from .player_ai import build_matchup_context
from app.services.depth_chart import get_offensive_starters, get_defensive_starters

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
    all_plays: List[PlayEvent] = []
    h = a = 0
    htot = TeamTotals(); atot = TeamTotals()

    # Real starters + matchup composites, built once per game (not per
    # drive -- starters don't change mid-game) for both directions of play.
    home_off_starters = get_offensive_starters(home.abbr)
    home_def_starters = get_defensive_starters(home.abbr)
    away_off_starters = get_offensive_starters(away.abbr)
    away_def_starters = get_defensive_starters(away.abbr)
    ctx_home_offense = build_matchup_context(home_off_starters, away_def_starters)
    ctx_away_offense = build_matchup_context(away_off_starters, home_def_starters)

    for i in range(drives_total):
        side_home = (i % 2 == 0) == home_first
        off = home if side_home else away
        ctx = ctx_home_offense if side_home else ctx_away_offense

        # rough clock proxy
        drives_left = drives_total - i - 1
        is_two_min = drives_left <= 2
        trailing = (h < a) if side_home else (a < h)
        fourth_ok = (is_two_min or trailing) and off.ratings.aggression >= 0.55

        pts, txt, field_pos, plays, yards, tos, drive_play_events = simulate_drive(
            rng, ctx, off.ratings, field_pos,
            is_two_minute=is_two_min, trailing=trailing, fourth_down_ok=fourth_ok
        )

        for pe in drive_play_events:
            pe.offense_abbr = off.abbr
        all_plays.extend(drive_play_events)

        pass_yards = sum(pe.yards for pe in drive_play_events if pe.play_type == "pass" and pe.outcome != "turnover")
        rush_yards = sum(pe.yards for pe in drive_play_events if pe.play_type == "run" and pe.outcome != "turnover")

        # Safety points belong to the defense, not this drive's offense --
        # simulate_drive() returns pts=0 for a safety and flags it via txt.
        safety_pts = 2 if txt == "Safety" else 0

        if side_home:
            h += pts       # offense (home) scores normally; 0 on a safety
            a += safety_pts  # defense (away) gets the 2 points on a safety
            htot.points += pts; htot.plays += plays; htot.yards += yards; htot.turnovers += tos
            htot.pass_yards += pass_yards; htot.rush_yards += rush_yards
        else:
            a += pts
            h += safety_pts
            atot.points += pts; atot.plays += plays; atot.yards += yards; atot.turnovers += tos
            atot.pass_yards += pass_yards; atot.rush_yards += rush_yards

        events.append(DriveEvent(
            desc=f"{off.abbr} {txt}",
            clock_left=max(0, drives_left * 180),
            home_score=h, away_score=a
        ))

    winner = "home" if h >= a else "away"
    res = GameResult(home_score=h, away_score=a, winner=winner, events=events, plays=all_plays)
    res.home_totals = htot  # type: ignore[attr-defined]
    res.away_totals = atot  # type: ignore[attr-defined]
    return res
