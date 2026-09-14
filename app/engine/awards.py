"""
Season Awards (GDD Part 1 Sec 7.4): League MVP, Offensive/Defensive
Player of the Year (OPOY/DPOY), Rookie of the Year (ROY).

Real, counted inputs: app/engine/season_stats.py's full per-player
season Passing/Rushing/Receiving aggregation (built from every game's
real box score), each team's real win% (Season.records), and each
player's real years_pro from the Madden-derived roster import (rookie
== years_pro == 0). Computed from however many games have been played
so far -- there's no "season complete" gate, so this doubles as an
in-season Awards Race leaderboard and a season-end result once the
season (and playoffs) finish, matching how the old GDD source
documents described an always-visible "Awards Race" widget.

Deliberate, disclosed interpretations of an underspecified GDD formula
-- Sec 7.4 doesn't give exact weights or a defensive stat model, so
these choices are this module's own, not GDD-literal:

- MVP's GDD formula is "a weighted sum of team wins, Offensive EPA,
  total yards, and touchdowns," but this engine has no per-play EPA
  model at all (drive_sim.py's own docstring notes no GDD-literal
  formula exists to build one from). "Offensive EPA" is folded into
  the yards/touchdowns terms rather than kept separate: MVP = 0.4 *
  team win% + 0.6 * the player's own normalized production score
  (below). The 0.4/0.6 split is this module's choice, not a GDD value.
- The candidate pool for MVP/OPOY/ROY is every player who appears in
  the season's passing, rushing, or receiving aggregation (i.e. every
  offensive skill player who's touched the ball). Each stat is
  normalized WITHIN its own category (a QB's yards against other QBs'
  yards, not against RBs') before the categories are compared, since
  raw yardage isn't on the same scale across positions -- production
  score = 0.5 * normalized_yards + 0.5 * normalized_touchdowns.
- DPOY ("statistical dominance at the position") is now a real,
  multi-stat composite built on app/engine/defensive_box_score.py's real
  per-player defensive attribution (solo tackles, sacks, TFL, INT, PD,
  FF, Defensive TD -- see that module's own docstring, and drive_sim.py's
  _run_tackler/_sack_defender/_defensive_td_probability docstrings for
  exactly how each defender/score is chosen).
  No GDD formula/weights are given for this either, so this module's own
  choice: DPOY score = 0.27 * normalized(sacks) + 0.27 *
  normalized(interceptions) + 0.13 * normalized(tackles_for_loss) +
  0.09 * normalized(solo_tackles) + 0.09 * normalized(forced_fumbles) +
  0.05 * normalized(passes_defended) + 0.10 *
  normalized(defensive_touchdowns), each normalized within the whole
  defensive candidate pool (there's no positional split like offense's
  QB/RB/WR-TE -- DL/LB/DB are all compared on the same defensive stat
  line, matching how DPOY is a single, position-agnostic real NFL award
  too). Weighted toward sacks/INTs since those are what actually
  decides most real-world AP DPOY votes, with a real but bounded slice
  (0.10) carved out for Defensive TD -- a rare, high-impact play real
  DPOY voters do notice, but nowhere near as decisive as a full season of
  sacks/INTs; fumble_recoveries is tracked and shown but excluded from
  the score itself (more a product of luck/opportunity than of
  individual defensive dominance).
- COTY (Coach of the Year) is the one award here with a real GDD
  formula (Sec 7.4.6): CS_COTY = 0.35*RankNorm(Wins) +
  0.25*RankNorm(Wins-ExpectedWins) + 0.15*RankNorm(Improvement_yoy) +
  0.10*RankNorm(S) + 0.10*RankNorm(-InjuryLostWAR) +
  0.05*PlayoffByeBonus. Five of its six terms are computed for real
  here (see coach_of_the_year() for how each one is sourced). The sixth,
  InjuryLostWAR, has no source at all -- no injury system exists in this
  engine (ROADMAP.md R1) -- so its 0.10 weight is REDISTRIBUTED across
  the five real terms in proportion rather than silently scored as
  zero for every coach, which would have made the award land on a
  slightly-wrong-but-plausible-looking total. Disclosed here and in
  that function's docstring, not hidden.
- ROY now draws from BOTH the offensive AND defensive candidate pools
  (previously offense-only, since DPOY's interception-only basis was
  judged too thin to fairly weigh a rookie defender against a rookie
  QB/RB/WR -- resolved now that a real defensive box score exists).
  Each side is normalized within its OWN rookie sub-pool first (same
  technique MVP/OPOY already use to compare QB/RB/WR on one scale)
  before the two [0,1]-ish scores are merged into one ranking -- a
  standout rookie defender can now genuinely win ROY over a rookie
  offensive skill player, not just place behind one by construction.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from sqlmodel import select

from app.core.db import get_session
from app.models.player import Player
from app.models.coach import CoachRole
from app.engine.season_stats import aggregate_season_stats, aggregate_season_defensive_stats

# How many candidates the Awards Race / final award lists keep (Brian's
# ask, 2026-09-14: top 10, not 5).
AWARDS_RACE_TOP_N = 10


def _normalize(value: float, pool: list[float]) -> float:
    if not pool:
        return 0.0
    lo, hi = min(pool), max(pool)
    return (value - lo) / (hi - lo) if hi > lo else 0.5


@dataclass
class AwardCandidate:
    name: str
    team_abbr: str
    position: str  # "QB" | "RB" | "WR/TE" | "DEF"
    stat_line: str  # human-readable summary, e.g. "3,240 pass yds, 28 TD, 6 INT"
    score: float


@dataclass
class CoachAwardCandidate:
    """COTY's own candidate shape -- a coach, not a player, so it can't
    reuse AwardCandidate (no position, and the "stat line" is a record
    plus a playoff result rather than yardage)."""
    coach_id: str
    name: str
    team_abbr: str
    record: str            # e.g. "13-4"
    stat_line: str         # e.g. "13-4, +3.1 wins over expected, +5 vs. last season"
    score: float


def _pythagorean_expected_wins(points_for: int, points_against: int, games: int) -> float:
    """The standard Pythagorean expectation (exponent 2.37, the
    commonly used NFL value), which is what "ExpectedWins" in Sec
    7.4.6's formula has to mean in an engine with no per-play win
    probability model. Real inputs: this team's own points for/against,
    already tracked on TeamRecord."""
    if games <= 0 or points_for + points_against <= 0:
        return 0.0
    exp = 2.37
    pf, pa = float(points_for), float(points_against)
    return games * (pf ** exp) / (pf ** exp + pa ** exp)


def _rank_norm(values: dict[str, float], reverse: bool = True) -> dict[str, float]:
    """Sec 7.4.6's RankNorm: a team's rank within the league mapped onto
    [0, 1], best = 1.0. Ties share the better rank's value."""
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=reverse)
    n = len(ordered)
    out: dict[str, float] = {}
    prev_value = None
    prev_norm = 1.0
    for i, (key, value) in enumerate(ordered):
        norm = 1.0 if n == 1 else 1.0 - i / (n - 1)
        if prev_value is not None and value == prev_value:
            norm = prev_norm
        out[key] = norm
        prev_value, prev_norm = value, norm
    return out


