"""
Kickoffs, onside kicks, blocked kicks, and 2-point conversions (GDD Sec
6.8) -- the special-teams activities that weren't modeled at all before
this module (see ROADMAP.md R2's original "Return-game simulation" row
and R10/this module's own HANDOFF entry for what was actually built vs.
just specced). Field goals, PATs, and net-only punts already existed in
drive_sim.py before this and stay there unchanged; this module only adds
what those didn't cover.

Kept as its own module (not folded into drive_sim.py, already 740+ lines)
since these are a genuinely separate concern -- possession-transition
plays that happen BETWEEN drives, not down-by-down snaps within one.

Determinism (GDD Sec 1.3): every roll here goes through the same seeded
`RNG` helper drive_sim.py already uses -- never a bare `random` call.

Known, disclosed simplification: no dedicated kick/punt returner exists
anywhere in this engine's depth-chart model (app/services/depth_chart.py
-- confirmed via that module's own KR/PR-slot omission, M15's note). A
returner is picked here from the receiving team's real WR/HB depth pools
by whoever has the best `kick_return` rating, not a fixed depth-chart
slot -- the same "pick a fitting player dynamically" approach drive_sim.py
already uses for run-play tacklers/sack credit (_run_tackler/
_sack_defender) rather than inventing a new roster field.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .rng import RNG
from .tuning import PARAMS
from app.models.player import Player
from app.services.depth_chart import OffensiveStarters

# Kickoffs: touchback rate calibrated as a reasonable middle ground (not
# tied to any one real-world rule era, since this project's Madden-derived
# data doesn't specify one) -- high enough that touchbacks are the common
# case (matching post-2018-ish rule eras) while still leaving room for a
# real, disclosed return-yardage/return-TD distribution the GDD asks for.
KICKOFF_TOUCHBACK_PROB = 0.55
KICKOFF_TOUCHBACK_SPOT = 25
KICKOFF_RETURN_MU = 24.0
KICKOFF_RETURN_SIGMA = 9.0
KICKOFF_RETURN_KR_SCALE = 0.15  # per point of (kick_return - 70)

# Return TD: same single-distance-based-roll shape as drive_sim.py's
# _defensive_td_probability (GDD Sec 6.7.2) -- deliberately not a full
# open-field return simulation (blocking, missed tackles play by play),
# just a real, small, distance-sensitive chance a long return goes all
# the way, shared by kickoff and punt returns since neither has a fuller
# model to draw from.
RETURN_TD_BASE_PROB = 0.05
RETURN_TD_DISTANCE_SCALE = 0.0009  # per yard of remaining distance to the end zone
RETURN_TD_MIN_PROB = 0.002
RETURN_TD_MAX_PROB = 0.06

ONSIDE_RECOVERY_PROB = 0.07  # GDD Sec 6.8's ~7%
ONSIDE_KICK_SPOT = 45        # short kick recovered/lost around the kicking team's 45

# R2b: real punt-return yardage + return-tackle attribution (GDD Sec
# 6.8's return game, previously only built for kickoffs -- see
# ROADMAP.md R2's own "still not done" note). Resolved from game_sim.py,
# not drive_sim.py's simulate_drive -- a return's stat credit belongs to
# a DIFFERENT team's box score than the drive that just ended (the
# RECEIVING team gets the return yardage, the PUNTING team's coverage
# gets the tackle), the same "resolve between drives" architecture
# _resolve_kickoff already established for kickoff returns. Return
# yardage here is a real, disclosed DECOMPOSITION of the net-yards
# field-position outcome drive_sim.py's _punt_result already computed
# (gross = net + return), never a second, independent field-position
# roll -- this is what keeps the Score Fidelity System's existing net-
# punt calibration completely unaffected by this feature.
#
# PUNT_RETURN_PROB: this module's own disclosed estimate (no exact
# league-wide rate is published) for how often a real, non-touchback,
# non-blocked punt is actually returned rather than fair-caught/downed/
# out of bounds -- roughly half, matching the modern NFL's much higher
# fair-catch rate than the pre-2010s game. Return yardage is heavily
# weighted toward short/modest gains (most real returns are 0-15 yards)
# via a Gaussian floor plus a small, real "explosive return" bonus --
# the same shape drive_sim.py's own _resolve_run uses for an explosive
# run. Punt-return touchdowns are real but rarer than kickoff-return
# ones (a shorter runback, more traffic near the line) -- a smaller base
# probability than RETURN_TD_BASE_PROB above, same distance-sensitive
# shape.
PUNT_RETURN_PROB = 0.55
PUNT_RETURN_MU = 7.0
PUNT_RETURN_SIGMA = 5.5
PUNT_RETURN_KR_SCALE = 0.12
PUNT_RETURN_EXPLOSIVE_BASE_PROB = 0.04
PUNT_RETURN_TD_BASE_PROB = 0.012
PUNT_RETURN_TD_DISTANCE_SCALE = 0.0006
PUNT_RETURN_TD_MIN_PROB = 0.0005
PUNT_RETURN_TD_MAX_PROB = 0.02

# 2-point conversions: real NFL success rate is ~47-50%; the offense's
# own pass/run resolution machinery isn't reused here (no goal-line-
# package concept exists in this engine, a disclosed simplification) --
# a single flat roll stands in for "the 2-point attempt," same spirit as
# _attempt_field_goal's single roll for a kick.
TWO_POINT_SUCCESS_PROB = 0.48


def _best_returner(receiving_offense: OffensiveStarters) -> Player:
    pool = receiving_offense.wr_depth + receiving_offense.hb_depth
    if not pool:
        return receiving_offense.wr1 or receiving_offense.hb
    return max(pool, key=lambda p: p.kick_return)


def _coverage_tackler(kicking_or_punting_offense: OffensiveStarters, rng: RNG) -> str:
    """R2b: real tackle credit for a kickoff/punt return -- no dedicated
    special-teams unit/roster exists anywhere in this engine (the same
    gap _best_returner's own docstring already discloses for the
    RECEIVING side), so the tackler is picked from the KICKING/PUNTING
    team's own WR depth: a real "gunner" (the player assigned to sprint
    downfield in coverage) is most often a receiver in the real NFL,
    the same disclosed-analog approach as the returner side."""
    pool = kicking_or_punting_offense.wr_depth
    if not pool:
        pool = [p for p in (kicking_or_punting_offense.wr1, kicking_or_punting_offense.te) if p is not None]
    if not pool:
        return ""
    return rng.choice(pool).full_name


def _return_td_probability(return_distance: int) -> float:
    return max(RETURN_TD_MIN_PROB, min(RETURN_TD_MAX_PROB,
        RETURN_TD_BASE_PROB - return_distance * RETURN_TD_DISTANCE_SCALE))


def _punt_return_td_probability(return_distance: int) -> float:
    return max(PUNT_RETURN_TD_MIN_PROB, min(PUNT_RETURN_TD_MAX_PROB,
        PUNT_RETURN_TD_BASE_PROB - return_distance * PUNT_RETURN_TD_DISTANCE_SCALE))


@dataclass(frozen=True)
class KickoffResult:
    new_pos: int          # receiving team's new field position (0..100, their own perspective)
    kind: str              # "touchback" | "return" | "return_td" | "blocked"... (blocks not modeled for kickoffs)
    return_yards: int
    returner_name: str
    desc: str
    tackler_name: str = ""  # R2b: empty on a touchback or a return_td (nobody "tackled" a score)


@dataclass(frozen=True)
class PuntReturnResult:
    kind: str              # "no_return" | "return" | "return_td"
    return_yards: int
    returner_name: str
    tackler_name: str
    desc: str


def decide_kickoff_strategy(kicking_team_trailing: bool, drives_left: int, rng: RNG) -> str:
    """Mirrors _decide_fourth_down's shape (base rate + situational
    adjustments) -- returns "onside" or "normal". Onside is only ever
    worth trying when the kicking team is behind late; a small baseline
    chance even then keeps it from being a deterministic if/else."""
    if not kicking_team_trailing or drives_left > 3:
        return "normal"
    go_chance = 0.35 if drives_left <= 1 else 0.15
    return "onside" if rng.prob(go_chance) else "normal"


def onside_kick_result(rng: RNG) -> tuple[bool, int]:
    """Returns (kicking_team_recovered, new_pos_for_whoever_takes_over).
    new_pos is always from the perspective of whichever team ends up on
    offense next (the kicking team itself if they recover, matching how
    simulate_drive's field_pos is always "the team about to snap the
    ball"'s own distance-to-go)."""
    recovered = rng.prob(ONSIDE_RECOVERY_PROB)
    return recovered, ONSIDE_KICK_SPOT


def kickoff_result(rng: RNG, receiving_offense: OffensiveStarters, kicking_offense: OffensiveStarters) -> KickoffResult:
    if rng.prob(KICKOFF_TOUCHBACK_PROB):
        return KickoffResult(KICKOFF_TOUCHBACK_SPOT, "touchback", 0, "", "Touchback")

    returner = _best_returner(receiving_offense)
    mean = KICKOFF_RETURN_MU + (returner.kick_return - 70) * KICKOFF_RETURN_KR_SCALE
    return_yards = max(0, int(round(rng.gauss(mean, KICKOFF_RETURN_SIGMA))))
    new_pos = max(1, min(60, return_yards))  # kickoff return starts at the 0 (own goal line), not the 25

    return_distance = 100 - new_pos  # how far the returner would still have to go for a TD
    if rng.prob(_return_td_probability(return_distance)):
        return KickoffResult(100, "return_td", return_yards, returner.full_name,
                              f"Kickoff returned {return_yards} yards for a TOUCHDOWN by {returner.full_name}")

    tackler = _coverage_tackler(kicking_offense, rng)
    return KickoffResult(new_pos, "return", return_yards, returner.full_name,
                          f"Kickoff returned {return_yards} yards by {returner.full_name}", tackler_name=tackler)


def punt_return_result(
    rng: RNG, receiving_offense: OffensiveStarters, punting_offense: OffensiveStarters, return_distance: int,
) -> PuntReturnResult:
    """R2b: called from game_sim.py AFTER a punt's own net-yards field-
    position math is already final (drive_sim.py's _punt_result) --
    return_distance is how far the returner would have to go from that
    ALREADY-DECIDED spot to reach the end zone, purely to scale the
    return-TD roll; a "return_td" here overrides that spot with a real
    score instead (the caller's job, same as kickoffs' own return_td
    case). See this module's own top-of-section docstring for why this
    lives here, not in simulate_drive."""
    if not rng.prob(PUNT_RETURN_PROB):
        return PuntReturnResult("no_return", 0, "", "", "")

    returner = _best_returner(receiving_offense)
    mean = PUNT_RETURN_MU + (returner.kick_return - 70) * PUNT_RETURN_KR_SCALE
    return_yards = max(0, int(round(rng.gauss(mean, PUNT_RETURN_SIGMA))))
    if rng.prob(PUNT_RETURN_EXPLOSIVE_BASE_PROB + max(0, returner.kick_return - 80) * 0.002):
        return_yards += int(abs(rng.gauss(15, 8)))  # explosive return, same shape as _resolve_run's own bonus

    if rng.prob(_punt_return_td_probability(return_distance)):
        return PuntReturnResult("return_td", return_yards, returner.full_name, "",
                                 f"Punt returned {return_yards} yards for a TOUCHDOWN by {returner.full_name}")

    tackler = _coverage_tackler(punting_offense, rng)
    return PuntReturnResult("return", return_yards, returner.full_name, tackler,
                             f"Punt returned {return_yards} yards by {returner.full_name}")


def decide_pat_or_two(trailing: bool, is_two_minute: bool, aggression: float, rng: RNG,
                      two_point_bias: float = 0.0) -> str:
    """Returns "pat" or "two_point". Real 2-point decisions cluster around
    specific deficits late in games (down 2, 5, 8, 10...) where 2 points
    changes the number of scores needed -- modeling a full go-for-2 chart
    needs a real score-margin/clock model this engine's simplified
    late-game proxy (`trailing`/`is_two_minute`, the same two signals
    _decide_fourth_down already works from, not a raw score margin) can't
    support, so this uses PARAMS["aggression"]["two_point_try"]'s
    existing baseline plus a late-and-trailing bump instead.

    `two_point_bias` is the offense's real coaching staff's own
    two_point_tendency slider (GDD Sec 7.7.2.2), already converted to a
    probability shift by app/engine/coaching.py -- 0.0 for a
    league-average staff, and 0.0 for every caller that has no staff, so
    the calibrated baseline above is unchanged in both cases."""
    base = PARAMS["aggression"]["two_point_try"] + two_point_bias
    if trailing and is_two_minute:
        base += 0.20 + 0.05 * (aggression - 0.5)
    return "two_point" if rng.prob(max(0.0, min(0.9, base))) else "pat"


def two_point_attempt(rng: RNG) -> bool:
    return rng.prob(TWO_POINT_SUCCESS_PROB)
