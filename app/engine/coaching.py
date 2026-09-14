"""
Coaching effects on the simulation (GDD Part 1 Sec 7.7.2.2/7.7.2.3,
Sec 7.7.3's "Weekly strategy profile (Off + Def + ST) locked at
kickoff"; ROADMAP.md R3).

This is the layer that makes a real coaching staff actually *do*
something in a game, rather than being a roster of names on a page. It
deliberately mirrors app/engine/gameplan.py's shape -- every function
takes a `StaffEffect | None` and returns a zero/no-op bias for None --
because that's the contract drive_sim.py/defensive_ai.py already thread
through the whole play loop for the Weekly Gameplan, and reusing it
means coaches plug into the same call sites instead of needing a second,
parallel mechanism.

**The important difference from Gameplan:** a Weekly Gameplan exists
only for the USER's team (every AI team passes None). A StaffEffect
exists for all 32, because all 32 have a real staff. So this is the
first system in this engine that gives every team a distinct
play-calling identity -- before it, every AI team called plays from the
identical league-average baseline, and the only thing separating them
was their players.

Filling two hooks the engine's own comments had already marked as
blocked on a Coach entity existing:
- drive_sim.py's Penalty System header: "No Team_Discipline_Modifier/
  Coach_Modifier: neither a 'discipline' player attribute nor a Coach
  entity exists in the real data." A head coach's `discipline` rating
  (Sec 7.7.2.3, and Sec 7.7.4's "coach discipline modulates team-level
  penalty rates") now supplies exactly that modifier.
- simulate_drive()'s docstring: "offense_ratings is only used for
  aggression (4th-down tendency) -- a coaching-tendency proxy until a
  real Coach entity exists (Post-MVP)." The proxy is still there as the
  floor; the real OC/HC `offensive_aggression` slider now adds to it.

Calibration: every bias below is bounded to roughly HALF the magnitude
of the equivalent Weekly Gameplan lever. That's deliberate. A gameplan
is an explicit weekly choice the user makes and expects to feel; a
staff's tendencies apply to every team in every game all season, so an
equally-strong dial would drown out the player-attribute-driven engine
that Sec 6.6's whole play-calling model rests on, and would invalidate
tests/test_stat_realism.py's league-wide calibration. The slider->bias
scales here are this module's own documented choices -- GDD Sec 7.7.2.2
defines the sliders and their direction but gives no formula converting
a 0-100 slider into a probability shift, the same gap gameplan.py's own
docstring notes for its option tooltips.

**R13 (Coach Focus Areas, docs/R13_COACH_FOCUS_AREA_SPECIFICATION.md):**
build_staff_effect() used to gather each slider by ROLE (the OC's tendency
sliders always drove offense, the DC's always drove defense, every coach's
dev ratings were always pooled). It now gathers by each coach's OWN chosen
`focus_area` instead -- a coach not focused on a bucket contributes NOTHING
to it, full stop. This is a REALLOCATION, not an added power source: the
same `LeagueBaseline` centering below still guarantees a staff can only move
its own team relative to the league, never move the league itself, exactly
as before. `_weighted_blend()` is the one new primitive this required --
everything downstream of it (the StaffEffect fields, every accessor
function) is unchanged from the pre-R13 shape.
"""
from __future__ import annotations
from dataclasses import dataclass

from app.models.coach import (
    Coach, CoachRole, FOCUS_OF_GAMEPLAN, FOCUS_DF_GAMEPLAN, FOCUS_BALANCED_GAMEPLAN,
    FOCUS_DEVELOPMENT, FOCUS_SPECIAL_TEAMS, FOCUS_TRAINING,
)