def _strength_of_schedule(season) -> dict[str, float]:
    """Sec 7.4.4's S: opponent strength. Computed for real from the
    schedule -- each team's opponents' combined win percentage, the
    standard SoS definition. Sec 7.4.4 also folds "unit ranks faced"
    into its 0.85-1.15 index; that half is omitted (disclosed), since
    weighting by faced-unit rank needs a per-unit rating this engine
    doesn't compute."""
    opponents: dict[str, list[str]] = {a: [] for a in season.records}
    for week in season.schedule:
        for game in week:
            if game.result is None:
                continue
            opponents[game.home_abbr].append(game.away_abbr)
            opponents[game.away_abbr].append(game.home_abbr)
    out: dict[str, float] = {}
    for abbr, opps in opponents.items():
        if not opps:
            continue
        out[abbr] = sum(season.records[o].win_pct for o in opps) / len(opps)
    return out


def _prior_season_wins(season) -> dict[str, int]:
    """Sec 7.4.6's Improvement_yoy input: last season's real win total
    per team, read from the archived League History (which is where
    every completed season's final standings already live). Returns an
    empty dict in a franchise's first season -- there is genuinely
    nothing to improve on yet, and coach_of_the_year() drops the
    improvement term entirely rather than scoring everyone at zero."""
    from app.services import history_store
    try:
        history = history_store.get_history()
    except Exception:
        return {}
    prior = [rec for rec in history if rec.season_number == season.season_number - 1]
    if not prior:
        return {}
    return {t.abbr: t.wins for t in prior[0].team_results}


