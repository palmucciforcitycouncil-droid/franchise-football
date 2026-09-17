"""
Coaching effects on the simulation (GDD Part 1 Sec 7.7.2.2/7.7.2.3,
Sec 7.7.3's "Weekly strategy profile (Off + Def + ST) locked at
kickoff"; ROADMAP.md R3, R16).

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
exists for all 32, because all 32 have a real staff.

**R16 (docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md) split this
module's job in two, on purpose, after R13 tangled them together:**

1. **Play-calling** (`StaffEffect`'s bias fields below) is driven by a
   coach's own tendency sliders (Sec 7.7.2.2), read by ROLE -- an OC's
   own tendencies always drive their team's offensive calls, a DC's
   always drive defense, exactly like this system worked before R13.
   Focus Area has ZERO influence here now. This is a deliberate REVERT
   of R13's own "gather every slider by focus_area, not role"
   mechanism (that whole `_bucket_weight`/`_tier_weight`/`_weighted_
   blend` apparatus is gone) -- confirmed in R16 planning: "only the
   Gameplan setting the user picks changes play-calling," and without
   SOME staff-driven differentiation every AI team's play-calling would
   otherwise be identical.
2. **Focus Area** now does something completely different and never
   touches play-calling at all: a this-game player-attribute boost to
   a targeted position group (`apply_focus_boosts()` below) plus a
   running seasonal development total (`app/services/coach_focus_
   accumulator.py`). See that module and `app/models/coach.py`'s
   FOCUS_* constants for the full taxonomy.

Calibration: every play-calling bias below is bounded to roughly HALF
the magnitude of the equivalent Weekly Gameplan lever -- a gameplan is
an explicit weekly choice the user makes and expects to feel; a staff's
tendencies apply to every team in every game all season, so an equally-
strong dial would drown out the player-attribute-driven engine Sec 6.6
rests on. The slider->bias scales here are this module's own documented
choices -- GDD Sec 7.7.2.2 defines the sliders and their direction but
gives no formula converting a 0-100 slider into a probability shift.
"""
from __future__ import annotations
from dataclasses import dataclass

from app.models.coach import Coach, CoachRole, FOCUS_RATING_WEIGHTS, FOCUS_POSITION_GROUPS, FOCUS_BREADTH_MULTIPLIER

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
# discipline 0-99 -> penalty rate multiplier. A league-average staff
# lands on exactly 1.0, so the calibrated penalty rates in tuning.py stay
# the league mean rather than drifting as a side effect of this system.
PENALTY_RATE_AT_ZERO_DISCIPLINE = 1.30
PENALTY_RATE_AT_MAX_DISCIPLINE = 0.70
# R16 Sec 8: motivation_chemistry (Strength & Conditioning focus) ->
# injury-rate multiplier AND stamina-recovery multiplier -- same shape
# as the discipline->penalty-rate pair above, a league-average staff
# lands on exactly 1.0/1.0.
INJURY_RISK_AT_ZERO_TRAINING = 1.20
INJURY_RISK_AT_MAX_TRAINING = 0.80
STAMINA_RECOVERY_AT_ZERO_TRAINING = 0.85
STAMINA_RECOVERY_AT_MAX_TRAINING = 1.15

# R16 Sec 6: how strongly the focused coach's own rating (relative to
# league average) scales their this-game position-group boost. [tune] --
# real structure, not yet playtested magnitude.
BOOST_SCALE = 6.0  # max +/- rating points added to a targeted player's relevant attributes

# The rating value that counts as "league average" when no real league
# is available to measure against (unit tests with hand-built staffs,
# and any database with no coaches).
NEUTRAL_RATING = 50.0


@dataclass(frozen=True)
class LeagueBaseline:
    """What "average" actually means in THIS league, measured rather
    than assumed (see module docstring's calibration note -- centering
    on a hardcoded 50 previously gave every team a systematic bias
    because `reputation`-anchored ratings' real league mean is ~70, not
    50)."""
    discipline: float = NEUTRAL_RATING
    tendency: float = NEUTRAL_RATING
    motivation_chemistry: float = NEUTRAL_RATING
    # R16: per-position-group coaching ratings' league means, for the
    # this-game boost's relative-to-average scaling (Sec 6).
    qb_coaching: float = NEUTRAL_RATING
    rb_coaching: float = NEUTRAL_RATING
    wr_coaching: float = NEUTRAL_RATING
    ol_coaching: float = NEUTRAL_RATING
    dl_coaching: float = NEUTRAL_RATING
    lb_coaching: float = NEUTRAL_RATING
    secondary_coaching: float = NEUTRAL_RATING
    st_coaching: float = NEUTRAL_RATING