# Rating -> bias scales. A 0-100 rating is read as its distance from the
# LEAGUE AVERAGE for that rating (see LeagueBaseline below), scaled into
# [-1, 1], then multiplied by the scale here to get the actual shift
# applied at the call site.
PASS_MIX_SCALE = 0.08          # run_pass_tendency -> base pass probability
RZ_PASS_SCALE = 0.10           # red_zone_offense_bias -> extra inside the 20
FOURTH_DOWN_SCALE = 0.10       # offensive_aggression -> go-for-it chance
TWO_POINT_SCALE = 0.10         # two_point_tendency -> 2-pt conversion attempt chance
BLITZ_SCALE = 0.10             # blitz_rate -> blitz chance
RZ_BLITZ_SCALE = 0.06          # red_zone_defense_bias -> extra inside the 20
COVERAGE_SWING = 0.30          # coverage_mix -> how far man/zone can move off the 40% default
FOURTH_DOWN_DEFENSE_SCALE = 0.05  # fourth_down_defense -> short-yardage run-tactic commitment
FG_RANGE_SCALE = 3.0           # special_teams_focus -> yards of extra FG-attempt range
# discipline 0-99 -> penalty rate multiplier. A league-average staff
# lands on exactly 1.0, so the calibrated penalty rates in tuning.py stay
# the league mean rather than drifting as a side effect of this system.
PENALTY_RATE_AT_ZERO_DISCIPLINE = 1.30
PENALTY_RATE_AT_MAX_DISCIPLINE = 0.70
# player_dev_* 0-99 -> progression multiplier (GDD Sec 8.2.1 lists
# player development as a coach's headline dynamic rating; Sec 7.6's
# progression formula is where it lands).
DEV_MULTIPLIER_MIN = 0.85
DEV_MULTIPLIER_MAX = 1.15
# R13 Sec 5.2: motivation_chemistry -> injury-rate multiplier (Training
# focus). Same shape as the discipline->penalty-rate pair above -- a
# league-average Training investment lands on exactly 1.0.
INJURY_RISK_AT_ZERO_TRAINING = 1.20
INJURY_RISK_AT_MAX_TRAINING = 0.80

# R13 Sec 5.1: how much weight a coach's OWN chosen focus_area carries into
# whichever bucket it targets -- replaces the old two-tier COORDINATOR_WEIGHT/
# HEAD_COACH_WEIGHT role-based split with a focus-based one covering all
# three staff tiers. Values chosen so a bucket with exactly one HC + one
# coordinator focused there reproduces the old 0.4/0.6 split exactly.
HC_TIER_WEIGHT = 0.4
COORDINATOR_TIER_WEIGHT = 0.6
ASSISTANT_TIER_WEIGHT = 0.3
# Balanced Gameplan (R13 Sec 5.1): a coach here contributes to BOTH OF
# Gameplan and DF Gameplan at this fraction of their normal tier weight on
# EACH side -- real influence on both, smaller than fully focusing on one
# (Brian's own explicit design, 2026-09-13).
BALANCE_SPLIT_FACTOR = 0.5

# The rating value that counts as "league average" when no real league
# is available to measure against (unit tests with hand-built staffs,
# and any database with no coaches).
NEUTRAL_RATING = 50.0


@dataclass(frozen=True)
class LeagueBaseline:
    """What "average" actually means in THIS league, measured rather
    than assumed.

    This exists because of a real calibration bug caught during this
    system's first live verification. The quality ratings (discipline,
    player_dev_*) are generated centered on each coach's `reputation`,
    and reputation is a salary PERCENTILE mapped onto 40-99 -- so its
    league mean is ~70, not 50. Centering the penalty-rate and
    development multipliers on a hardcoded 50 therefore gave *every*
    team a below-1.0 penalty multiplier (~0.8x) and an above-1.0
    development multiplier (~1.10x), quietly shifting league-wide
    penalty and progression rates that tuning.py and
    tests/test_stat_realism.py have calibrated -- a systematic bias, not
    the per-team differentiation this system is for.

    Centering on the measured league mean instead makes the average
    team land on exactly 1.0 by construction, so a staff can only ever
    move its own team relative to the rest of the league, never move
    the league."""
    discipline: float = NEUTRAL_RATING
    dev_offense: float = NEUTRAL_RATING
    dev_defense: float = NEUTRAL_RATING
    tendency: float = NEUTRAL_RATING
    # R13: motivation_chemistry's league mean -- same pool shape as
    # dev_offense/dev_defense (mean across every employed coach), NOT
    # HC-only like discipline, since Training can be any coach's focus.
    motivation_chemistry: float = NEUTRAL_RATING


NEUTRAL_BASELINE = LeagueBaseline()


