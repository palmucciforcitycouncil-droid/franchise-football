"""
Scouting: Next Opponent (GDD Part 1 Sec 10.4.1) -- a report on the
user's team's upcoming opponent, built entirely from real PlayEvents
this season has actually logged, not fabricated placeholder numbers.

Deliberate scope cuts, since the underlying systems don't exist yet:
- No pass-depth (quick/standard/deep) split or target-distribution
  breakdown -- PlayEvent has no depth-of-target or receiver-rank field.
- No return-game averages -- the special-teams engine (drive_sim.py's
  _punt_result) computes a net field position, not a tracked return
  yardage stat.
- No weather forecast -- no weather system exists yet (GDD Sec 6.11 /
  Part 2, an existing documented Known Gap).
Everything else here (situational run/pass splits, red zone tendencies,
blitz/coverage rates, 4th-down aggressiveness, field-goal accuracy by
distance, discipline, season stats, turnover differential) is computed
for real from this season's actual games -- if a number looks specific,
it's because it was actually counted, not estimated.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

OFFENSIVE_PENALTY_TYPES = {"False start", "Delay of game", "Illegal formation", "Holding"}
DEFENSIVE_PENALTY_TYPES = {"Offside", "Defensive pass interference", "Roughing the passer"}

_FG_YARDS_RE = re.compile(r"^(\d+)-yard field goal")


def _pct(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 1) if denominator else None


def find_next_opponent(season, team_abbr: str) -> tuple[str, bool] | None:
    """Scans forward from season.current_week (skipping over a bye week
    if team_abbr doesn't play that week) for team_abbr's next unplayed
    game. Returns (opponent_abbr, team_is_home), or None if the season
    is over or team_abbr has no games left."""
    for week in season.schedule[season.current_week - 1:]:
        for g in week:
            if g.result is not None:
                continue
            if g.home_abbr == team_abbr:
                return g.away_abbr, True
            if g.away_abbr == team_abbr:
                return g.home_abbr, False
    return None


def _played_games(season, team_abbr: str) -> list[tuple[object, bool]]:
    """(WeekGame, team_is_home) for every game team_abbr has actually
    played this season, in week order."""
    out = []
    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            if g.home_abbr == team_abbr:
                out.append((g, True))
            elif g.away_abbr == team_abbr:
                out.append((g, False))
    return out


def _offensive_plays(season, team_abbr: str):
    """team_abbr's own run/pass plays across every game it's played."""
    return [
        p
        for g, _ in _played_games(season, team_abbr)
        for p in g.result.plays
        if p.offense_abbr == team_abbr and p.play_type in ("run", "pass")
    ]


def _defensive_plays(season, team_abbr: str):
    """Run/pass plays where team_abbr was ON DEFENSE (the opponent had the ball)."""
    plays = []
    for g, is_home in _played_games(season, team_abbr):
        opponent = g.away_abbr if is_home else g.home_abbr
        plays.extend(p for p in g.result.plays if p.offense_abbr == opponent and p.play_type in ("run", "pass"))
    return plays


def _pass_pct(plays) -> float | None:
    return _pct(sum(1 for p in plays if p.play_type == "pass"), len(plays))


def situational_offense(season, team_abbr: str) -> dict:
    plays = _offensive_plays(season, team_abbr)
    first_down = [p for p in plays if p.down == 1]
    third_short = [p for p in plays if p.down == 3 and p.distance <= 3]
    third_medium = [p for p in plays if p.down == 3 and 4 <= p.distance <= 7]
    third_long = [p for p in plays if p.down == 3 and p.distance >= 8]
    red_zone = [p for p in plays if p.field_pos >= 80]
    return {
        "sample_size": len(plays),
        "first_down_pass_pct": _pass_pct(first_down),
        "third_short_pass_pct": _pass_pct(third_short),
        "third_medium_pass_pct": _pass_pct(third_medium),
        "third_long_pass_pct": _pass_pct(third_long),
        "redzone_pass_pct": _pass_pct(red_zone),
    }


def _defcall_parts(defensive_call: str) -> list[str]:
    return [s.strip() for s in defensive_call.split(",")]


def situational_defense(season, team_abbr: str) -> dict:
    plays = [p for p in _defensive_plays(season, team_abbr) if p.defensive_call]
    red_zone = [p for p in plays if p.field_pos >= 80]

    def blitz_pct(group):
        return _pct(sum(1 for p in group if any(part.startswith("Blitz") for part in _defcall_parts(p.defensive_call))), len(group))

    def man_pct(group):
        return _pct(sum(1 for p in group if "Man" in _defcall_parts(p.defensive_call)), len(group))

    return {
        "sample_size": len(plays),
        "blitz_pct": blitz_pct(plays),
        "man_pct": man_pct(plays),
        "redzone_blitz_pct": blitz_pct(red_zone),
    }


def fourth_down_aggressiveness(season, team_abbr: str) -> dict:
    attempts = [p for p in _offensive_plays(season, team_abbr) if p.down == 4]
    conversions = [p for p in attempts if p.outcome in ("first_down", "touchdown")]
    return {"attempts": len(attempts), "conversions": len(conversions)}


def field_goal_accuracy(season, team_abbr: str) -> dict:
    """Make/attempt counts by distance bucket, parsed from the real
    field_goal PlayEvents' desc text (the yard distance isn't stored in
    a structured field -- see drive_sim.py's _attempt_field_goal)."""
    buckets = {"<30": [0, 0], "30-39": [0, 0], "40-49": [0, 0], "50+": [0, 0]}  # [made, attempted]
    for g, _ in _played_games(season, team_abbr):
        for p in g.result.plays:
            if p.play_type != "field_goal" or p.offense_abbr != team_abbr:
                continue
            m = _FG_YARDS_RE.match(p.desc)
            if not m:
                continue
            yards = int(m.group(1))
            bucket = "<30" if yards < 30 else "30-39" if yards < 40 else "40-49" if yards < 50 else "50+"
            buckets[bucket][1] += 1
            if p.outcome == "field_goal":
                buckets[bucket][0] += 1
    return {b: {"made": made, "attempted": att, "pct": _pct(made, att)} for b, (made, att) in buckets.items()}


def penalty_discipline(season, team_abbr: str) -> dict:
    """Penalties actually COMMITTED by team_abbr: pre-snap offense/
    holding penalties count when team_abbr was on offense that play;
    offside/DPI/roughing count when team_abbr was on defense (i.e. the
    play's offense_abbr is the opponent). Penalty type is parsed from
    the real desc text's leading phrase -- every penalty desc in
    drive_sim.py starts with a clean "Type, ..." format."""
    games = _played_games(season, team_abbr)
    counts: dict[str, int] = {}
    for g, is_home in games:
        opponent = g.away_abbr if is_home else g.home_abbr
        for p in g.result.plays:
            if p.play_type != "penalty":
                continue
            ptype = p.desc.split(",")[0]
            if ptype in OFFENSIVE_PENALTY_TYPES and p.offense_abbr == team_abbr:
                counts[ptype] = counts.get(ptype, 0) + 1
            elif ptype in DEFENSIVE_PENALTY_TYPES and p.offense_abbr == opponent:
                counts[ptype] = counts.get(ptype, 0) + 1
    total = sum(counts.values())
    per_game = round(total / len(games), 1) if games else None
    top_types = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
    return {"per_game": per_game, "total": total, "top_types": top_types}


@dataclass
class RecentGame:
    won: bool
    my_score: int
    opp_score: int
    opponent: str
    at: str  # "vs" or "@"


def team_summary(season, team_abbr: str) -> dict:
    record = season.records[team_abbr]
    games = _played_games(season, team_abbr)

    recent: list[RecentGame] = []
    total_pass_yards = total_rush_yards = 0
    turnovers_committed = turnovers_forced = 0
    for g, is_home in games:
        my_score = g.result.home_score if is_home else g.result.away_score
        opp_score = g.result.away_score if is_home else g.result.home_score
        opponent = g.away_abbr if is_home else g.home_abbr
        won = (g.result.winner == "home") == is_home
        recent.append(RecentGame(won=won, my_score=my_score, opp_score=opp_score,
                                  opponent=opponent, at="vs" if is_home else "@"))
        my_tot = g.result.home_totals if is_home else g.result.away_totals
        opp_tot = g.result.away_totals if is_home else g.result.home_totals
        total_pass_yards += my_tot.pass_yards
        total_rush_yards += my_tot.rush_yards
        turnovers_committed += my_tot.turnovers
        turnovers_forced += opp_tot.turnovers

    streak = "-"
    if recent:
        last_won = recent[-1].won
        n = 0
        for r in reversed(recent):
            if r.won != last_won:
                break
            n += 1
        streak = f"{'W' if last_won else 'L'}{n}"

    power_rank = next(
        (i for i, r in enumerate(season.standings(), start=1) if r.abbr == team_abbr),
        None,
    )
    n = len(games)
    return {
        "wins": record.wins,
        "losses": record.losses,
        "streak": streak,
        "power_rank": power_rank,
        "last3": list(reversed(recent[-3:])),
        "ppg": round(record.points_for / n, 1) if n else None,
        "papg": round(record.points_against / n, 1) if n else None,
        "pass_ypg": round(total_pass_yards / n, 1) if n else None,
        "rush_ypg": round(total_rush_yards / n, 1) if n else None,
        "turnover_diff": turnovers_forced - turnovers_committed,
        "games_played": n,
    }


def build_scouting_report(season, opponent_abbr: str) -> dict:
    """Assembles the full report for one opponent. Every value is either
    a real, counted statistic or None (not a fabricated default) when
    the opponent hasn't played enough games yet for a given split to
    have any sample -- e.g. a team's first career 3rd-and-long play of
    the season leaves that bucket empty until it happens."""
    return {
        "team_abbr": opponent_abbr,
        "summary": team_summary(season, opponent_abbr),
        "offense": situational_offense(season, opponent_abbr),
        "defense": situational_defense(season, opponent_abbr),
        "fourth_down": fourth_down_aggressiveness(season, opponent_abbr),
        "field_goals": field_goal_accuracy(season, opponent_abbr),
        "discipline": penalty_discipline(season, opponent_abbr),
    }