def coach_of_the_year(season, top_n: int = 5) -> list[CoachAwardCandidate]:
    """GDD Sec 7.4.6's COTY, with every term this engine can source for
    real, and the one it cannot (InjuryLostWAR) removed with its weight
    redistributed proportionally across the rest rather than scored as a
    constant zero.

    Term by term:
      0.35 RankNorm(Wins)               -- real, TeamRecord.wins
      0.25 RankNorm(Wins-ExpectedWins)  -- real, Pythagorean expectation
                                           from the team's own PF/PA
      0.15 RankNorm(Improvement_yoy)    -- real, vs. last season's
                                           archived win total; DROPPED
                                           (weight redistributed) in a
                                           franchise's first season,
                                           when there is no prior season
      0.10 RankNorm(S)                  -- real, opponents' combined win%
      0.10 RankNorm(-InjuryLostWAR)     -- NOT COMPUTABLE, no injury
                                           system exists (ROADMAP R1)
      0.05 PlayoffByeBonus              -- real, the conference's #1 seed

    Candidates are head coaches only. Sec 7.4.2 lists COTY as a single
    award and every real-world equivalent goes to the head coach; the
    coordinators' own recognition in this project is Sec 7.9's
    championship credit, which they already receive by role."""
    from app.services import coach_store
    from app.engine import playoffs as playoffs_engine

    heads = [c for c in coach_store.all_coaches()
             if c.team_abbr and not c.retired and CoachRole(c.role) is CoachRole.HC]
    if not heads:
        return []

    played = {a: r for a, r in season.records.items() if r.games_played > 0}
    if not played:
        return []

    wins = {a: float(r.wins) for a, r in played.items()}
    over_expected = {
        a: r.wins - _pythagorean_expected_wins(r.points_for, r.points_against, r.games_played)
        for a, r in played.items()
    }
    sos = _strength_of_schedule(season)
    prior_wins = _prior_season_wins(season)
    improvement = {a: r.wins - prior_wins[a] for a, r in played.items() if a in prior_wins}

    terms: list[tuple[float, dict[str, float]]] = [
        (0.35, _rank_norm(wins)),
        (0.25, _rank_norm(over_expected)),
        (0.10, _rank_norm(sos)),
    ]
    if improvement:
        terms.append((0.15, _rank_norm(improvement)))

    # Renormalize whatever terms are actually real so the weights sum to
    # 0.95 (leaving Sec 7.4.6's own 0.05 for the bye bonus) instead of
    # letting a dropped term silently deflate every coach's score.
    weight_total = sum(w for w, _ in terms)
    scale = 0.95 / weight_total if weight_total else 0.0

    top_seeds = set()
    for conference in ("AFC", "NFC"):
        seeds = playoffs_engine.seed_conference(season, conference)
        if seeds:
            top_seeds.add(seeds[0])  # the #1 seed is the one with a bye

    candidates: list[CoachAwardCandidate] = []
    for coach in heads:
        abbr = coach.team_abbr
        if abbr not in played:
            continue
        score = sum(weight * scale * ranked.get(abbr, 0.0) for weight, ranked in terms)
        if abbr in top_seeds:
            score += 0.05
        record = played[abbr]
        bits = [f"{record.wins}-{record.losses}"]
        bits.append(f"{over_expected[abbr]:+.1f} wins vs. expected")
        if abbr in improvement:
            bits.append(f"{improvement[abbr]:+d} vs. last season")
        if abbr in top_seeds:
            bits.append("#1 seed")
        candidates.append(CoachAwardCandidate(
            coach_id=coach.coach_id,
            name=coach.full_name,
            team_abbr=abbr,
            record=f"{record.wins}-{record.losses}",
            stat_line=", ".join(bits),
            score=score,
        ))

    return sorted(candidates, key=lambda c: (-c.score, c.name))[:top_n]


def _rookie_keys(season) -> set[tuple[str, str]]:
    """(team_abbr, full_name) for every real rookie (years_pro == 0) on
    a real roster -- free agents (team_abbr is None) can't be
    candidates since they haven't played a game this season."""
    with get_session() as s:
        rookies = s.exec(
            select(Player).where(Player.years_pro == 0, Player.team_abbr != None)  # noqa: E711
        ).all()
    return {(p.team_abbr, p.full_name) for p in rookies}


def _offensive_candidates(season, rookies_only: bool = False) -> list[AwardCandidate]:
    passing, rushing, receiving = aggregate_season_stats(season)
    rookie_keys = _rookie_keys(season) if rookies_only else None
    return offensive_candidates_from_stats(passing, rushing, receiving, rookie_keys)