def _slider(value: float, center: float = NEUTRAL_RATING) -> float:
    """A 0-100 rating -> [-1, 1] relative to what's average in this
    league (see LeagueBaseline). Clamped so an extreme outlier can't
    push a bias past its documented scale."""
    return max(-1.0, min(1.0, (value - center) / 50.0))


@dataclass(frozen=True)
class StaffEffect:
    """One team's coaching staff, reduced to the handful of numbers the
    sim actually consumes -- computed once per game (Sec 7.7.3's
    "strategy profile locked at kickoff") rather than re-derived per
    play. Every field is already in final bias units, not raw slider
    values, so the per-play call sites stay arithmetic-free."""
    team_abbr: str
    pass_bias: float = 0.0
    rz_pass_bias: float = 0.0
    fourth_down_bias: float = 0.0
    two_point_bias: float = 0.0
    blitz_bias: float = 0.0
    rz_blitz_bias: float = 0.0
    man_coverage_prob: float | None = None
    run_tactic_extra_penalty: float = 0.0
    penalty_rate_multiplier: float = 1.0
    fg_range_bonus: float = 0.0
    dev_multiplier_offense: float = 1.0
    dev_multiplier_defense: float = 1.0
    # R13 Sec 5.2: Training focus (via motivation_chemistry) -> injury-rate
    # multiplier. 1.0 = league-average Training investment, same shape as
    # penalty_rate_multiplier above.
    injury_risk_multiplier: float = 1.0


NEUTRAL = StaffEffect(team_abbr="")


def _tier_weight(role: CoachRole) -> float:
    """R13 Sec 5.1: how much one coach's focus_area choice counts,
    by their organizational tier -- HC > coordinator (OC/DC/ST) >
    assistant. Replaces the old COORDINATOR_WEIGHT/HEAD_COACH_WEIGHT
    two-tier split."""
    if role is CoachRole.HC:
        return HC_TIER_WEIGHT
    if role is CoachRole.AC:
        return ASSISTANT_TIER_WEIGHT
    return COORDINATOR_TIER_WEIGHT


def _bucket_weight(coach: Coach, target_focus: str) -> float:
    """How much weight `coach` contributes to `target_focus`'s blend: their
    full tier weight if focused there directly, `BALANCE_SPLIT_FACTOR` of it
    if Balanced Gameplan and `target_focus` is one of the two gameplan
    buckets (R13 Sec 5.1), otherwise 0.0 -- a coach contributes NOTHING
    outside their own chosen focus, the whole point of this being a
    reallocation rather than free power."""
    if coach.focus_area == target_focus:
        return _tier_weight(CoachRole(coach.role))
    if coach.focus_area == FOCUS_BALANCED_GAMEPLAN and target_focus in (FOCUS_OF_GAMEPLAN, FOCUS_DF_GAMEPLAN):
        return _tier_weight(CoachRole(coach.role)) * BALANCE_SPLIT_FACTOR
    return 0.0


# Staff impact audit (2026-09-14): which side of the ball a coach's
# player-development work actually lands on. Before this, every coach
# focused on Development fed BOTH dev multipliers -- a defensive line
# coach's player_dev_offense rating was moving quarterbacks' growth. Keyword
# match on the real AC specialty strings scripts/import_coaches.py's
# _SPECIALTY_BY_TITLE produces; anything unmatched (e.g. a strength coach,
# an unknown imported title) stays neutral and feeds both, as before.
SIDE_OFFENSE = "offense"
SIDE_DEFENSE = "defense"
SIDE_NEUTRAL = "neutral"
_OFFENSE_SPECIALTY_KEYWORDS = ("quarterback", "passing", "running back", "wide receiver", "tight end", "offensive")
_DEFENSE_SPECIALTY_KEYWORDS = ("defensive", "linebacker", "secondary", "safet", "cornerback")


def coach_side(coach: Coach) -> str:
    role = CoachRole(coach.role)
    if role is CoachRole.OC:
        return SIDE_OFFENSE
    if role is CoachRole.DC:
        return SIDE_DEFENSE
    if role is not CoachRole.AC:
        return SIDE_NEUTRAL
    text = (coach.specialty or "").lower()
    if any(k in text for k in _DEFENSE_SPECIALTY_KEYWORDS):
        return SIDE_DEFENSE
    if any(k in text for k in _OFFENSE_SPECIALTY_KEYWORDS):
        return SIDE_OFFENSE
    return SIDE_NEUTRAL


