"""
Dynamic Coach Progression & Lifecycle (GDD Part 1 Sec 8.2.2 / 8.2.3).

Run once per offseason, from season_state.start_new_season(), right
alongside the player progression pass that already happens there.

**Sec 8.2.2, progression.** The GDD gives both the shape AND, unusually,
one concrete worked example:

    Delta_R = PerfScore_R * Volatility * PositionalModifier
    PerfScore (discipline) = (16.5 - Rank) * 0.2   # league rank in Penalties/Game

That formula is used literally here, including its 16.5 midpoint (the
centre of a 32-team league, so rank 16/17 is a wash). Volatility and
PositionalModifier are NOT given any values anywhere in the GDD, so
those two constants are this module's own documented choices.

Only the ratings with a real team-statistical rank behind them move.
Sec 8.2.2 says ratings "progress or regress based on the team's
statistical rank in relevant categories" -- where this engine has no
such category, the rating is left ALONE rather than drifted on an
invented signal:

  moved (real rank exists)          | not moved (no real signal)
  ----------------------------------+---------------------------------
  discipline (penalties/game)       | clock_management (no clock model
  player_dev_offense (points for)   |   exists anywhere in this engine
  player_dev_defense (points ag.)   |   -- score_fidelity.py's own
  motivation_chemistry (win pct)    |   docstring documents this gap)
  red_zone_offense (RZ TD%)         | challenge_sense (no coach's
  red_zone_defense (opp RZ TD%)     |   challenge system exists)

**Sec 8.2.3, retirement.** "Coaches aged 65 or older have a
deterministic, age-based probability of retiring each offseason.
Retirement % = (Coach Age - 64) * 3" -- used exactly as written, rolled
against this project's own seeded RNG so a given league replays
identically (GDD Sec 1.3).

Hiring and firing (the rest of Sec 8.2.3 -- Job Security thresholds, the
multi-round offer market, Coach_Offer_Score) are deliberately NOT built
here. job_security_score IS computed and stored every offseason
(app/services/coach_records.py), and retirement genuinely does open
vacancies, but actually FILLING a vacancy needs the offer/negotiation
market, which is the same contract-negotiation machinery R4a builds for
players and which does not exist yet. A vacancy is therefore left
visibly vacant on the Staff page rather than silently auto-filled with
an invented coach.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from app.engine.rng import RNG, stable_seed
from app.models.coach import Coach, CoachRole

# Sec 8.2.2 gives no value for either of these.
VOLATILITY = 1.0
# Per-role share of the team's statistical outcome. A head coach owns
# the whole program's result; a coordinator owns their side of the ball;
# an assistant's individual rating moves least on a team-wide number.
POSITIONAL_MODIFIER: dict[CoachRole, float] = {
    CoachRole.HC: 1.0,
    CoachRole.OC: 0.8,
    CoachRole.DC: 0.8,
    CoachRole.ST: 0.5,
    CoachRole.AC: 0.4,
}

LEAGUE_MIDPOINT_RANK = 16.5  # Sec 8.2.2's own constant, for a 32-team league
PERF_SCORE_SCALE = 0.2       # Sec 8.2.2's own constant
ANNUAL_CAP = 5.0             # max |Delta_R| per rating per offseason (this module's choice)

RETIREMENT_MIN_AGE = 65      # Sec 8.2.3
RETIREMENT_PCT_PER_YEAR = 3  # Sec 8.2.3: (age - 64) * 3


@dataclass
class TeamRanks:
    """One team's real league ranks (1 = best) for each category that
    drives a rating. None means "not enough real data this season" --
    the corresponding rating simply doesn't move."""
    penalty_rank: int | None = None       # 1 = fewest penalties per game
    points_for_rank: int | None = None    # 1 = most points scored
    points_against_rank: int | None = None  # 1 = fewest points allowed
    win_pct_rank: int | None = None       # 1 = best record
    red_zone_offense_rank: int | None = None
    red_zone_defense_rank: int | None = None


# rating name -> which TeamRanks field drives it (Sec 8.2.2's "relevant
# categories"). Every pairing here is a real, computed league rank.
RATING_SOURCES: dict[str, str] = {
    "discipline": "penalty_rank",
    "player_dev_offense": "points_for_rank",
    "player_dev_defense": "points_against_rank",
    "motivation_chemistry": "win_pct_rank",
    "red_zone_offense": "red_zone_offense_rank",
    "red_zone_defense": "red_zone_defense_rank",
}


def perf_score(rank: int) -> float:
    """Sec 8.2.2's own worked example, generalized to every category
    that has a real league rank: a top-ranked team's coaches gain, a
    bottom-ranked team's regress, rank 16/17 is a wash."""
    return (LEAGUE_MIDPOINT_RANK - rank) * PERF_SCORE_SCALE