def offensive_candidates_from_stats(passing: dict, rushing: dict, receiving: dict, rookie_keys: set | None = None) -> list[AwardCandidate]:
    """Pure version of _offensive_candidates, decoupled from a live
    Season object -- takes the same-shaped dicts aggregate_season_stats()
    produces (keyed by (team_abbr, name) -> Season*Line) directly. Split
    out so real historical NFL data (scripts/import_nfl_history.py) can
    score real players by this exact same formula, not a re-implemented
    copy that could silently drift from the live one."""

    def _keep(key):
        return rookie_keys is None or key in rookie_keys

    candidates: list[AwardCandidate] = []

    qb_pool = [(k, l) for k, l in passing.items() if l.attempts >= 1 and _keep(k)]
    if qb_pool:
        yards_pool = [l.yards for _, l in qb_pool]
        td_pool = [l.touchdowns for _, l in qb_pool]
        for (abbr, name), line in qb_pool:
            score = 0.5 * _normalize(line.yards, yards_pool) + 0.5 * _normalize(line.touchdowns, td_pool)
            candidates.append(AwardCandidate(
                name=name, team_abbr=abbr, position="QB",
                stat_line=f"{line.yards:,} pass yds, {line.touchdowns} TD, {line.interceptions} INT",
                score=score,
            ))

    rb_pool = [(k, l) for k, l in rushing.items() if l.carries >= 1 and _keep(k)]
    if rb_pool:
        yards_pool = [l.yards for _, l in rb_pool]
        td_pool = [l.touchdowns for _, l in rb_pool]
        for (abbr, name), line in rb_pool:
            score = 0.5 * _normalize(line.yards, yards_pool) + 0.5 * _normalize(line.touchdowns, td_pool)
            candidates.append(AwardCandidate(
                name=name, team_abbr=abbr, position="RB",
                stat_line=f"{line.yards:,} rush yds, {line.touchdowns} TD",
                score=score,
            ))

    wr_pool = [(k, l) for k, l in receiving.items() if l.targets >= 1 and _keep(k)]
    if wr_pool:
        yards_pool = [l.yards for _, l in wr_pool]
        td_pool = [l.touchdowns for _, l in wr_pool]
        for (abbr, name), line in wr_pool:
            score = 0.5 * _normalize(line.yards, yards_pool) + 0.5 * _normalize(line.touchdowns, td_pool)
            candidates.append(AwardCandidate(
                name=name, team_abbr=abbr, position="WR/TE",
                stat_line=f"{line.yards:,} rec yds, {line.touchdowns} TD",
                score=score,
            ))

    return candidates


def offensive_player_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    return sorted(_offensive_candidates(season), key=lambda c: -c.score)[:top_n]


def rookie_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    """Offensive AND defensive rookies, each normalized within their OWN
    rookie sub-pool first (same cross-position technique MVP/OPOY use)
    before being merged into one ranking -- see this module's docstring
    for why this changed from offense-only."""
    candidates = _offensive_candidates(season, rookies_only=True) + _defensive_candidates(season, rookies_only=True)
    return sorted(candidates, key=lambda c: -c.score)[:top_n]


def offensive_rookie_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    """R8 (Awards Page): the real NFL splits Rookie of the Year into an
    offensive and a defensive award (OROY/DROY) rather than ROY's single
    combined ranking above -- this is exactly ROY's own offensive-rookie
    HALF, surfaced on its own rather than merged, no new scoring."""
    return sorted(_offensive_candidates(season, rookies_only=True), key=lambda c: -c.score)[:top_n]


def defensive_rookie_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    """DROY: ROY's defensive-rookie half, surfaced on its own -- see
    offensive_rookie_of_the_year()'s docstring."""
    return sorted(_defensive_candidates(season, rookies_only=True), key=lambda c: -c.score)[:top_n]


def most_valuable_player(season, top_n: int = 5) -> list[AwardCandidate]:
    """MVP = the same normalized offensive-production score OPOY uses,
    blended with the player's own team's win% (Sec 7.4's "team wins"
    term)."""
    win_pct_by_abbr = {abbr: r.win_pct for abbr, r in season.records.items()}
    return mvp_from_candidates(_offensive_candidates(season), win_pct_by_abbr)[:top_n]


def mvp_from_candidates(offensive_candidates: list[AwardCandidate], win_pct_by_abbr: dict) -> list[AwardCandidate]:
    """Pure version of the MVP blend -- takes OPOY-shaped candidates and
    a plain {team_abbr: win_pct} dict rather than a live Season.records.
    Split out for the same reason offensive_candidates_from_stats() was:
    real historical seasons need the identical formula, not a copy."""
    blended = [
        AwardCandidate(name=c.name, team_abbr=c.team_abbr, position=c.position, stat_line=c.stat_line,
                        score=0.4 * win_pct_by_abbr.get(c.team_abbr, 0.0) + 0.6 * c.score)
        for c in offensive_candidates
    ]
    return sorted(blended, key=lambda c: -c.score)