def _weighted_blend(staff, target_focus: str, attr: str, fallback: float) -> float:
    """Tier-weighted average of `attr` across every coach in `staff`
    contributing to `target_focus` (via `_bucket_weight`). Returns
    `fallback` when nobody contributes at all -- the same graceful
    degradation the old `_blend()` had for a vacant coordinator seat,
    generalized to "nobody focused here" instead of "role not filled".
    Passing the bucket's own league-baseline value as `fallback` makes an
    empty bucket collapse to an exactly-neutral (1.0x) multiplier
    downstream, via `_slider(fallback, fallback) == 0`."""
    total_weight = 0.0
    total = 0.0
    for coach in staff:
        w = _bucket_weight(coach, target_focus)
        if w <= 0:
            continue
        total_weight += w
        total += w * getattr(coach, attr)
    return total / total_weight if total_weight > 0 else fallback


def _dev_multiplier(rating: float, center: float) -> float:
    """player_dev rating -> a bounded progression multiplier, 1.0 for a
    league-average staff."""
    span = (DEV_MULTIPLIER_MAX - DEV_MULTIPLIER_MIN) / 2.0
    return 1.0 + _slider(rating, center) * span


def _penalty_multiplier(discipline: float, center: float) -> float:
    hi, lo = PENALTY_RATE_AT_ZERO_DISCIPLINE, PENALTY_RATE_AT_MAX_DISCIPLINE
    span = (hi - lo) / 2.0
    return 1.0 - _slider(discipline, center) * span


def _injury_risk_multiplier(motivation_chemistry: float, center: float) -> float:
    """R13 Sec 5.2: Training focus (via motivation_chemistry) -> injury-rate
    multiplier, same shape as _penalty_multiplier above."""
    hi, lo = INJURY_RISK_AT_ZERO_TRAINING, INJURY_RISK_AT_MAX_TRAINING
    span = (hi - lo) / 2.0
    return 1.0 - _slider(motivation_chemistry, center) * span