NEUTRAL_BASELINE = LeagueBaseline()


def _slider(value: float, center: float = NEUTRAL_RATING) -> float:
    """A 0-100 rating -> [-1, 1] relative to what's average in this
    league (see LeagueBaseline). Clamped so an extreme outlier can't
    push a bias past its documented scale."""
    return max(-1.0, min(1.0, (value - center) / 50.0))


@dataclass(frozen=True)
class StaffEffect:
    """One team's coaching staff, reduced to the handful of PLAY-CALLING
    numbers the sim actually consumes -- computed once per game (Sec
    7.7.3's "strategy profile locked at kickoff") rather than re-derived
    per play. R16: this is play-calling ONLY now (see module docstring)
    -- the this-game player boost and seasonal development live
    elsewhere (`apply_focus_boosts()` below, `coach_focus_accumulator.py`)."""
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
    injury_risk_multiplier: float = 1.0
    stamina_recovery_multiplier: float = 1.0


NEUTRAL = StaffEffect(team_abbr="")


def _role_attr(staff, role: CoachRole, attr: str, fallback: float) -> float:
    """Sec 8's role-based play-calling read, replacing R13's focus-gated
    blend: the role owner's own value, falling back to the HC if that
    seat is vacant (a real, sensible fallback -- the program's overall
    lead still has an opinion on a coordinator-less team), and to the
    league baseline if the whole staff is empty."""
    coach = next((c for c in staff if CoachRole(c.role) is role), None)
    if coach is not None:
        return getattr(coach, attr)
    head = next((c for c in staff if CoachRole(c.role) is CoachRole.HC), None)
    if head is not None:
        return getattr(head, attr)
    return fallback


def _penalty_multiplier(discipline: float, center: float) -> float:
    hi, lo = PENALTY_RATE_AT_ZERO_DISCIPLINE, PENALTY_RATE_AT_MAX_DISCIPLINE
    span = (hi - lo) / 2.0
    return 1.0 - _slider(discipline, center) * span


def _injury_risk_multiplier(motivation_chemistry: float, center: float) -> float:
    hi, lo = INJURY_RISK_AT_ZERO_TRAINING, INJURY_RISK_AT_MAX_TRAINING
    span = (hi - lo) / 2.0
    return 1.0 - _slider(motivation_chemistry, center) * span


def _stamina_recovery_multiplier(motivation_chemistry: float, center: float) -> float:
    lo, hi = STAMINA_RECOVERY_AT_ZERO_TRAINING, STAMINA_RECOVERY_AT_MAX_TRAINING
    span = (hi - lo) / 2.0
    return 1.0 + _slider(motivation_chemistry, center) * span


def _training_focused_motivation(staff, baseline_mc: float) -> float:
    """Strength & Conditioning is universal (every role can pick it) and
    can be picked by more than one coach on the same staff -- a simple,
    tier-weighted average across everyone currently focused there,
    falling back to the league baseline (-> exactly neutral 1.0x) when
    nobody is."""
    from app.models.coach import FOCUS_TRAINING
    focused = [c for c in staff if c.focus_area == FOCUS_TRAINING]
    if not focused:
        return baseline_mc
    return sum(c.motivation_chemistry for c in focused) / len(focused)


def build_staff_effect(team_abbr: str, staff: list[Coach] | tuple[Coach, ...],
                       baseline: LeagueBaseline = NEUTRAL_BASELINE) -> StaffEffect:
    """Pure reduction of a staff list to PLAY-CALLING biases -- no DB
    access, directly unit-testable with hand-built Coach objects. Use
    staff_effect_for() for the cached, DB-backed version.

    R16: every tendency input is read by ROLE (`_role_attr()`), not by
    focus_area -- see module docstring for why."""
    if not staff:
        return StaffEffect(team_abbr=team_abbr)

    head = next((c for c in staff if CoachRole(c.role) is CoachRole.HC), None)
    t = baseline.tendency

    of_run_pass = _role_attr(staff, CoachRole.OC, "run_pass_tendency", t)
    of_rz_bias = _role_attr(staff, CoachRole.OC, "red_zone_offense_bias", t)
    of_aggression = _role_attr(staff, CoachRole.OC, "offensive_aggression", t)
    of_two_point = _role_attr(staff, CoachRole.OC, "two_point_tendency", t)
    df_blitz = _role_attr(staff, CoachRole.DC, "blitz_rate", t)
    df_rz_bias = _role_attr(staff, CoachRole.DC, "red_zone_defense_bias", t)
    # coverage_mix is 0 = man heavy, 100 = zone heavy (Sec 7.7.2.2).
    # decide_coverage()'s own default is a 40% man / 60% zone split, so
    # a league-average staff must land on exactly 0.40 for this system
    # to be a lean rather than a recalibration.
    df_coverage = _role_attr(staff, CoachRole.DC, "coverage_mix", t)
    df_fourth = _role_attr(staff, CoachRole.DC, "fourth_down_defense", t)
    man_prob = max(0.10, min(0.75, 0.40 - _slider(df_coverage, t) * COVERAGE_SWING))

    training_mc = _training_focused_motivation(staff, baseline.motivation_chemistry)

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
        # discipline stays a fixed HC-only read, always did (R13's own
        # comment already noted this is a leadership trait, not a
        # delegable focus -- still true post-R16).
        penalty_rate_multiplier=_penalty_multiplier(
            head.discipline if head else baseline.discipline, baseline.discipline),
        injury_risk_multiplier=_injury_risk_multiplier(training_mc, baseline.motivation_chemistry),
        stamina_recovery_multiplier=_stamina_recovery_multiplier(training_mc, baseline.motivation_chemistry),
    )