def _known_non_defensive_position_keys() -> set[tuple[str, str]]:
    """(team_abbr, full_name) for every real, live-rostered player whose
    actual position is NOT a genuine defensive one (QB/HB/FB/WR/TE/OL/K/P).
    R2b's real special-teams tackle credit (app/engine/special_teams.py's
    _coverage_tackler) picks a kickoff/punt-return tackler from the
    KICKING/PUNTING team's own WR depth (a real-world "gunner" is most
    often a receiver) -- without this exclusion, a rookie WR who happened
    to make one incidental coverage tackle would show up as a "DEF"
    position DPOY/DROY candidate off that single stat, which is real data
    but not what either award is meant to recognize (a real NFL DPOY/
    DROY ballot is scoped to actual defenders).

    Deliberately an EXCLUSION set, not an inclusion whitelist: an unknown
    name with no live DB match at all (this module's own pure, DB-free
    unit tests against hand-built PlayEvents naming fabricated players,
    or a future real-historical-data caller) is never excluded by this --
    only a POSITIVELY-confirmed real non-defensive player is. Degrades to
    "exclude nothing" (unchanged pre-R2b behavior) if the DB isn't
    reachable at all, same defensive pattern as this module's own
    _prior_season_wins()."""
    from app.models.player import Position
    defensive_positions = {
        Position.EDGE, Position.DT,
        Position.LB,
        Position.CB, Position.S,
    }
    try:
        with get_session() as s:
            players = s.exec(select(Player)).all()
    except Exception:
        return set()
    return {(p.team_abbr, p.full_name) for p in players if p.position not in defensive_positions}


def _defensive_candidates(season, rookies_only: bool = False) -> list[AwardCandidate]:
    """See this module's docstring for the disclosed DPOY weighting.
    Candidate pool: every defender credited with at least one stat this
    season (app/engine/season_stats.py's aggregate_season_defensive_stats,
    built on the real per-play defender attribution in drive_sim.py/
    defensive_box_score.py), with real, positively-confirmed non-
    defensive players excluded (see _known_non_defensive_position_keys'
    own docstring for why that exclusion exists) -- no FURTHER positional
    split beyond that, matching how DPOY is a single, position-agnostic
    real NFL award among actual defenders."""
    defense = aggregate_season_defensive_stats(season)
    non_defenders = _known_non_defensive_position_keys()
    defense = {key: line for key, line in defense.items() if key not in non_defenders}
    rookie_keys = _rookie_keys(season) if rookies_only else None
    return defensive_candidates_from_stats(defense, rookie_keys)


def defensive_candidates_from_stats(defense: dict, rookie_keys: set | None = None) -> list[AwardCandidate]:
    """Pure version of _defensive_candidates -- see offensive_candidates_
    from_stats' docstring for why this split exists."""

    def _keep(key):
        return rookie_keys is None or key in rookie_keys

    pool = [(k, l) for k, l in defense.items() if _keep(k)]
    if not pool:
        return []

    sacks_pool = [l.sacks for _, l in pool]
    ints_pool = [l.interceptions for _, l in pool]
    tfl_pool = [l.tackles_for_loss for _, l in pool]
    tkl_pool = [l.solo_tackles for _, l in pool]
    ff_pool = [l.forced_fumbles for _, l in pool]
    pd_pool = [l.passes_defended for _, l in pool]
    td_pool = [l.defensive_touchdowns for _, l in pool]

    candidates: list[AwardCandidate] = []
    for (abbr, name), line in pool:
        score = (
            0.27 * _normalize(line.sacks, sacks_pool)
            + 0.27 * _normalize(line.interceptions, ints_pool)
            + 0.13 * _normalize(line.tackles_for_loss, tfl_pool)
            + 0.09 * _normalize(line.solo_tackles, tkl_pool)
            + 0.09 * _normalize(line.forced_fumbles, ff_pool)
            + 0.05 * _normalize(line.passes_defended, pd_pool)
            + 0.10 * _normalize(line.defensive_touchdowns, td_pool)
        )
        stat_line = f"{line.solo_tackles} tkl, {line.sacks} sacks, {line.tackles_for_loss} TFL, {line.interceptions} INT, {line.passes_defended} PD"
        if line.defensive_touchdowns:
            stat_line += f", {line.defensive_touchdowns} DEF TD"
        candidates.append(AwardCandidate(
            name=name, team_abbr=abbr, position="DEF",
            stat_line=stat_line,
            score=score,
        ))
    return candidates


def defensive_player_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    return sorted(_defensive_candidates(season), key=lambda c: -c.score)[:top_n]


@dataclass
class AwardsRace:
    mvp: list[AwardCandidate]
    opoy: list[AwardCandidate]
    dpoy: list[AwardCandidate]
    roy: list[AwardCandidate]
    # Empty list when the database has no coaches (a franchise that
    # predates the coach import) -- every consumer treats an empty
    # award the same way it already treats an empty MVP race in week 0.
    coty: list[CoachAwardCandidate] = field(default_factory=list)


