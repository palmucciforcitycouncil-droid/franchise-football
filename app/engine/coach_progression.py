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
invented signal. All six performance ratings Coach still carries have a
real category behind them:

  discipline             -> penalties/game
  player_dev_offense     -> points for
  player_dev_defense     -> points against
  motivation_chemistry   -> win pct
  red_zone_offense       -> RZ TD%
  red_zone_defense       -> opp RZ TD%

(`clock_management` and `challenge_sense` used to sit here as
permanently-excluded no-signal ratings -- no clock model and no coach's
challenge system exist anywhere in this engine. Rather than progress
ratings with no signal to move on, they were removed from `Coach`
entirely on 2026-09-11; see ROADMAP.md Sec 4c.)

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
# R16: player_dev_offense/player_dev_defense are REMOVED from this table
# -- they're now computed averages of the 8 granular ratings (app/models/
# coach.py), not stored fields, and those 8 ratings have their OWN real
# movement mechanism below (_position_rating_deltas()), not this one.
RATING_SOURCES: dict[str, str] = {
    "discipline": "penalty_rank",
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


# R16 Sec 1/2 (docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md): the 8
# granular position-group ratings, keyed to whichever side of the ball
# they're on -- there's no real per-unit rank for e.g. "OL play" alone
# in this engine (coach_hiring.py's own JSS formulas already disclose
# the same gap for OC/DC scoring), so each group's outcome modifier
# reuses the real, already-computed offense/defense-wide rank, same
# "closest real substitute" precedent as everywhere else in this module.
_POSITION_RATING_SIDE: dict[str, str] = {
    "qb_coaching": "offense", "rb_coaching": "offense", "wr_coaching": "offense", "ol_coaching": "offense",
    "dl_coaching": "defense", "lb_coaching": "defense", "secondary_coaching": "defense",
}
# Reputation and the 8 granular ratings [tune]: this project's own
# documented growth constants, separate from Sec 8.2.2's GDD-given
# ANNUAL_CAP (which governs discipline/motivation_chemistry/etc. only).
REPUTATION_ANNUAL_CAP = 4.0
REPUTATION_TITLE_BONUS = 3.0        # a conference title this season
REPUTATION_SUPER_BOWL_BONUS = 6.0   # a Super Bowl win this season
POSITION_RATING_ANNUAL_CAP = 4.0
# How much of a group's total seasonal accumulator points converts into
# real rating growth -- [tune], a real disclosed starting point.
ACCUMULATOR_TO_RATING_SCALE = 0.03


def _position_rating_deltas(coach: Coach, ranks: TeamRanks, modifier: float,
                             accumulator_totals: dict[str, float] | None) -> dict[str, float]:
    """R16 Sec 2: the 8 granular ratings' own progression -- base weekly
    practice (this season's real accumulated Focus Area investment,
    app/services/coach_focus_accumulator.py) plus a real unit/team
    outcome modifier, both scaled by organizational tier (`modifier`,
    the SAME POSITIONAL_MODIFIER used for every other rating here --
    Brian's "proportional to the level of coach they are," clarified in
    planning to mean the coach's OWN progression speed by role tier)."""
    deltas: dict[str, float] = {}
    accumulator_totals = accumulator_totals or {}
    from app.models.coach import FOCUS_POSITION_GROUPS
    # Which position groups THIS coach could plausibly have been
    # investing in, from their own available focus menu -- e.g. an OC
    # only ever accrues qb/rb/wr/ol_coaching practice, never dl_coaching.
    from app.models.coach import focus_options_for
    own_groups: set[str] = set()
    for option in focus_options_for(coach):
        for group in FOCUS_POSITION_GROUPS.get(option, []):
            own_groups.add(group)
    group_to_rating = {
        "QB": "qb_coaching", "RB": "rb_coaching", "WR": "wr_coaching", "TE": "wr_coaching",
        "OL": "ol_coaching", "DL": "dl_coaching", "LB": "lb_coaching",
        "CB": "secondary_coaching", "S": "secondary_coaching", "K": "st_coaching", "P": "st_coaching",
    }
    for rating, side in _POSITION_RATING_SIDE.items():
        rank = ranks.points_for_rank if side == "offense" else ranks.points_against_rank
        outcome = perf_score(rank) * VOLATILITY if rank is not None else 0.0
        practice = sum(accumulator_totals.get(g, 0.0) for g, r in group_to_rating.items()
                       if r == rating and g in own_groups) * ACCUMULATOR_TO_RATING_SCALE
        delta = (outcome + practice) * modifier
        deltas[rating] = max(-POSITION_RATING_ANNUAL_CAP, min(POSITION_RATING_ANNUAL_CAP, delta))
    return deltas


def _reputation_delta(ranks: TeamRanks, achievement: str | None, modifier: float) -> float:
    """R16 Sec 1: reputation is now earned, not frozen at import -- a
    continuous nudge from this season's real win-pct rank (same
    perf_score(rank) shape as every other rating here) plus a real,
    discrete bonus for a conference title or Super Bowl won THIS season
    (`achievement`, from coach_hiring.best_achievement() -- real,
    already-computed, not a new signal)."""
    outcome = perf_score(ranks.win_pct_rank) * VOLATILITY if ranks.win_pct_rank is not None else 0.0
    bonus = 0.0
    if achievement == "super_bowl":
        bonus = REPUTATION_SUPER_BOWL_BONUS
    elif achievement == "conference_title":
        bonus = REPUTATION_TITLE_BONUS
    delta = (outcome * modifier) + bonus
    return max(-REPUTATION_ANNUAL_CAP, min(REPUTATION_ANNUAL_CAP + bonus, delta))


def progress_coach(coach: Coach, ranks: TeamRanks, season_number: int, league_seed: int,
                    accumulator_totals: dict[str, float] | None = None,
                    achievement: str | None = None) -> CoachProgressionResult:
    """Pure computation -- does not mutate `coach`. Mirrors
    app/engine/progression.py's progress_player/apply_progression split
    so the arithmetic is testable without a database.

    `accumulator_totals` (this season's real per-position-group Focus
    Area investment, app/services/coach_focus_accumulator.py) and
    `achievement` (this season's real playoff outcome bucket, e.g.
    "super_bowl"/"conference_title"/None, from coach_hiring.best_
    achievement()) are optional -- omitting them (the pre-R16 call
    shape) simply skips the R16 granular-rating/reputation movement
    below, so an isolated test of the ORIGINAL Sec 8.2.2 ratings still
    works unchanged."""
    modifier = POSITIONAL_MODIFIER[CoachRole(coach.role)]
    deltas: dict[str, float] = {}
    for rating, source in RATING_SOURCES.items():
        rank = getattr(ranks, source)
        if rank is None:
            continue
        delta = perf_score(rank) * VOLATILITY * modifier
        deltas[rating] = max(-ANNUAL_CAP, min(ANNUAL_CAP, delta))

    if accumulator_totals is not None or achievement is not None:
        deltas.update(_position_rating_deltas(coach, ranks, modifier, accumulator_totals))
        deltas["reputation"] = _reputation_delta(ranks, achievement, modifier)

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


# R16 Sec 3: the 8 granular ratings, for the Coaching Tree drift below.
_POSITION_RATINGS = (
    "qb_coaching", "rb_coaching", "wr_coaching", "ol_coaching",
    "dl_coaching", "lb_coaching", "secondary_coaching", "st_coaching",
)
# How far a coach drifts toward their lineage source each offseason --
# [tune], a real disclosed starting point for the post-build playtest.
COACHING_TREE_DRIFT = 0.05


def _drift_toward(coach: Coach, source: Coach, fraction: float) -> None:
    for rating in _POSITION_RATINGS:
        current = getattr(coach, rating)
        target = getattr(source, rating)
        setattr(coach, rating, max(0, min(99, int(round(current + (target - current) * fraction)))))


def apply_coaching_tree_drift(staff: list[Coach]) -> None:
    """R16 Sec 3, "the Coaching Tree" -- a real, marketed feature: every
    OC/DC's 8 ratings drift toward their team's HC's; every AC's drift
    toward their ALIGNED coordinator's (OC if offense-side, DC if
    defense-side, per Coach.primary_side -- a real, rating-based signal,
    not a specialty-text lookup, so it can never disagree with the
    numbers driving everything else). A Special-Teams-side AC drifts
    directly toward the HC (no ST coordinator exists to align with).
    Mutates in place; called once per team, AFTER that team's own
    progress_coach()/apply_coach_progression() pass so drift moves
    against this season's ALREADY-updated ratings, not last season's."""
    head = next((c for c in staff if CoachRole(c.role) is CoachRole.HC), None)
    if head is None:
        return
    oc = next((c for c in staff if CoachRole(c.role) is CoachRole.OC), None)
    dc = next((c for c in staff if CoachRole(c.role) is CoachRole.DC), None)

    for coach in staff:
        role = CoachRole(coach.role)
        if role in (CoachRole.OC, CoachRole.DC):
            _drift_toward(coach, head, COACHING_TREE_DRIFT)
        elif role is CoachRole.AC:
            side = coach.primary_side
            source = oc if side == "Offense" else dc if side == "Defense" else head
            if source is not None:
                _drift_toward(coach, source, COACHING_TREE_DRIFT)


# A real margin, not a hair-trigger -- [tune]: how much higher a
# DIFFERENT group's rating needs to be than the current specialty's own
# group before relabeling, so noise doesn't flip a title back and forth
# season to season.
SPECIALTY_RELABEL_MARGIN = 8.0

# specialty group -> the position-group key it maps to (Sec 5's own
# FOCUS_POSITION_GROUPS shares this shape) -- only REAL, relabel-able
# position specialties are covered; a generic/unmapped specialty (e.g.
# "Passing Game") is left alone rather than guessed at.
_SPECIALTY_GROUP: dict[str, str] = {
    "Quarterbacks": "QB", "Quarterbacks (Assistant)": "QB",
    "Running Backs": "RB", "Wide Receivers": "WR", "Tight Ends": "TE",
    "Offensive Line": "OL", "Offensive Line (Assistant)": "OL",
    "Defensive Line": "DL", "Linebackers": "LB",
    "Secondary": "CB", "Safeties": "CB", "Cornerbacks": "CB",
    "Special Teams": "K", "Special Teams (Assistant)": "K",
}
_GROUP_SPECIALTY = {
    "QB": "Quarterbacks", "RB": "Running Backs", "WR": "Wide Receivers", "TE": "Tight Ends",
    "OL": "Offensive Line", "DL": "Defensive Line", "LB": "Linebackers", "CB": "Secondary", "K": "Special Teams",
}
_GROUP_RATING = {
    "QB": "qb_coaching", "RB": "rb_coaching", "WR": "wr_coaching", "TE": "wr_coaching",
    "OL": "ol_coaching", "DL": "dl_coaching", "LB": "lb_coaching", "CB": "secondary_coaching", "K": "st_coaching",
}


def relabel_specialty_if_needed(coach: Coach) -> str | None:
    """R16 Sec 1: "specialty can change" -- if a DIFFERENT group's
    rating now clearly beats the coach's CURRENT specialty's own group
    rating (by SPECIALTY_RELABEL_MARGIN, so a real career shift, not
    noise), relabel them. AC only (HC/OC/DC's role already says what
    they do); a coach whose specialty doesn't map to a known group
    (e.g. "Passing Game") is left alone. Mutates `coach.specialty` in
    place; returns the new specialty if it changed, else None."""
    if CoachRole(coach.role) is not CoachRole.AC:
        return None
    current_group = _SPECIALTY_GROUP.get(coach.specialty or "")
    if current_group is None:
        return None
    current_rating = getattr(coach, _GROUP_RATING[current_group])
    best_group, best_rating = current_group, current_rating
    for group, rating_attr in _GROUP_RATING.items():
        value = getattr(coach, rating_attr)
        if value > best_rating:
            best_group, best_rating = group, value
    if best_group != current_group and best_rating - current_rating >= SPECIALTY_RELABEL_MARGIN:
        coach.specialty = _GROUP_SPECIALTY[best_group]
        return coach.specialty
    return None


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
