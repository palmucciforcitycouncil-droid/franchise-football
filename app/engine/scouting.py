"""
Scouting: Next Opponent (GDD Part 1 Sec 10.4.1) -- a report on the
user's team's upcoming opponent, built entirely from real PlayEvents
this season has actually logged, not fabricated placeholder numbers.

Deliberate scope cuts, since the underlying systems don't exist yet:
- No pass-depth (quick/standard/deep) split or target-distribution
  breakdown -- PlayEvent has no depth-of-target or receiver-rank field.
- No run point-of-attack (inside/outside) split -- PlayEvent has no run
  direction/gap field either; only the DEFENSE's own predicted tactic
  (Plug Gaps/Contain Edge, decide_run_tactic in defensive_ai.py) is
  tracked, which is why situational_defense() can report that but
  situational_offense() can't report the offense's real point of attack.
- No return-game averages -- the special-teams engine (drive_sim.py's
  _punt_result) computes a net field position, not a tracked return
  yardage stat.
- No Coach entity -- ROADMAP.md's R3 (Coaching Staff) hasn't been built,
  so the Overview tab's coach info is a disclosed placeholder wired in
  by app/main.py (`_placeholder_coach()`), not real data from this module.
Everything else here (situational run/pass splits, red zone tendencies
including trip-based TD conversion %, blitz/coverage rates including the
defense's own run-tactic and primary-call splits, 4th-down aggressiveness
and success rate, field-goal accuracy by distance, discipline including
league rank, season stats including yards allowed and turnover
differential rank) is computed for real from this season's actual
games -- if a number looks specific, it's because it was actually
counted, not estimated.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

from app.engine.flavor_text import pick_and_render

OFFENSIVE_PENALTY_TYPES = {"False start", "Delay of game", "Illegal formation", "Holding"}
DEFENSIVE_PENALTY_TYPES = {"Offside", "Defensive pass interference", "Roughing the passer"}

_FG_YARDS_RE = re.compile(r"^(\d+)-yard field goal")


def _pct(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 1) if denominator else None


def _complement(pct_value: float | None) -> float | None:
    """The other side of a real two-way split (e.g. run % from a real
    pass %) -- kept as an explicit backend field rather than `100 - x`
    arithmetic in the template, and None stays None (no fabricated
    complement for an empty sample)."""
    return None if pct_value is None else round(100 - pct_value, 1)


def next_opponent_weather(season, team_abbr: str):
    """R7 (GDD Sec 6.9.2): real, deterministic weather forecast
    (app/engine/weather.py) for team_abbr's next unplayed game -- the
    same forward scan find_next_opponent() does, just also keeping the
    week number and home team (generate_weather()'s own real inputs)
    that function's simpler (opponent, is_home) return doesn't carry.
    None once the season has no more games left for team_abbr."""
    from app.engine.weather import generate_weather
    for offset, week in enumerate(season.schedule[season.current_week - 1:]):
        week_num = season.current_week + offset
        for g in week:
            if g.result is not None:
                continue
            if team_abbr in (g.home_abbr, g.away_abbr):
                return generate_weather(season.league_seed, season.season_number, week_num, g.home_abbr)
    return None


def find_next_opponent(season, team_abbr: str) -> tuple[str, bool] | None:
    """Scans forward from season.current_week (skipping over a bye week
    if team_abbr doesn't play that week) for team_abbr's next unplayed
    game. Returns (opponent_abbr, team_is_home), or None if the season
    is over or team_abbr has no games left.

    Playoff games live entirely in season.playoffs.rounds -- a separate
    structure never appended to season.schedule -- so once the regular
    season is done, this falls through to the bracket's current round
    (rounds[-1], the round that still needs simulating; every prior
    round is fully resolved before a new one is appended). Returns None
    for a team on a bye this round or already eliminated -- neither has
    a confirmed next opponent yet -- as well as once the bracket itself
    is complete."""
    for week in season.schedule[season.current_week - 1:]:
        for g in week:
            if g.result is not None:
                continue
            if g.home_abbr == team_abbr:
                return g.away_abbr, True
            if g.away_abbr == team_abbr:
                return g.home_abbr, False
    bracket = season.playoffs
    if bracket is not None and not bracket.is_complete:
        for matchup in bracket.rounds[-1]:
            if matchup.result is not None:
                continue
            if matchup.home_abbr == team_abbr:
                return matchup.away_abbr, True
            if matchup.away_abbr == team_abbr:
                return matchup.home_abbr, False
    return None


def _played_games(season, team_abbr: str) -> list[tuple[object, bool]]:
    """(WeekGame, team_is_home) for every game team_abbr has actually
    played this season, in week order.

    R10 (GDD preseason): a real Week 1 has NOTHING to show here yet --
    every scouting/situational split would render as an empty "—" sample
    the moment a franchise starts. So while season.current_week == 1 (no
    regular-season game has been played yet), this backfills with the
    real preseason games instead -- 4 real, played games with real box
    scores, just not ones that count toward the regular season. The
    moment Week 1 is actually simulated (current_week advances past 1),
    this reverts to regular-season-only and preseason is never queried
    again, matching the GDD's "preseason isn't the regular season"
    scoping."""
    out = []
    weeks = season.schedule
    if season.current_week == 1 and getattr(season, "preseason_schedule", None):
        weeks = season.preseason_schedule + season.schedule
    for week in weeks:
        for g in week:
            if g.result is None:
                continue
            if g.home_abbr == team_abbr:
                out.append((g, True))
            elif g.away_abbr == team_abbr:
                out.append((g, False))
    return out


def _preseason_game_ids(season) -> set[int]:
    """id() of every WeekGame object in season.preseason_schedule, so a
    game pulled out of _played_games()'s combined preseason+regular list
    can be told apart from a real one (Brian's ask, 2026-09-13: Scouting
    needs to visually flag preseason games instead of showing them
    identically to a real Week 1 result)."""
    return {id(g) for week in getattr(season, "preseason_schedule", None) or [] for g in week}


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
    first_down_pass_pct = _pass_pct(first_down)
    third_short_pass_pct = _pass_pct(third_short)
    third_medium_pass_pct = _pass_pct(third_medium)
    third_long_pass_pct = _pass_pct(third_long)
    redzone_pass_pct = _pass_pct(red_zone)
    return {
        "sample_size": len(plays),
        "first_down_pass_pct": first_down_pass_pct,
        "first_down_run_pct": _complement(first_down_pass_pct),
        "third_short_pass_pct": third_short_pass_pct,
        "third_short_run_pct": _complement(third_short_pass_pct),
        "third_medium_pass_pct": third_medium_pass_pct,
        "third_medium_run_pct": _complement(third_medium_pass_pct),
        "third_long_pass_pct": third_long_pass_pct,
        "third_long_run_pct": _complement(third_long_pass_pct),
        "redzone_pass_pct": redzone_pass_pct,
        "redzone_run_pct": _complement(redzone_pass_pct),
    }


def _defcall_parts(defensive_call: str) -> list[str]:
    return [s.strip() for s in defensive_call.split(",")]


def situational_defense(season, team_abbr: str) -> dict:
    plays = [p for p in _defensive_plays(season, team_abbr) if p.defensive_call]
    red_zone = [p for p in plays if p.field_pos >= 80]
    third_long = [p for p in plays if p.down == 3 and p.distance >= 8]

    def blitz_pct(group):
        return _pct(sum(1 for p in group if any(part.startswith("Blitz") for part in _defcall_parts(p.defensive_call))), len(group))

    def man_pct(group):
        return _pct(sum(1 for p in group if "Man" in _defcall_parts(p.defensive_call)), len(group))

    def primary_pct(label):
        return _pct(sum(1 for p in plays if _defcall_parts(p.defensive_call)[0] == label), len(plays))

    # Run tactic (defensive_ai.py's decide_run_tactic): only ever set on
    # "Run Defense" calls, so this is real, just a narrower sample than
    # `plays` as a whole -- Figma's "Run Blitz / Plug Gaps" label is
    # relabeled to this engine's own real two tactics (Plug Gaps/Contain
    # Edge), not a literal 1:1 match to the Figma wording.
    run_tactic_plays = [p for p in plays if any(part in ("Plug Gaps", "Contain Edge") for part in _defcall_parts(p.defensive_call))]

    def run_tactic_pct(label):
        return _pct(sum(1 for p in run_tactic_plays if label in _defcall_parts(p.defensive_call)), len(run_tactic_plays))

    overall_man_pct = man_pct(plays)
    redzone_man = man_pct(red_zone)
    return {
        "sample_size": len(plays),
        "blitz_pct": blitz_pct(plays),
        "man_pct": overall_man_pct,
        "zone_pct": _complement(overall_man_pct),
        "redzone_blitz_pct": blitz_pct(red_zone),
        "redzone_man_pct": redzone_man,
        "redzone_zone_pct": _complement(redzone_man),
        "third_long_blitz_pct": blitz_pct(third_long),
        "run_defense_pct": primary_pct("Run Defense"),
        "pass_defense_pct": primary_pct("Pass Defense"),
        "standard_pct": primary_pct("Standard"),
        "plug_gaps_pct": run_tactic_pct("Plug Gaps"),
        "contain_edge_pct": run_tactic_pct("Contain Edge"),
    }


def red_zone_efficiency(season, team_abbr: str) -> dict:
    """Real red-zone trip conversion rate -- among team_abbr's own
    offensive drives that reached the red zone (any play in that drive
    with field_pos >= 80), what fraction ended in a touchdown. Grouped by
    the real per-game `drive_number` game_sim.py already stamps on every
    PlayEvent (a single running counter per game, so each drive_number
    within one game belongs to exactly one team's one drive) -- the
    standard NFL "red zone TD%" stat, not a per-play approximation."""
    trips = touchdowns = 0
    for g, _ in _played_games(season, team_abbr):
        drives: dict[int, list] = {}
        for p in g.result.plays:
            if p.offense_abbr == team_abbr:
                drives.setdefault(p.drive_number, []).append(p)
        for drive_plays in drives.values():
            if any(p.field_pos >= 80 for p in drive_plays):
                trips += 1
                if drive_plays[-1].outcome == "touchdown":
                    touchdowns += 1
    return {"trips": trips, "touchdowns": touchdowns, "td_pct": _pct(touchdowns, trips)}


def fourth_down_aggressiveness(season, team_abbr: str) -> dict:
    attempts = [p for p in _offensive_plays(season, team_abbr) if p.down == 4]
    conversions = [p for p in attempts if p.outcome in ("first_down", "touchdown")]
    return {"attempts": len(attempts), "conversions": len(conversions), "success_rate": _pct(len(conversions), len(attempts))}


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


def field_goal_accuracy_3bucket(season, team_abbr: str) -> dict:
    """Same real make/attempt data as field_goal_accuracy(), regrouped
    into the 3 buckets the Scouting Panel's Special tab wants (Under 40 /
    40-49 / 50+) instead of the Stats page's own finer 4-bucket split
    (<30/30-39/40-49/50+, unchanged, still used there) -- a display
    regrouping, not a second parse of the underlying plays."""
    fine = field_goal_accuracy(season, team_abbr)
    under_40_made = fine["<30"]["made"] + fine["30-39"]["made"]
    under_40_att = fine["<30"]["attempted"] + fine["30-39"]["attempted"]
    return {
        "Under 40": {"made": under_40_made, "attempted": under_40_att, "pct": _pct(under_40_made, under_40_att)},
        "40-49": fine["40-49"],
        "50+": fine["50+"],
    }


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
    is_preseason: bool = False


def team_summary(season, team_abbr: str) -> dict:
    record = season.records[team_abbr]
    games = _played_games(season, team_abbr)
    preseason_ids = _preseason_game_ids(season)

    recent: list[RecentGame] = []
    total_pass_yards = total_rush_yards = 0
    total_pass_yards_allowed = total_rush_yards_allowed = 0
    turnovers_committed = turnovers_forced = 0
    for g, is_home in games:
        my_score = g.result.home_score if is_home else g.result.away_score
        opp_score = g.result.away_score if is_home else g.result.home_score
        opponent = g.away_abbr if is_home else g.home_abbr
        won = (g.result.winner == "home") == is_home
        recent.append(RecentGame(won=won, my_score=my_score, opp_score=opp_score,
                                  opponent=opponent, at="vs" if is_home else "@",
                                  is_preseason=id(g) in preseason_ids))
        my_tot = g.result.home_totals if is_home else g.result.away_totals
        opp_tot = g.result.away_totals if is_home else g.result.home_totals
        total_pass_yards += my_tot.pass_yards
        total_rush_yards += my_tot.rush_yards
        total_pass_yards_allowed += opp_tot.pass_yards
        total_rush_yards_allowed += opp_tot.rush_yards
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

    # Overview tab's "Philosophy" label -- a real, disclosed simplification
    # (a single season-long pass-rate threshold, not a scouted "identity"
    # score) derived from the same real play-type counts situational_offense()
    # already counts, just over every offensive play instead of one split.
    overall_pass_pct = _pass_pct(_offensive_plays(season, team_abbr))
    if overall_pass_pct is None:
        philosophy = None
    elif overall_pass_pct >= 58:
        philosophy = "Pass-Heavy"
    elif overall_pass_pct <= 42:
        philosophy = "Run-Heavy"
    else:
        philosophy = "Balanced"

    return {
        "wins": record.wins,
        "losses": record.losses,
        "ties": getattr(record, "ties", 0),
        "streak": streak,
        "power_rank": power_rank,
        "last3": list(reversed(recent[-3:])),
        "ppg": round(record.points_for / n, 1) if n else None,
        "papg": round(record.points_against / n, 1) if n else None,
        "pass_ypg": round(total_pass_yards / n, 1) if n else None,
        "rush_ypg": round(total_rush_yards / n, 1) if n else None,
        "total_ypg": round((total_pass_yards + total_rush_yards) / n, 1) if n else None,
        "pass_ypg_allowed": round(total_pass_yards_allowed / n, 1) if n else None,
        "rush_ypg_allowed": round(total_rush_yards_allowed / n, 1) if n else None,
        "total_ypg_allowed": round((total_pass_yards_allowed + total_rush_yards_allowed) / n, 1) if n else None,
        "turnover_diff": turnovers_forced - turnovers_committed,
        "games_played": n,
        "philosophy": philosophy,
    }


def league_ranks(season, team_abbr: str) -> dict:
    """This team's rank among every team with at least one game played,
    on two of the Stats tab's real season aggregates: Penalties/Game
    (rank 1 = fewest, i.e. most disciplined) and Turnover Differential
    (rank 1 = best, i.e. highest). Real, computed fresh from every
    team's own games -- not cached, so this is an O(32) full-league scan
    on every dashboard render; revisit with the same lru_cache pattern
    depth_chart.py/history_store.py already use if that ever becomes a
    measurable cost."""
    all_abbrs = list(season.records.keys())

    penalty_vals: dict[str, float] = {}
    for a in all_abbrs:
        pg = penalty_discipline(season, a)["per_game"]
        if pg is not None:
            penalty_vals[a] = pg

    turnover_vals: dict[str, int] = {}
    for a in all_abbrs:
        if _played_games(season, a):
            turnover_vals[a] = team_summary(season, a)["turnover_diff"]

    def rank_of(values: dict, reverse: bool) -> int | None:
        if team_abbr not in values:
            return None
        ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=reverse)
        return next((i for i, (a, _) in enumerate(ordered, start=1) if a == team_abbr), None)

    return {
        "penalty_rank": rank_of(penalty_vals, reverse=False),
        "turnover_rank": rank_of(turnover_vals, reverse=True),
        "of_teams": len(all_abbrs),
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
        "red_zone": red_zone_efficiency(season, opponent_abbr),
        "fourth_down": fourth_down_aggressiveness(season, opponent_abbr),
        "field_goals": field_goal_accuracy_3bucket(season, opponent_abbr),
        "discipline": penalty_discipline(season, opponent_abbr),
        "league_ranks": league_ranks(season, opponent_abbr),
        "weather": next_opponent_weather(season, opponent_abbr),
    }


# ---------------------------------------------------------------------------
# Scouting Panel prose (ROADMAP.md Sec4e/R12, 2026-09-12, GDD-original --
# not from any Figma source, same precedent as the Awards Race box).
#
# One short sentence per tab, bucketing the exact real fields the stat
# grids on this page already show into a qualitative bracket (pass-heavy/
# run-heavy/balanced, blitz-heavy/conservative, etc.) and picking a real
# phrasing deterministically -- same app.engine.flavor_text picker Weekly
# Headlines uses, same reason: no live LLM call, reproducible given the
# same LEAGUE_SEED (GDD Sec 1.3). Purely additive -- every stat grid these
# tabs already render stays exactly as it was; this is one extra sentence
# above each one. None of these functions invents a bracket boundary that
# isn't already a real threshold used elsewhere in this module (Pass-Heavy/
# Run-Heavy/Balanced reuses team_summary()'s own `philosophy` field
# verbatim, not a second, different cutoff).
# ---------------------------------------------------------------------------

PROSE_TEMPLATES: dict[str, list[str]] = {
    "overview_no_games": [
        "{team} hasn't played a game yet this season -- no real tendencies to report yet.",
    ],
    "overview_pass_heavy": [
        "{team} leans pass-heavy on offense, averaging {ppg} points and {papg} allowed per game.",
        "A pass-first attack: {team} is averaging {ppg} PPG this season ({papg} allowed).",
    ],
    "overview_run_heavy": [
        "{team} builds around the run, averaging {ppg} points and {papg} allowed per game.",
        "Ground-and-pound identity: {team} scores {ppg} PPG while allowing {papg}.",
    ],
    "overview_balanced": [
        "{team} plays a balanced offense, averaging {ppg} points and {papg} allowed per game.",
    ],
    "offense_pass_heavy": [
        "{team} throws {first_down_pass_pct}% of the time on 1st down, climbing to {third_long_pass_pct}% on 3rd-and-long.",
    ],
    "offense_run_heavy": [
        "{team} leans run on early downs ({first_down_run_pct}% run on 1st down) but opens up on 3rd-and-long ({third_long_pass_pct}% pass).",
    ],
    "offense_balanced": [
        "{team} keeps defenses honest with a {first_down_pass_pct}% pass / {first_down_run_pct}% run split on 1st down.",
    ],
    "offense_no_sample": [
        "Not enough offensive snaps logged yet to show a real situational split for {team}.",
    ],
    "defense_blitz_heavy": [
        "{team}'s defense brings pressure often, blitzing on {blitz_pct}% of snaps.",
    ],
    "defense_conservative": [
        "{team}'s defense plays it conservative, blitzing on just {blitz_pct}% of snaps.",
    ],
    "defense_balanced_blitz": [
        "{team} mixes it up on defense, blitzing {blitz_pct}% of the time ({man_pct}% man coverage).",
    ],
    "defense_no_sample": [
        "Not enough defensive snaps logged yet to show a real blitz/coverage split for {team}.",
    ],
    "special_teams": [
        "{team} has made {fg_pct}% of field goal attempts this season.",
    ],
    "special_teams_no_sample": [
        "{team} hasn't attempted a field goal yet this season.",
    ],
    "discipline_clean": [
        "{team} is one of the league's more disciplined teams, ranked #{rank} in least penalties per game.",
    ],
    "discipline_average": [
        "{team} ranks #{rank} in the league in penalties per game.",
    ],
    "discipline_sloppy": [
        "{team} has struggled with penalties, ranked #{rank} in the league.",
    ],
    "stats_positive_to": [
        "{team} owns a plus-{diff} turnover margin, a real edge on the stat sheet.",
    ],
    "stats_negative_to": [
        "{team} is a minus-{diff} in turnover margin this season.",
    ],
    "stats_even_to": [
        "{team} is even in turnover margin this season.",
    ],
}


def overview_prose(scouting: dict, league_seed: int) -> str:
    team, summary = scouting["team_abbr"], scouting["summary"]
    if not summary["games_played"]:
        return pick_and_render(PROSE_TEMPLATES, "overview_no_games", (league_seed, team), team=team)
    category = {"Pass-Heavy": "overview_pass_heavy", "Run-Heavy": "overview_run_heavy"}.get(summary["philosophy"], "overview_balanced")
    return pick_and_render(
        PROSE_TEMPLATES, category, (league_seed, team, summary["games_played"]),
        team=team, ppg=summary["ppg"], papg=summary["papg"],
    )


def offense_prose(scouting: dict, league_seed: int) -> str:
    team, offense = scouting["team_abbr"], scouting["offense"]
    if not offense["sample_size"]:
        return pick_and_render(PROSE_TEMPLATES, "offense_no_sample", (league_seed, team), team=team)
    pass_pct = offense["first_down_pass_pct"] or 0
    category = "offense_pass_heavy" if pass_pct >= 58 else "offense_run_heavy" if pass_pct <= 42 else "offense_balanced"
    return pick_and_render(
        PROSE_TEMPLATES, category, (league_seed, team, offense["sample_size"]),
        team=team, first_down_pass_pct=offense["first_down_pass_pct"], first_down_run_pct=offense["first_down_run_pct"],
        third_long_pass_pct=offense["third_long_pass_pct"],
    )


def defense_prose(scouting: dict, league_seed: int) -> str:
    team, defense = scouting["team_abbr"], scouting["defense"]
    if not defense["sample_size"]:
        return pick_and_render(PROSE_TEMPLATES, "defense_no_sample", (league_seed, team), team=team)
    blitz = defense["blitz_pct"] or 0
    category = "defense_blitz_heavy" if blitz >= 35 else "defense_conservative" if blitz <= 15 else "defense_balanced_blitz"
    return pick_and_render(
        PROSE_TEMPLATES, category, (league_seed, team, defense["sample_size"]),
        team=team, blitz_pct=defense["blitz_pct"], man_pct=defense["man_pct"],
    )


def special_teams_prose(scouting: dict, league_seed: int) -> str:
    team, fg = scouting["team_abbr"], scouting["field_goals"]
    total_attempts = sum(b["attempted"] for b in fg.values()) if isinstance(fg, dict) else 0
    if not total_attempts:
        return pick_and_render(PROSE_TEMPLATES, "special_teams_no_sample", (league_seed, team), team=team)
    total_made = sum(b["made"] for b in fg.values())
    fg_pct = round(100 * total_made / total_attempts, 1)
    return pick_and_render(
        PROSE_TEMPLATES, "special_teams", (league_seed, team, total_attempts),
        team=team, fg_pct=fg_pct,
    )


def discipline_prose(scouting: dict, league_seed: int) -> str:
    team = scouting["team_abbr"]
    rank = scouting["league_ranks"]["penalty_rank"]
    if rank is None:
        return pick_and_render(PROSE_TEMPLATES, "discipline_average", (league_seed, team), team=team, rank="—")
    category = "discipline_clean" if rank <= 10 else "discipline_sloppy" if rank >= 23 else "discipline_average"
    return pick_and_render(PROSE_TEMPLATES, category, (league_seed, team, rank), team=team, rank=rank)


def stats_prose(scouting: dict, league_seed: int) -> str:
    team, summary = scouting["team_abbr"], scouting["summary"]
    diff = summary["turnover_diff"]
    category = "stats_positive_to" if diff > 0 else "stats_negative_to" if diff < 0 else "stats_even_to"
    return pick_and_render(
        PROSE_TEMPLATES, category, (league_seed, team, summary["games_played"]),
        team=team, diff=abs(diff),
    )