def season_award_lists(season, top_n: int = AWARDS_RACE_TOP_N) -> dict[str, list]:
    """Every award's ranked list in one pass -- {"mvp", "opoy", "dpoy",
    "oroy", "droy", "roy", "coty"} -- producing exactly what the
    individual *_of_the_year() functions above return, but aggregating
    the season's box scores ONCE (season_stats' cached aggregates) instead
    of once per award. Used by the Awards page and the end-of-season
    finalization (app/services/season_honors.py), which both need all
    of them at once."""
    from app.engine.season_stats import cached_current_season_aggregates

    passing, rushing, receiving, defense = cached_current_season_aggregates(season)
    rookie_keys = _rookie_keys(season)
    non_defenders = _known_non_defensive_position_keys()
    real_defense = {k: v for k, v in defense.items() if k not in non_defenders}

    offense = offensive_candidates_from_stats(passing, rushing, receiving)
    offense_rookies = offensive_candidates_from_stats(passing, rushing, receiving, rookie_keys)
    defenders = defensive_candidates_from_stats(real_defense)
    defense_rookies = defensive_candidates_from_stats(real_defense, rookie_keys)
    by_score = lambda cands: sorted(cands, key=lambda c: -c.score)[:top_n]  # noqa: E731
    win_pct_by_abbr = {abbr: r.win_pct for abbr, r in season.records.items()}

    return {
        "mvp": mvp_from_candidates(offense, win_pct_by_abbr)[:top_n],
        "opoy": by_score(offense),
        "dpoy": by_score(defenders),
        "oroy": by_score(offense_rookies),
        "droy": by_score(defense_rookies),
        "roy": by_score(offense_rookies + defense_rookies),
        "coty": coach_of_the_year(season, top_n),
    }


def season_awards(season, top_n: int = 5) -> AwardsRace:
    return AwardsRace(
        mvp=most_valuable_player(season, top_n),
        opoy=offensive_player_of_the_year(season, top_n),
        dpoy=defensive_player_of_the_year(season, top_n),
        roy=rookie_of_the_year(season, top_n),
        coty=coach_of_the_year(season, top_n),
    )


@dataclass
class ProBowlStarter:
    name: str
    team_abbr: str
    position: str  # generic position-group label (position_groups.py's QUOTA_GROUPS)
    ovr: int
    # Filled by pro_bowl_rosters() (the real end-of-season selection);
    # left at their defaults by the older OVR-only pro_bowl_starters().
    player_id: str = ""
    stat_line: str = ""
    score: float = 0.0


# Real starter COUNTS per side loosely match a real Pro Bowl roster's own
# shape (2 WR/T/G/EDGE/DT/CB/S, 3 LB, 1 everything else) -- this module's
# own choice, not a GDD value. Buckets are position_groups.py's generic
# groups (the Roster page's Team Quota grouping), not Madden's granular
# per-slot positions. K/P are their own "special" bucket.
PRO_BOWL_OFFENSE_STARTER_COUNTS: dict[str, int] = {"QB": 1, "RB": 1, "WR": 2, "TE": 1, "C": 1, "G": 2, "T": 2}
PRO_BOWL_DEFENSE_STARTER_COUNTS: dict[str, int] = {"EDGE": 2, "DT": 2, "LB": 3, "CB": 2, "S": 2}
PRO_BOWL_SPECIAL_STARTER_COUNTS: dict[str, int] = {"K": 1, "P": 1}
# Reserves (Brian's ask, 2026-09-14: "starters + reserves"): a second,
# smaller tier per group, roughly a real Pro Bowl roster's alternates.
# Module's own choice. No K/P reserves -- one specialist per side is
# already the real shape.
PRO_BOWL_RESERVE_COUNTS: dict[str, int] = {
    "QB": 2, "RB": 1, "WR": 2, "TE": 1, "C": 1, "G": 1, "T": 1,
    "EDGE": 2, "DT": 1, "LB": 2, "CB": 2, "S": 1,
}


def _pro_bowl_side(conf_players: list, counts: dict[str, int]) -> list[ProBowlStarter]:
    from app.engine.position_groups import POSITION_TO_GROUP

    by_group: dict[str, list] = {}
    for p in conf_players:
        by_group.setdefault(POSITION_TO_GROUP[p.position], []).append(p)

    starters: list[ProBowlStarter] = []
    for group, n in counts.items():
        ranked = sorted(by_group.get(group, []), key=lambda p: -p.overall_rating)[:n]
        starters.extend(
            ProBowlStarter(name=p.full_name, team_abbr=p.team_abbr, position=group, ovr=p.overall_rating)
            for p in ranked
        )
    return starters