def league_baseline() -> LeagueBaseline:
    """The measured league averages every staff is judged against.
    Computed once from every employed coach and cached; cleared by
    clear_cache() whenever a Coach row changes."""
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

    def _avg(attr: str) -> float:
        return sum(getattr(c, attr) for c in coaches) / len(coaches)

    _BASELINE = LeagueBaseline(
        discipline=sum(c.discipline for c in heads) / len(heads) if heads else NEUTRAL_RATING,
        motivation_chemistry=_avg("motivation_chemistry"),
        tendency=sum(tendency_values) / len(tendency_values),
        qb_coaching=_avg("qb_coaching"), rb_coaching=_avg("rb_coaching"),
        wr_coaching=_avg("wr_coaching"), ol_coaching=_avg("ol_coaching"),
        dl_coaching=_avg("dl_coaching"), lb_coaching=_avg("lb_coaching"),
        secondary_coaching=_avg("secondary_coaching"), st_coaching=_avg("st_coaching"),
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


def injury_risk_multiplier(effect: StaffEffect | None) -> float:
    """Strength & Conditioning focus (via motivation_chemistry) -> team
    injury-rate multiplier."""
    return 1.0 if effect is None else effect.injury_risk_multiplier


def stamina_recovery_multiplier(effect: StaffEffect | None) -> float:
    """R16 Sec 8: Strength & Conditioning focus also speeds stamina
    recovery, reusing the existing roster-depth-rotation durability/
    stamina mechanic (ROADMAP item 37) rather than a second one."""
    return 1.0 if effect is None else effect.stamina_recovery_multiplier


# ---------------------------------------------------------------------------
# R16 Sec 6: this-game position-group boost -- Focus Area's real new job.
# Pure function of a staff + starters; never touches the DB-backed Player
# rows themselves (a copy-with-adjusted-attributes, same "never persist a
# per-game effect" principle Weekly Gameplan/weather already follow).
# ---------------------------------------------------------------------------

# Which of a Player's own attributes each position group's boost actually
# nudges -- the attributes app/engine/player_ai.py's real matchup
# functions already read for that group (ol_run_block/ol_pass_block,
# dl_run_stop/dl_pass_rush, coverage_rating, etc.), so a boost here is
# guaranteed to reach the sim through an existing, real read path.
_GROUP_BOOST_ATTRS: dict[str, tuple[str, ...]] = {
    "QB": ("throw_power", "throw_accuracy_short", "throw_accuracy_mid", "throw_accuracy_deep", "awareness"),
    "RB": ("carrying", "break_tackle", "ball_carrier_vision", "juke_move"),
    "WR": ("catching", "short_route_running", "medium_route_running", "deep_route_running"),
    "TE": ("catching", "short_route_running", "medium_route_running", "run_block"),
    "OL": ("run_block", "pass_block"),
    "DL": ("tackle", "block_shedding", "power_moves", "finesse_moves", "pursuit"),
    "LB": ("tackle", "block_shedding", "pursuit", "man_coverage", "zone_coverage"),
    "CB": ("man_coverage", "zone_coverage", "press"),
    "S": ("man_coverage", "zone_coverage", "hit_power"),
    "K": ("kick_power", "kick_accuracy"),
    "P": ("kick_power", "kick_accuracy"),
}


def _coach_group_boost(coach: Coach, focus: str, baseline: LeagueBaseline) -> float:
    """This one coach's rating-scaled boost points for `focus`, 0 if
    they're not focused there. Magnitude scales off their OWN relevant
    rating relative to league average (Sec 6) -- a great coach's "OL"
    focus does more than a replacement-level one's -- times the focus's
    breadth multiplier (a narrow focus hits harder than a broad one)."""
    if coach.focus_area != focus:
        return 0.0
    weights = FOCUS_RATING_WEIGHTS.get(focus)
    if not weights:
        return 0.0
    total_w = sum(w for _, w in weights)
    rating = sum(getattr(coach, r) * w for r, w in weights) / total_w
    center = sum(getattr(baseline, r) * w for r, w in weights) / total_w
    breadth = FOCUS_BREADTH_MULTIPLIER.get(focus, 1.0)
    return _slider(rating, center) * BOOST_SCALE * breadth


def _team_group_boosts(staff, baseline: LeagueBaseline) -> dict[str, float]:
    """Every position group's TOTAL boost this week for one team --
    R16 Sec 6: multiple coaches focused on the same/overlapping group
    compound (summed, not averaged/maxed)."""
    totals: dict[str, float] = {}
    for coach in staff:
        boost = _coach_group_boost(coach, coach.focus_area, baseline)
        if boost == 0.0:
            continue
        for group in FOCUS_POSITION_GROUPS.get(coach.focus_area, []):
            totals[group] = totals.get(group, 0.0) + boost
    return totals


def _boosted_player(player, attrs: tuple[str, ...], boost: float):
    """A DETACHED copy of `player` with `attrs` nudged by `boost` (clamped
    0-99) -- never the real session-attached row, so this can never
    accidentally persist. SQLModel rows support `model_copy(update=...)`
    (pydantic v2 style) for exactly this."""
    if boost == 0.0:
        return player
    updates = {attr: max(0, min(99, int(round(getattr(player, attr) + boost)))) for attr in attrs}
    return player.model_copy(update=updates)


# Named single-Player fields on OffensiveStarters/DefensiveStarters that
# a boost can land on -- explicit, not reflected, since both dataclasses
# also carry an Optional field (wr3) and non-Player fields (hb_depth/
# wr_depth/te_depth lists, backups dict) that a generic walk would
# mishandle. The depth-pool list fields are boosted too, separately --
# see `apply_focus_boosts()`'s own note on why that's safe, not a
# double-boost.
_OFFENSE_SINGLE_FIELDS = ("qb", "hb", "wr1", "wr2", "wr3", "te", "lt", "lg", "c", "rg", "rt", "k", "p")
_OFFENSE_LIST_FIELDS = ("hb_depth", "wr_depth", "te_depth")
_DEFENSE_SINGLE_FIELDS = ("dt1", "dt2", "le", "re", "lolb", "mlb", "rolb", "cb1", "cb2", "fs", "ss")


def _boost_one(player, position_to_group: dict, boosts: dict[str, float]):
    if player is None:
        return None
    group = position_to_group.get(player.position)
    boost = boosts.get(group, 0.0) if group else 0.0
    if boost == 0.0:
        return player
    return _boosted_player(player, _GROUP_BOOST_ATTRS.get(group, ()), boost)


def apply_focus_boosts(team_abbr: str, offense, defense):
    """R16 Sec 6: returns (boosted_offense, boosted_defense) -- the same
    `OffensiveStarters`/`DefensiveStarters` shape app/services/depth_
    chart.py already produces, with every targeted player's relevant
    attributes nudged for this one game only. A team with no coaches (or
    nobody focused anywhere real) gets back the exact objects it was
    given, untouched.

    Boosting a named starter field (e.g. `hb`) and that same real person
    again inside a depth-pool list (e.g. `hb_depth[0]`) is NOT a double
    boost: each is computed fresh from the original, un-boosted `Player`
    row, so both copies land on the identical once-boosted value rather
    than compounding."""
    from app.services import coach_store
    staff = coach_store.staff_for(team_abbr)
    if not staff:
        return offense, defense
    boosts = _team_group_boosts(staff, league_baseline())
    if not boosts:
        return offense, defense

    from app.engine.draft import GROUP_POSITIONS
    position_to_group = {pos: group for group, positions in GROUP_POSITIONS.items() for pos in positions}

    if offense is not None:
        updates = {f: _boost_one(getattr(offense, f), position_to_group, boosts) for f in _OFFENSE_SINGLE_FIELDS}
        updates.update({
            f: [_boost_one(p, position_to_group, boosts) for p in getattr(offense, f)]
            for f in _OFFENSE_LIST_FIELDS
        })
        offense = offense.__class__(**{**offense.__dict__, **updates})

    if defense is not None:
        updates = {f: _boost_one(getattr(defense, f), position_to_group, boosts) for f in _DEFENSE_SINGLE_FIELDS}
        defense = defense.__class__(**{**defense.__dict__, **updates})

    return offense, defense