def build_staff_effect(team_abbr: str, staff: list[Coach] | tuple[Coach, ...],
                       baseline: LeagueBaseline = NEUTRAL_BASELINE) -> StaffEffect:
    """Pure reduction of a staff list to sim biases -- no DB access, so
    it's directly unit-testable with hand-built Coach objects. Use
    staff_effect_for() for the cached, DB-backed version, which supplies
    the real measured `baseline` for this league.

    R13: every input below is gathered via `_weighted_blend()`, keyed by
    each coach's OWN `focus_area` rather than their role -- a coach whose
    focus points elsewhere contributes NOTHING to a given bucket. An empty
    staff (no coaches at all) is the one case handled outside that
    machinery, short-circuiting to a fully neutral effect exactly as
    before R13."""
    if not staff:
        return StaffEffect(team_abbr=team_abbr)

    head = next((c for c in staff if CoachRole(c.role) is CoachRole.HC), None)

    t = baseline.tendency
    of_run_pass = _weighted_blend(staff, FOCUS_OF_GAMEPLAN, "run_pass_tendency", t)
    of_rz_bias = _weighted_blend(staff, FOCUS_OF_GAMEPLAN, "red_zone_offense_bias", t)
    of_aggression = _weighted_blend(staff, FOCUS_OF_GAMEPLAN, "offensive_aggression", t)
    of_two_point = _weighted_blend(staff, FOCUS_OF_GAMEPLAN, "two_point_tendency", t)
    df_blitz = _weighted_blend(staff, FOCUS_DF_GAMEPLAN, "blitz_rate", t)
    df_rz_bias = _weighted_blend(staff, FOCUS_DF_GAMEPLAN, "red_zone_defense_bias", t)
    # coverage_mix is 0 = man heavy, 100 = zone heavy (Sec 7.7.2.2).
    # decide_coverage()'s own default is a 40% man / 60% zone split, so
    # a league-average staff must land on exactly 0.40 for this system
    # to be a lean rather than a recalibration.
    df_coverage = _weighted_blend(staff, FOCUS_DF_GAMEPLAN, "coverage_mix", t)
    df_fourth = _weighted_blend(staff, FOCUS_DF_GAMEPLAN, "fourth_down_defense", t)
    man_prob = max(0.10, min(0.75, 0.40 - _slider(df_coverage, t) * COVERAGE_SWING))

    # Side-aware (see coach_side()): an offensive position coach develops
    # the offense only, a defensive one the defense only.
    dev_off = _weighted_blend([c for c in staff if coach_side(c) != SIDE_DEFENSE],
                              FOCUS_DEVELOPMENT, "player_dev_offense", baseline.dev_offense)
    dev_def = _weighted_blend([c for c in staff if coach_side(c) != SIDE_OFFENSE],
                              FOCUS_DEVELOPMENT, "player_dev_defense", baseline.dev_defense)
    training_mc = _weighted_blend(staff, FOCUS_TRAINING, "motivation_chemistry", baseline.motivation_chemistry)
    st_focus = _weighted_blend(staff, FOCUS_SPECIAL_TEAMS, "special_teams_focus", t)

    return StaffEffect(
        team_abbr=team_abbr,
        pass_bias=_slider(of_run_pass, t) * PASS_MIX_SCALE,
        rz_pass_bias=_slider(of_rz_bias, t) * RZ_PASS_SCALE,
        fourth_down_bias=_slider(of_aggression, t) * FOURTH_DOWN_SCALE,
        two_point_bias=_slider(of_two_point, t) * TWO_POINT_SCALE,
        blitz_bias=_slider(df_blitz, t) * BLITZ_SCALE,
        rz_blitz_bias=_slider(df_rz_bias, t) * RZ_BLITZ_SCALE,
        man_coverage_prob=man_prob,
        run_tactic_extra_penalty=max(0.0, _slider(df_fourth, t)) * FOURTH_DOWN_DEFENSE_SCALE * 20,
        # discipline stays a fixed HC-only read, unaffected by focus_area
        # (R13 Sec 5.1: not everything becomes reallocatable -- a program's
        # discipline culture is a leadership trait, not a delegable focus).
        penalty_rate_multiplier=_penalty_multiplier(
            head.discipline if head else baseline.discipline, baseline.discipline),
        fg_range_bonus=_slider(st_focus, t) * FG_RANGE_SCALE,
        dev_multiplier_offense=_dev_multiplier(dev_off, baseline.dev_offense),
        dev_multiplier_defense=_dev_multiplier(dev_def, baseline.dev_defense),
        injury_risk_multiplier=_injury_risk_multiplier(training_mc, baseline.motivation_chemistry),
    )


def league_baseline() -> LeagueBaseline:
    """The measured league averages every staff is judged against.
    Computed once from every employed coach and cached; cleared by
    clear_cache() whenever a Coach row changes.

    Each pool matches how that rating is actually consumed, and is
    DELIBERATELY independent of any coach's current focus_area -- what
    counts as "average" for a rating is a property of the coaching
    population, not of who currently happens to be focused where (that
    would create a feedback loop as focus assignments change). `discipline`
    is only ever read off the HEAD coach, so its baseline is the mean
    across the 32 head coaches -- not across all 433 staffers, which would
    measure Andy Reid against a $450K assistant. The development ratings
    and motivation_chemistry (R13's Training input) are blended across a
    whole staff, so theirs is the mean across every coach. The tendency
    sliders are drawn symmetrically around 50 by construction, so their
    baseline is the mean of every slider on every coach, which lands on
    ~50 and confirms that rather than assuming it."""
    global _BASELINE
    if _BASELINE is not None:
        return _BASELINE
    from app.services import coach_store
    coaches = [c for c in coach_store.all_coaches() if c.team_abbr is not None and not c.retired]
    if not coaches:
        _BASELINE = NEUTRAL_BASELINE
        return _BASELINE

    heads = [c for c in coaches if CoachRole(c.role) is CoachRole.HC]
    # `pace` is deliberately NOT in this pool: no sim system reads a coach's
    # pace (staff impact audit, 2026-09-14), so it has no business shaping
    # what "average" means for the sliders that ARE consumed.
    tendency_values = [
        v for c in coaches for v in (
            c.run_pass_tendency, c.offensive_aggression, c.red_zone_offense_bias,
            c.two_point_tendency, c.blitz_rate, c.coverage_mix, c.fourth_down_defense,
            c.red_zone_defense_bias, c.special_teams_focus,
        )
    ]
    _BASELINE = LeagueBaseline(
        discipline=sum(c.discipline for c in heads) / len(heads) if heads else NEUTRAL_RATING,
        dev_offense=sum(c.player_dev_offense for c in coaches) / len(coaches),
        dev_defense=sum(c.player_dev_defense for c in coaches) / len(coaches),
        motivation_chemistry=sum(c.motivation_chemistry for c in coaches) / len(coaches),
        tendency=sum(tendency_values) / len(tendency_values),
    )
    return _BASELINE