def pro_bowl_starters(season, conf: str) -> dict[str, list[ProBowlStarter]]:
    """{"offense": [...], "defense": [...], "special": [...]} of real
    ProBowlStarter rows for the given conference ("AFC"/"NFC"). `season`
    is accepted (unused) for the same call shape as this module's other
    *_of_the_year functions -- overall_rating is a roster-DB property,
    not something derived from season play, so nothing here actually
    needs it yet."""
    from app.data.teams import TEAMS_BY_ABBR
    from sqlmodel import select

    conf_team_abbrs = {abbr for abbr, info in TEAMS_BY_ABBR.items() if info.conference == conf}
    with get_session() as s:
        conf_players = list(s.exec(select(Player).where(Player.team_abbr.in_(conf_team_abbrs))))  # type: ignore[union-attr]

    return {
        "offense": _pro_bowl_side(conf_players, PRO_BOWL_OFFENSE_STARTER_COUNTS),
        "defense": _pro_bowl_side(conf_players, PRO_BOWL_DEFENSE_STARTER_COUNTS),
        "special": _pro_bowl_side(conf_players, PRO_BOWL_SPECIAL_STARTER_COUNTS),
    }


# --- End-of-season Pro Bowl selection (Brian's decision, 2026-09-14) -------
#
# Selected ONCE, right after the final regular-season game (see
# app/services/season_honors.py), per conference. Brian's call: season
# stats blended with OVR, scored with the SAME per-position stat scoring
# the awards already use (offensive_candidates_from_stats /
# defensive_candidates_from_stats), with OVR as the tiebreak -- and as the
# whole signal for groups this engine has no per-player stat line for
# (OL, K, P). The 0.7/0.3 split is this module's own choice: large enough
# that a real season of production beats a higher-rated backup who barely
# played, small enough that OVR still separates two similar stat lines.
PRO_BOWL_STAT_WEIGHT = 0.7

# Which awards candidate pool scores each position group. A group missing
# here (C/G/T/K/P) is scored on OVR alone.
_PRO_BOWL_STAT_POOL = {
    "QB": "QB", "RB": "RB", "WR": "WR/TE", "TE": "WR/TE",
    "EDGE": "DEF", "DT": "DEF", "LB": "DEF", "CB": "DEF", "S": "DEF",
}


def pro_bowl_rosters(season) -> dict[str, dict[str, list[ProBowlStarter]]]:
    """{"AFC": {"offense", "defense", "special", "reserves"}, "NFC": {...}}
    of real ProBowlStarter rows (player_id/stat_line/score filled in)."""
    from app.data.teams import TEAMS_BY_ABBR
    from app.engine.position_groups import POSITION_TO_GROUP
    from app.engine.season_stats import cached_current_season_aggregates

    passing, rushing, receiving, defense = cached_current_season_aggregates(season)
    stat_candidates: dict[tuple[str, str, str], AwardCandidate] = {}
    for c in offensive_candidates_from_stats(passing, rushing, receiving) + defensive_candidates_from_stats(defense):
        stat_candidates[(c.team_abbr, c.name, c.position)] = c

    with get_session() as s:
        players = list(s.exec(select(Player).where(Player.team_abbr != None)))  # noqa: E711

    by_conf_group: dict[tuple[str, str], list[ProBowlStarter]] = {}
    for p in players:
        info = TEAMS_BY_ABBR.get(p.team_abbr)
        if info is None:
            continue
        group = POSITION_TO_GROUP[p.position]
        ovr_term = p.overall_rating / 99.0
        pool = _PRO_BOWL_STAT_POOL.get(group)
        cand = stat_candidates.get((p.team_abbr, p.full_name, pool)) if pool else None
        if pool:
            score = PRO_BOWL_STAT_WEIGHT * (cand.score if cand else 0.0) + (1 - PRO_BOWL_STAT_WEIGHT) * ovr_term
        else:
            score = ovr_term
        by_conf_group.setdefault((info.conference, group), []).append(ProBowlStarter(
            name=p.full_name, team_abbr=p.team_abbr, position=group, ovr=p.overall_rating,
            player_id=p.player_id, stat_line=cand.stat_line if cand else "", score=round(score, 4),
        ))

    rosters: dict[str, dict[str, list[ProBowlStarter]]] = {}
    for conf in ("AFC", "NFC"):
        sides: dict[str, list[ProBowlStarter]] = {"offense": [], "defense": [], "special": [], "reserves": []}
        for side, counts in (("offense", PRO_BOWL_OFFENSE_STARTER_COUNTS),
                             ("defense", PRO_BOWL_DEFENSE_STARTER_COUNTS),
                             ("special", PRO_BOWL_SPECIAL_STARTER_COUNTS)):
            for group, n in counts.items():
                ranked = sorted(by_conf_group.get((conf, group), []), key=lambda r: (-r.score, -r.ovr, r.name))
                sides[side].extend(ranked[:n])
                sides["reserves"].extend(ranked[n:n + PRO_BOWL_RESERVE_COUNTS.get(group, 0)])
        rosters[conf] = sides
    return rosters


