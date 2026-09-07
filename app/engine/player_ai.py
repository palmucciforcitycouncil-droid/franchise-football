"""
Player-level play-calling AI (GDD Part 1 Sec 6.6), using the real roster
data (app/models/player.py, app/services/depth_chart.py) instead of
team-level ratings. This is the swap-in replacement for the team-level
stand-in functions that were in drive_sim.py -- see that module's
docstring history for why the team-level version existed first.

Composite ratings: the GDD's formulas reference things like
Avg_OL_RunBlock_Rating and DL_RunStop_Rating as if they were single
attributes. The real (Madden-derived) data doesn't have a "RunStop"
field, or separate left/right DTs -- these composites are a documented,
reasonable mapping from what the data actually has, not what the GDD's
prose assumed would exist:
    OL_RunBlock   = run_block
    OL_PassBlock  = pass_block
    DL_RunStop    = avg(tackle, block_shedding)
    DL_PassRush   = avg(power_moves, finesse_moves)
    Coverage      = avg(man_coverage, zone_coverage) -- used for any
                    defender type (CB/S/LB); the GDD calls the LB version
                    "PassCoverage" as if it were a different attribute,
                    but the source data only has one coverage pair, used
                    for everyone.
    RouteRunning  = avg(short, medium, deep route running) for target
                    *selection* (before pass depth is chosen); the specific
                    depth's rating is used once a pass type is picked.
"""
from __future__ import annotations
import math
from dataclasses import dataclass

from app.models.player import Player
from app.services.depth_chart import OffensiveStarters, DefensiveStarters


def _avg(*vals: float) -> float:
    return sum(vals) / len(vals)


def ol_run_block(offense: OffensiveStarters) -> float:
    return _avg(*(p.run_block for p in offense.offensive_line))


def ol_pass_block(offense: OffensiveStarters) -> float:
    return _avg(*(p.pass_block for p in offense.offensive_line))


def dl_run_stop(defense: DefensiveStarters) -> float:
    return _avg(*(_avg(p.tackle, p.block_shedding) for p in defense.defensive_line))


def dl_pass_rush(defense: DefensiveStarters) -> float:
    return _avg(*(_avg(p.power_moves, p.finesse_moves) for p in defense.defensive_line))


def coverage_rating(defender: Player) -> float:
    return _avg(defender.man_coverage, defender.zone_coverage)


def route_running_avg(receiver: Player) -> float:
    return _avg(receiver.short_route_running, receiver.medium_route_running, receiver.deep_route_running)


@dataclass(frozen=True)
class ZoneAdvantage:
    left: float   # our LT/LG (run_block) vs their RE + a DT
    center: float  # our C (run_block) vs their DT average
    right: float  # our RT/RG (run_block) vs their LE + a DT


def run_zone_advantages(offense: OffensiveStarters, defense: DefensiveStarters) -> ZoneAdvantage:
    """
    GDD Sec 6.6.2: "Left Zone: LT & LG vs. opponent RDE & RDT" -- i.e. the
    offense's left side faces the defense's right side (they're mirrored
    when facing each other). The source data doesn't split DT into
    left/right, so each zone borrows one of the two DTs; see module
    docstring.
    """
    dl_stop = lambda p: _avg(p.tackle, p.block_shedding)
    left = _avg(offense.lt.run_block, offense.lg.run_block) - _avg(dl_stop(defense.re), dl_stop(defense.dt1))
    center = offense.c.run_block - _avg(dl_stop(defense.dt1), dl_stop(defense.dt2))
    right = _avg(offense.rt.run_block, offense.rg.run_block) - _avg(dl_stop(defense.le), dl_stop(defense.dt2))
    return ZoneAdvantage(left=left, center=center, right=right)


@dataclass(frozen=True)
class MatchupContext:
    """Everything a play decision needs about this specific matchup,
    computed once per drive rather than recomputed every play."""
    offense: OffensiveStarters
    defense: DefensiveStarters
    ol_run_block: float
    ol_pass_block: float
    dl_run_stop: float
    dl_pass_rush: float
    zones: ZoneAdvantage
    ep_multiplier: float = 1.0  # Score Fidelity System (app/engine/score_fidelity.py) -- see that module's docstring