def staff_effect_for(team_abbr: str) -> StaffEffect:
    """Cached, DB-backed StaffEffect for one team. Returns a fully
    neutral effect when the database has no coaches (see
    coach_store.has_coaches()), so a pre-coach database simulates
    exactly as it did before this system existed."""
    from app.services import coach_store
    return _cached_staff_effect(team_abbr, coach_store.staff_for(team_abbr))


def _cached_staff_effect(team_abbr: str, staff: tuple[Coach, ...]) -> StaffEffect:
    # Keyed on the staff tuple itself (coach_store already caches that),
    # so a staff change invalidates this automatically without a second
    # cache to remember to clear.
    key = (team_abbr, tuple(c.coach_id for c in staff))
    cached = _EFFECT_CACHE.get(key)
    if cached is None:
        cached = build_staff_effect(team_abbr, staff, league_baseline())
        _EFFECT_CACHE[key] = cached
    return cached


_EFFECT_CACHE: dict[tuple, StaffEffect] = {}
_BASELINE: LeagueBaseline | None = None


def clear_cache() -> None:
    global _BASELINE
    _EFFECT_CACHE.clear()
    _BASELINE = None


# --- Per-call-site accessors, mirroring gameplan.py's function shape ---

def offense_pass_bias(effect: StaffEffect | None, in_red_zone: bool) -> float:
    if effect is None:
        return 0.0
    return effect.pass_bias + (effect.rz_pass_bias if in_red_zone else 0.0)


def offense_fourth_down_bias(effect: StaffEffect | None) -> float:
    return 0.0 if effect is None else effect.fourth_down_bias


def offense_two_point_bias(effect: StaffEffect | None) -> float:
    return 0.0 if effect is None else effect.two_point_bias


def defense_blitz_bias(effect: StaffEffect | None, in_red_zone: bool) -> float:
    if effect is None:
        return 0.0
    return effect.blitz_bias + (effect.rz_blitz_bias if in_red_zone else 0.0)


def defense_coverage_man_prob(effect: StaffEffect | None) -> float | None:
    """None means "no opinion" -- the caller keeps its own default,
    exactly as gameplan.defense_coverage_man_prob() already specifies."""
    return None if effect is None else effect.man_coverage_prob


def defense_run_tactic_extra_penalty(effect: StaffEffect | None, down: int, distance: int) -> float:
    """A defensive staff's short-yardage aggressiveness (Sec 7.7.2.2's
    fourth_down_defense) commits harder to the predicted run point of
    attack when the offense is in an obvious short-yardage down --
    which is the only situation that slider describes."""
    if effect is None or distance > 2 or down < 3:
        return 0.0
    return effect.run_tactic_extra_penalty


def penalty_rate_multiplier(effect: StaffEffect | None) -> float:
    """Head coach discipline -> team penalty rate (GDD Sec 7.7.4)."""
    return 1.0 if effect is None else effect.penalty_rate_multiplier


def fg_range_bonus(effect: StaffEffect | None) -> float:
    """Special-teams focus -> how far out this staff will try a field
    goal (GDD Sec 7.7.2.2: special_teams_focus "affects ... average FG
    try distances")."""
    return 0.0 if effect is None else effect.fg_range_bonus


def injury_risk_multiplier(effect: StaffEffect | None) -> float:
    """R13 Sec 5.2: Training-focused staff (via motivation_chemistry) ->
    team injury-rate multiplier."""
    return 1.0 if effect is None else effect.injury_risk_multiplier