# --- Super Bowl MVP (Brian's ask, 2026-09-14) ------------------------------
#
# Chosen from the Super Bowl's own real box score, winning team only (the
# real award essentially always goes to the winner). Per-player "game
# impact" points -- this module's own weights, a fantasy-football-style
# yardage/TD/turnover scale since no GDD formula exists:
#   passing:   0.04/yd, 4/TD, -2/INT
#   rushing:   0.1/yd,  6/TD, -2/fumble lost
#   receiving: 0.1/yd,  6/TD, 0.5/reception
#   defense:   4/sack, 5/INT, 6/defensive TD, 3/forced fumble,
#              1/tackle-for-loss, 1/pass defended, 0.5/solo tackle

def _sb_stat_segments(passing, rushing, receiving, defense) -> list[tuple[float, str]]:
    """(weight, text) segments for one player's stat line, strongest
    contribution first."""
    segs: list[tuple[float, str]] = []
    if passing and passing.attempts:
        segs.append((passing.yards * 0.04 + passing.touchdowns * 4,
                     f"{passing.yards} Passing Yards | {passing.touchdowns} TD | {passing.interceptions} INT"))
    if rushing and rushing.carries and (rushing.yards >= 20 or rushing.touchdowns):
        segs.append((rushing.yards * 0.1 + rushing.touchdowns * 6,
                     f"{rushing.yards} Rushing Yards | {rushing.touchdowns} TD"))
    if receiving and receiving.receptions:
        segs.append((receiving.yards * 0.1 + receiving.touchdowns * 6,
                     f"{receiving.receptions} Receptions | {receiving.yards} Receiving Yards | {receiving.touchdowns} TD"))
    if defense:
        bits = []
        if defense.sacks:
            bits.append(f"{defense.sacks} Sack{'s' if defense.sacks != 1 else ''}")
        if defense.interceptions:
            bits.append(f"{defense.interceptions} INT")
        if defense.defensive_touchdowns:
            bits.append(f"{defense.defensive_touchdowns} TD")
        if defense.forced_fumbles:
            bits.append(f"{defense.forced_fumbles} FF")
        bits.append(f"{defense.solo_tackles} Tackles")
        segs.append((defense.sacks * 4 + defense.interceptions * 5 + defense.defensive_touchdowns * 6
                     + defense.forced_fumbles * 3, " | ".join(bits)))
    return sorted(segs, key=lambda s: -s[0])


def super_bowl_mvp(plays, winner_abbr: str) -> dict | None:
    """{"name", "team_abbr", "position", "player_id", "stat_line", "score"}
    for the winning team's highest-impact player in this game, or None
    if nobody on the winning side recorded a stat (not reachable in a
    real simulated game, but never fabricated)."""
    from app.engine.box_score import build_box_score
    from app.engine.defensive_box_score import build_defensive_box_score

    box = build_box_score(plays, winner_abbr)
    defense = build_defensive_box_score(plays, winner_abbr)

    names: set[str] = set()
    passing = {l.name: l for l in box.passing}
    rushing = {l.name: l for l in box.rushing}
    receiving = {l.name: l for l in box.receiving}
    defensive = {l.name: l for l in defense}
    for pool in (passing, rushing, receiving, defensive):
        names.update(pool)
    if not names:
        return None

    def impact(name: str) -> float:
        total = 0.0
        if name in passing:
            l = passing[name]
            total += l.yards * 0.04 + l.touchdowns * 4 - l.interceptions * 2
        if name in rushing:
            l = rushing[name]
            total += l.yards * 0.1 + l.touchdowns * 6 - l.fumbles_lost * 2
        if name in receiving:
            l = receiving[name]
            total += l.yards * 0.1 + l.touchdowns * 6 + l.receptions * 0.5
        if name in defensive:
            l = defensive[name]
            total += (l.sacks * 4 + l.interceptions * 5 + l.defensive_touchdowns * 6 + l.forced_fumbles * 3
                      + l.tackles_for_loss + l.passes_defended + l.solo_tackles * 0.5)
        return total

    best = max(sorted(names), key=impact)
    segments = _sb_stat_segments(passing.get(best), rushing.get(best), receiving.get(best), defensive.get(best))

    position, player_id = "", ""
    with get_session() as s:
        match = next((p for p in s.exec(select(Player).where(Player.team_abbr == winner_abbr)) if p.full_name == best), None)
    if match is not None:
        position, player_id = match.position.value, match.player_id

    return {
        "name": best, "team_abbr": winner_abbr, "position": position, "player_id": player_id,
        "stat_line": " | ".join(text for _, text in segments[:2]),
        "score": round(impact(best), 2),
    }


def super_bowl_numeral(season_year_value: int) -> str:
    """The real Super Bowl numbering: the 2025 season's game was Super
    Bowl LX, so N = season year - 1965 (2026 season -> LXI)."""
    n = season_year_value - 1965
    if n <= 0:
        return str(season_year_value)
    out = ""
    for value, sym in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                       (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += sym
            n -= value
    return out