def build_matchup_context(offense: OffensiveStarters, defense: DefensiveStarters, ep_multiplier: float = 1.0) -> MatchupContext:
    return MatchupContext(
        offense=offense,
        defense=defense,
        ol_run_block=ol_run_block(offense),
        ol_pass_block=ol_pass_block(offense),
        dl_run_stop=dl_run_stop(defense),
        dl_pass_rush=dl_pass_rush(defense),
        zones=run_zone_advantages(offense, defense),
        ep_multiplier=ep_multiplier,
    )


def matchup_adjustment(ctx: MatchupContext, weight: float = 0.01) -> float:
    """GDD Sec 6.6.1 Sec 4.2.2: a positive value means the offense has a
    bigger relative advantage passing than running, nudging P(Pass) up."""
    run_advantage = ctx.ol_run_block - ctx.dl_run_stop
    pass_advantage = ctx.ol_pass_block - ctx.dl_pass_rush
    return (pass_advantage - run_advantage) * weight


@dataclass(frozen=True)
class RunPlayChoice:
    point_of_attack: str  # "left" | "center" | "right"
    advantage: float


def choose_run_point_of_attack(ctx: MatchupContext, rb: Player, rng) -> RunPlayChoice:
    z = ctx.zones
    best = max(("left", z.left), ("center", z.center), ("right", z.right), key=lambda t: t[1])
    zone, advantage = best
    # GDD Sec 6.6.2: an agile RB gets a boost toward Outside (edge) runs, a
    # powerful RB toward Inside/Power (center). Modeled as a small chance
    # to override the pure blocking-advantage pick when the RB's traits
    # strongly favor a different direction.
    if rb.agility > 88 and zone != "left" and zone != "right" and rng.prob(0.35):
        zone = "left" if z.left >= z.right else "right"
        advantage = z.left if zone == "left" else z.right
    elif rb.strength > 88 and zone != "center" and rng.prob(0.35):
        zone = "center"
        advantage = z.center
    return RunPlayChoice(point_of_attack=zone, advantage=advantage)


@dataclass(frozen=True)
class PassTarget:
    receiver: Player
    defender: Player
    mismatch_score: float
    protection_score: float


def choose_pass_target(ctx: MatchupContext, rng, distance: int | None = None) -> PassTarget:
    """GDD Sec 6.6.2: simplified coverage assignment (WR1-CB1, WR2-CB2,
    slot/TE-safety), then target whoever has the biggest mismatch --
    "the receiver with the highest MismatchScore becomes the QB's primary
    read." The GDD's own wording is "primary read," not "only possible
    target": read literally as "always pick argmax," this was a pure
    function of static per-game ratings with nothing that varies play to
    play, so the same (receiver, defender) pair won the calculation on
    every single pass attempt of a game -- a real bug found via the box
    score (item 9/GDD's per-player stat lines), where a 30/30 or 37/37
    target share for one receiver made it obvious in a way play-by-play
    text alone hadn't.

    Fix: weighted-random selection (softmax over mismatch scores) so the
    best mismatch is still targeted most often -- a real "primary read"
    -- but not deterministically every play. `distance` (yards to go)
    tightens the distribution on a clear passing-down / must-convert
    situation (3rd/4th & 7+): a QB going through progressions still
    gravitates hardest to his best matchup when he has to convert, so
    less exploration there than on an early-down shot play."""
    off, defn = ctx.offense, ctx.defense
    assignments = [
        (off.wr1, defn.cb1),
        (off.wr2, defn.cb2),
        (off.te, defn.ss),
    ]
    if off.wr3 is not None:
        assignments.append((off.wr3, defn.fs))

    scores = [route_running_avg(receiver) - coverage_rating(defender) for receiver, defender in assignments]

    temperature = 4.0 if distance is not None and distance >= 7 else 7.0
    top_score = max(scores)
    weights = [math.exp((s - top_score) / temperature) for s in scores]
    receiver, defender = rng.weighted_choice(assignments, weights)
    score = scores[assignments.index((receiver, defender))]

    protection = ctx.ol_pass_block - ctx.dl_pass_rush
    return PassTarget(receiver=receiver, defender=defender, mismatch_score=score, protection_score=protection)
