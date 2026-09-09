"""
Defensive play-calling AI (GDD Part 1 Sec 6.6.3): a four-step decision
process -- anticipate the offense, decide blitz, decide coverage, and
(if run defense is called) pick a run tactic. This is the defense's
counterpart to app/engine/player_ai.py's offensive play-calling, and
plugs into drive_sim.py's per-play resolution so a defensive call
actually changes outcomes (pressure, completion odds, run yardage),
not just narration.

Deliberate scope cuts (see HANDOFF.md's Known Gaps list, now updated):
no real injury signal feeds Step 1 (no injury system exists yet --
Post-MVP), and the personnel labels in DefensivePrimary (Nickel/Dime/
Base) are cosmetic -- DefensiveStarters is still a fixed 4-3-ish 11
(depth_chart.py), not a swappable package. The blitz assignment and
coverage matchups ARE real: they use actual Player ratings, not a
placeholder.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Literal, Optional

from app.models.player import Player
from app.services.depth_chart import OffensiveStarters, DefensiveStarters
from .player_ai import MatchupContext, ZoneAdvantage
from .gameplan import Gameplan, defense_blitz_bias, defense_coverage_man_prob, defense_run_tactic_extra_penalty

# Same softmax-temperature scale as player_ai.py's TARGET_TEMPERATURE_*/
# ZONE_TEMPERATURE (a ~0-99 Madden attribute-average difference) --
# picked for the same reason: see decide_blitz's own docstring below.
BLITZER_TEMPERATURE = 45.0

LEAGUE_AVG_YPC = 4.2
LEAGUE_AVG_YPA = 7.0

DefensivePrimary = Literal["pass_defense", "run_defense", "standard"]
Coverage = Literal["man", "zone"]
RunTactic = Literal["plug_gaps", "contain_edge"]


def _avg(*vals: float) -> float:
    return sum(vals) / len(vals)


def _pass_rush_rating(defender: Player) -> float:
    return _avg(defender.power_moves, defender.finesse_moves)


def anticipated_pass_prob(
    down: int, distance: int, trailing: bool, is_two_minute: bool,
    off_ypc: float, off_ypa: float,
) -> float:
    """Step 1: a lightweight, defense-side re-derivation of the offense's
    own situational baseline (GDD Sec 6.6.1 Layers 1-2: down/distance,
    score/time), plus a performance layer from the offense's own in-game
    YPC/YPA. Deliberately does NOT use the offense's true internal
    matchup_adjustment (Sec 6.6.1 Layer 3, player_ai.matchup_adjustment)
    -- a real defensive coordinator reacts to what he can observe (down,
    distance, the box score so far), not the offense's hidden talent
    differential. That asymmetry is the point, not an oversight."""
    base = 0.56

    if down == 2:
        if distance >= 8:
            base += 0.15
        elif distance <= 3:
            base -= 0.10
    elif down >= 3:
        if distance >= 8:
            base += 0.30
        elif distance <= 2:
            base -= 0.20
        else:
            base += 0.05

    if is_two_minute:
        base += 0.15 if trailing else -0.20

    ypa_edge = (off_ypa - LEAGUE_AVG_YPA) * 0.02
    ypc_edge = (off_ypc - LEAGUE_AVG_YPC) * 0.02
    base += ypa_edge - ypc_edge

    return max(0.05, min(0.95, base))


def choose_primary(anticipated_pass: float) -> DefensivePrimary:
    """GDD Sec 6.6.3 Step 1 thresholds: >0.65 obvious pass, <0.35 obvious
    run, otherwise balanced/standard."""
    if anticipated_pass > 0.65:
        return "pass_defense"
    if anticipated_pass < 0.35:
        return "run_defense"
    return "standard"


@dataclass(frozen=True)
class BlitzCall:
    called: bool
    blitzer: Optional[Player] = None
    target: Optional[Player] = None  # the RB/TE left in to help block, if any
    advantage: float = 0.0          # blitzer's pass-rush rating minus target's pass_block


def decide_blitz(
    defense: DefensiveStarters, offense: OffensiveStarters,
    down: int, distance: int, field_pos: int, rng,
    gameplan: Gameplan | None = None,
) -> BlitzCall:
    """Step 2: baseline 15% blitz chance, +20% on 3rd & 5+, +15% in the
    red zone (field_pos >= 80, i.e. inside the opponent's 20). If called,
    finds the weaker pass-blocking of the RB/TE and assigns the blitzer
    (LB or S) with the biggest rush-vs-block advantage against them.

    `gameplan` is the DEFENSE's Weekly Gameplan (GDD Sec 10.4.1) -- None
    for every AI team, since only the user's team ever has one set.

    The blitzer itself is a weighted-random pick among the 5 candidates,
    not the single best rush-vs-block matchup every time -- a
    deterministic argmax here sent every blitz of a game (and most of a
    season, since ratings don't change play to play) at the same
    linebacker, which is what let one player rack up 65 sacks in an
    18-week season during this engine's stat-realism audit (HANDOFF.md
    item 36) -- the same bug class player_ai.py's choose_pass_target and
    choose_run_point_of_attack were fixed for."""
    chance = 0.15
    if down >= 3 and distance >= 5:
        chance += 0.20
    if field_pos >= 80:
        chance += 0.15
    chance += defense_blitz_bias(gameplan, in_red_zone=field_pos >= 80)
    if not rng.prob(max(0.0, min(0.9, chance))):
        return BlitzCall(called=False)

    target = offense.hb if offense.hb.pass_block <= offense.te.pass_block else offense.te
    blitzers = [defense.lolb, defense.mlb, defense.rolb, defense.fs, defense.ss]
    scores = [_pass_rush_rating(p) - target.pass_block for p in blitzers]
    top_score = max(scores)
    weights = [math.exp((s - top_score) / BLITZER_TEMPERATURE) for s in scores]
    best = rng.weighted_choice(blitzers, weights)
    advantage = _pass_rush_rating(best) - target.pass_block
    return BlitzCall(called=True, blitzer=best, target=target, advantage=advantage)


def decide_coverage(
    down: int, distance: int, field_pos: int, blitz_called: bool, rng,
    gameplan: Gameplan | None = None,
) -> Coverage:
    """Step 3. GDD table: 3rd & 8+ -> zone (prevent the big play); goal
    line (field_pos >= 90, inside the 10) -> man (less space to cover);
    a called blitz -> man (win 1-on-1 while pressure gets home);
    otherwise a 60/40 zone/man mix to keep the offense guessing, unless
    the defense's Weekly Gameplan (GDD Sec 10.4.1) sets a Coverage
    Scheme, in which case that mix replaces the 60/40 default -- the
    three situational overrides above still take priority regardless."""
    if down >= 3 and distance >= 8:
        return "zone"
    if field_pos >= 90:
        return "man"
    if blitz_called:
        return "man"
    man_prob = defense_coverage_man_prob(gameplan)
    if man_prob is not None:
        return "man" if rng.prob(man_prob) else "zone"
    return "zone" if rng.prob(0.6) else "man"


def decide_run_tactic(ctx: MatchupContext) -> RunTactic:
    """Step 4: predicts Inside vs. Outside run using the SAME zone
    blocking-advantage math the offense's own play-caller uses (Sec
    6.6.2's OL-run-block-vs-DL-run-stop-by-zone) -- a real DC is scouting
    the same matchups the offense's playcaller is looking at, not a
    separate hidden signal. Center = "Plug Gaps"; either edge = "Contain
    Edge". Note this doesn't account for the offense's RB-trait-driven
    override in choose_run_point_of_attack (agile RB to the edge, power
    RB to the middle) -- the defense scouts blocking, not the specific
    back's tendencies, so it can still get out-guessed by that override."""
    z = ctx.zones
    best_zone = max(("left", z.left), ("center", z.center), ("right", z.right), key=lambda t: t[1])[0]
    return "plug_gaps" if best_zone == "center" else "contain_edge"


def apply_run_tactic(zones: ZoneAdvantage, tactic: Optional[RunTactic], extra_penalty: float = 0.0) -> ZoneAdvantage:
    """Applies the defense's committed run tactic as a penalty to the
    offense's zone advantage in the zone(s) the defense sold out to stop
    -- if the defense guessed right, that zone gets harder to run; if the
    RB-trait override or the other zone's advantage wins anyway, the
    defense guessed wrong and pays no extra penalty there.

    `extra_penalty` (from a Weekly Gameplan's Run-Sellout Red Zone
    Defense style, GDD Sec 10.4.1) commits harder to the same zone(s) on
    top of the base -6; 0.0 for every AI team and for any non-Run-Sellout
    style."""
    penalty = 6 + extra_penalty
    if tactic == "plug_gaps":
        return ZoneAdvantage(left=zones.left, center=zones.center - penalty, right=zones.right)
    if tactic == "contain_edge":
        return ZoneAdvantage(left=zones.left - penalty, center=zones.center, right=zones.right - penalty)
    return zones


@dataclass(frozen=True)
class DefensiveCall:
    primary: DefensivePrimary
    blitz: BlitzCall
    coverage: Coverage
    run_tactic: Optional[RunTactic]

    @property
    def description(self) -> str:
        parts = [{"pass_defense": "Pass Defense", "run_defense": "Run Defense", "standard": "Standard"}[self.primary]]
        if self.blitz.called and self.blitz.blitzer is not None:
            parts.append(f"Blitz ({self.blitz.blitzer.full_name})")
        parts.append("Man" if self.coverage == "man" else "Zone")
        if self.run_tactic == "plug_gaps":
            parts.append("Plug Gaps")
        elif self.run_tactic == "contain_edge":
            parts.append("Contain Edge")
        return ", ".join(parts)


def decide_defensive_call(
    ctx: MatchupContext, down: int, distance: int, field_pos: int,
    trailing: bool, is_two_minute: bool, off_ypc: float, off_ypa: float, rng,
    gameplan: Gameplan | None = None,
) -> DefensiveCall:
    """The full four-step process, run once per play (down/distance/field
    position all vary play to play, unlike the per-drive MatchupContext).

    `gameplan` is the DEFENSE's Weekly Gameplan (GDD Sec 10.4.1) -- None
    for every AI team."""
    anticipated = anticipated_pass_prob(down, distance, trailing, is_two_minute, off_ypc, off_ypa)
    primary = choose_primary(anticipated)
    blitz = decide_blitz(ctx.defense, ctx.offense, down, distance, field_pos, rng, gameplan=gameplan)
    coverage = decide_coverage(down, distance, field_pos, blitz.called, rng, gameplan=gameplan)
    run_tactic = decide_run_tactic(ctx) if primary == "run_defense" else None
    return DefensiveCall(primary=primary, blitz=blitz, coverage=coverage, run_tactic=run_tactic)