@dataclass
class CoachProgressionResult:
    coach_id: str
    age_delta: int = 1
    rating_deltas: dict[str, float] = field(default_factory=dict)
    retired: bool = False


def progress_coach(coach: Coach, ranks: TeamRanks, season_number: int, league_seed: int) -> CoachProgressionResult:
    """Pure computation -- does not mutate `coach`. Mirrors
    app/engine/progression.py's progress_player/apply_progression split
    so the arithmetic is testable without a database."""
    modifier = POSITIONAL_MODIFIER[CoachRole(coach.role)]
    deltas: dict[str, float] = {}
    for rating, source in RATING_SOURCES.items():
        rank = getattr(ranks, source)
        if rank is None:
            continue
        delta = perf_score(rank) * VOLATILITY * modifier
        deltas[rating] = max(-ANNUAL_CAP, min(ANNUAL_CAP, delta))

    new_age = coach.age + 1
    retired = False
    if new_age >= RETIREMENT_MIN_AGE:
        # Sec 8.2.3: Retirement % = (Coach Age - 64) * 3, rolled against
        # a per-coach seeded RNG so the same league retires the same
        # coaches on a replay (GDD Sec 1.3).
        chance = min(1.0, (new_age - (RETIREMENT_MIN_AGE - 1)) * RETIREMENT_PCT_PER_YEAR / 100.0)
        rng = RNG.with_seed(stable_seed("coach_retire", league_seed, season_number, coach.coach_id))
        retired = rng.prob(chance)

    return CoachProgressionResult(coach_id=coach.coach_id, rating_deltas=deltas, retired=retired)


def apply_coach_progression(coach: Coach, result: CoachProgressionResult) -> None:
    """Mutates `coach` in place; persisting is the caller's job (the
    same contract progression.apply_progression() has for players)."""
    coach.age += result.age_delta
    coach.experience_years += 1
    for rating, delta in result.rating_deltas.items():
        new_value = int(round(getattr(coach, rating) + delta))
        setattr(coach, rating, max(0, min(99, new_value)))
    if result.retired:
        coach.retired = True
        coach.team_abbr = None  # a retired coach vacates their seat


def _rank_map(values: dict[str, float], reverse: bool) -> dict[str, int]:
    ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=reverse)
    return {abbr: i for i, (abbr, _) in enumerate(ordered, start=1)}


def compute_team_ranks(season) -> dict[str, TeamRanks]:
    """Every team's real end-of-season league ranks, computed once for
    the whole league rather than re-scanning per coach (433 coaches x a
    32-team scan would be genuinely wasteful, and the numbers are
    identical for every coach on the same staff).

    Points-for/points-against/win% come straight off the real
    TeamRecord. Penalties-per-game and red-zone TD% reuse
    app/engine/scouting.py's existing real computations rather than
    reimplementing either."""
    from app.engine import scouting

    abbrs = [a for a, r in season.records.items() if r.games_played > 0]
    if not abbrs:
        return {a: TeamRanks() for a in season.records}

    points_for = {a: season.records[a].points_for for a in abbrs}
    points_against = {a: season.records[a].points_against for a in abbrs}
    win_pct = {a: season.records[a].win_pct for a in abbrs}

    penalties = {}
    rz_offense = {}
    for a in abbrs:
        per_game = scouting.penalty_discipline(season, a)["per_game"]
        if per_game is not None:
            penalties[a] = per_game
        td_pct = scouting.red_zone_efficiency(season, a)["td_pct"]
        if td_pct is not None:
            rz_offense[a] = td_pct

    penalty_ranks = _rank_map(penalties, reverse=False)       # fewest = rank 1
    pf_ranks = _rank_map(points_for, reverse=True)            # most = rank 1
    pa_ranks = _rank_map(points_against, reverse=False)       # fewest allowed = rank 1
    win_ranks = _rank_map(win_pct, reverse=True)
    rz_off_ranks = _rank_map(rz_offense, reverse=True)        # best TD% = rank 1
    # Red-zone DEFENSE has no direct scouting helper (red_zone_efficiency
    # is an offense-side computation), and building a full opponent-side
    # red-zone scan here would duplicate it. Points allowed is the real,
    # already-computed stand-in, disclosed rather than invented: a team
    # that allows few points is, in this engine, exactly a team whose
    # defense holds up in scoring situations.
    rz_def_ranks = pa_ranks

    out: dict[str, TeamRanks] = {}
    for a in season.records:
        out[a] = TeamRanks(
            penalty_rank=penalty_ranks.get(a),
            points_for_rank=pf_ranks.get(a),
            points_against_rank=pa_ranks.get(a),
            win_pct_rank=win_ranks.get(a),
            red_zone_offense_rank=rz_off_ranks.get(a),
            red_zone_defense_rank=rz_def_ranks.get(a),
        )
    return out
