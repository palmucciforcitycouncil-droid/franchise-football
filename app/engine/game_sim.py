from dataclasses import dataclass
from typing import List
from .rng import RNG
from .rating import TeamRatings
from .game_state import DriveEvent, GameResult, PlayEvent
from .drive_sim import simulate_drive
from .player_ai import build_matchup_context
from .defensive_ai import LEAGUE_AVG_YPC, LEAGUE_AVG_YPA
from .gameplan import Gameplan
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
    pass_attempts: int = 0
    rush_attempts: int = 0
    turnovers: int = 0

    def ypc(self) -> float:
        return self.rush_yards / self.rush_attempts if self.rush_attempts else LEAGUE_AVG_YPC

    def ypa(self) -> float:
        return self.pass_yards / self.pass_attempts if self.pass_attempts else LEAGUE_AVG_YPA

def simulate_game(
    rng: RNG, home: TeamSim, away: TeamSim,
    home_ep_multiplier: float = 1.0, away_ep_multiplier: float = 1.0,
    home_gameplan: Gameplan | None = None, away_gameplan: Gameplan | None = None,
) -> GameResult:
    """home_ep_multiplier/away_ep_multiplier: the Score Fidelity System's
    (app/engine/score_fidelity.py) per-game scoring nudge, computed from
    Team Power Ratings by whoever has season context (season_state.py).
    Default 1.0 (no effect) for callers with no season -- e.g. the
    standalone single-game simulator (app/main.py's /simulate route),
    which has no Team Power Rating to derive a multiplier from.

    home_gameplan/away_gameplan: the Weekly Gameplan (GDD Sec 10.4.1) for
    whichever of the two is the user's team -- None (the default) for
    every AI team and for the standalone single-game simulator, which
    has no concept of "the user's team" either."""
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
    ctx_home_offense = build_matchup_context(home_off_starters, away_def_starters, home_ep_multiplier)
    ctx_away_offense = build_matchup_context(away_off_starters, home_def_starters, away_ep_multiplier)

    for i in range(drives_total):
        side_home = (i % 2 == 0) == home_first
        off = home if side_home else away
        ctx = ctx_home_offense if side_home else ctx_away_offense

        # rough clock proxy
        drives_left = drives_total - i - 1
        is_two_min = drives_left <= 2
        trailing = (h < a) if side_home else (a < h)
        fourth_ok = (is_two_min or trailing) and off.ratings.aggression >= 0.55

        # In-game offensive performance SO FAR (before this drive) -- the
        # defense's Sec 6.6.3 Step 1 anticipation input. Read from this
        # offense's own running totals, not the defense's -- the defense
        # is reacting to what the offense has actually been doing.
        off_tot = htot if side_home else atot
        offense_gameplan = home_gameplan if side_home else away_gameplan
        defense_gameplan = away_gameplan if side_home else home_gameplan
        pts, txt, field_pos, plays, yards, tos, drive_play_events = simulate_drive(
            rng, ctx, off.ratings, field_pos,
            is_two_minute=is_two_min, trailing=trailing, fourth_down_ok=fourth_ok,
            off_ypc=off_tot.ypc(), off_ypa=off_tot.ypa(),
            offense_gameplan=offense_gameplan, defense_gameplan=defense_gameplan,
        )

        for pe in drive_play_events:
            pe.offense_abbr = off.abbr
            pe.drive_number = i + 1  # 1-based, matches this drive's index in `events` below
        all_plays.extend(drive_play_events)

        pass_yards = sum(pe.yards for pe in drive_play_events if pe.play_type == "pass" and pe.outcome != "turnover")
        rush_yards = sum(pe.yards for pe in drive_play_events if pe.play_type == "run" and pe.outcome != "turnover")
        pass_attempts = sum(1 for pe in drive_play_events if pe.play_type == "pass" and pe.outcome != "sack")
        rush_attempts = sum(1 for pe in drive_play_events if pe.play_type == "run")

        # Safety points belong to the defense, not this drive's offense --
        # simulate_drive() returns pts=0 for a safety and flags it via txt.
        safety_pts = 2 if txt == "Safety" else 0

        if side_home:
            h += pts       # offense (home) scores normally; 0 on a safety
            a += safety_pts  # defense (away) gets the 2 points on a safety
            htot.points += pts; htot.plays += plays; htot.yards += yards; htot.turnovers += tos
            htot.pass_yards += pass_yards; htot.rush_yards += rush_yards
            htot.pass_attempts += pass_attempts; htot.rush_attempts += rush_attempts
        else:
            a += pts
            h += safety_pts
            atot.points += pts; atot.plays += plays; atot.yards += yards; atot.turnovers += tos
            atot.pass_yards += pass_yards; atot.rush_yards += rush_yards
            atot.pass_attempts += pass_attempts; atot.rush_attempts += rush_attempts

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
