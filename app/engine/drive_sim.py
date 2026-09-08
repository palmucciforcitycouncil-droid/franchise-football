"""
Down-by-down drive simulation, using real player data for play-calling
and outcome resolution (GDD Part 1 Sec 6.6), not team-level aggregates.

History: this started as a single-Gaussian-per-drive model (one dice roll
decided the whole drive), then became a down-by-down loop using only
team-level ratings (no Player/roster data existed yet), and now uses the
real roster import (app/models/player.py) plus the starting-lineup and
matchup-composite helpers in app/services/depth_chart.py and
app/engine/player_ai.py. It now also runs the full defensive
play-calling decision tree (Sec 6.6.3, app/engine/defensive_ai.py) once
per play -- anticipate/blitz/coverage/run-tactic -- and that call
actually changes pressure, completion odds, and run yardage, not just
narration. A real (if deliberately partial) Penalty System (Sec 6.9) is
wired in -- see the module-level PENALTY_TYPES comment below for what's
modeled and what's cut. What's still NOT here: weather modifiers.
Coaching-tendency inputs (aggression, pace) still come from the
placeholder TeamRatings, since there's no Coach entity yet (Post-MVP).
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import List, Tuple

from .rng import RNG
from .rating import TeamRatings
from .tuning import PARAMS, DRIVE_SIM_PARAMS as P
from .game_state import PlayEvent
from .player_ai import MatchupContext, choose_run_point_of_attack, choose_pass_target, coverage_rating, matchup_adjustment
from .defensive_ai import DefensiveCall, decide_defensive_call, apply_run_tactic, LEAGUE_AVG_YPC, LEAGUE_AVG_YPA
from .gameplan import Gameplan, offense_pass_bias, offense_fourth_down_bias, defense_run_tactic_extra_penalty
from app.models.player import Player
from app.services.depth_chart import DefensiveStarters

MAX_PLAYS_PER_DRIVE = 20  # safety valve against pathological loops


def _pass_probability(
    down: int, distance: int, trailing: bool, is_two_minute: bool, matchup_adjustment: float,
    field_pos: int = 0, gameplan: Gameplan | None = None,
) -> float:
    """GDD Sec 6.6.1: Layer 1 (situational baseline by down & distance),
    Layer 2 (game-state adjustment), Layer 3 (performance/matchup
    adjustment -- now the real OL/DL-vs-DL/OL composite from
    player_ai.matchup_adjustment(), not a team-level run_bias knob).

    `gameplan` is the OFFENSE's Weekly Gameplan (GDD Sec 10.4.1) -- None
    for every AI team, since only the user's team ever has one set."""
    base = PARAMS["mix"]["pass"]  # 0.56 league-average target

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
        base += 0.15 if trailing else -0.20  # urgency vs. milking the clock

    base += matchup_adjustment
    base += offense_pass_bias(gameplan, in_red_zone=field_pos >= 80)

    return max(0.1, min(0.92, base))


def _point_of_attack_defenders(defense: DefensiveStarters, zone: str) -> list[Player]:
    """The specific DL pair engaged at a given run zone -- same pairing
    run_zone_advantages() (player_ai.py) itself uses, e.g. "left" zone is
    the offense's LT/LG vs. the defense's RE/DT1 (mirrored sides)."""
    if zone == "left":
        return [defense.re, defense.dt1]
    if zone == "right":
        return [defense.le, defense.dt2]
    return [defense.dt1, defense.dt2]


def _run_tackler(rng: RNG, defense: DefensiveStarters, zone: str, yards: int) -> str:
    """Solo-tackle/forced-fumble attribution for a run play -- a
    disclosed, GDD-underspecified heuristic (no formula is given): a run
    stuffed at or behind the line (yards <= 2, i.e. the DL actually won
    the point-of-attack battle) credits the real DL pair engaged at that
    zone; a run that gets real yardage past the line credits a real
    linebacker instead (pursuit-and-tackle, not the line), since crediting
    the same point-of-attack DL on every single run regardless of how far
    it went would be unrealistic."""
    if yards <= 2:
        return rng.choice(_point_of_attack_defenders(defense, zone)).full_name
    return rng.choice(defense.linebackers).full_name


def _resolve_run(
    rng: RNG, ctx: MatchupContext, rb: Player, defcall: DefensiveCall,
    field_pos: int = 0, defense_gameplan: Gameplan | None = None,
) -> Tuple[int, str, str, str, str]:
    """GDD Sec 6.6.2 (run) + Sec 6.6.7: point-of-attack chosen from real
    zone blocking advantages, yardage shaped by the winning zone's
    advantage and the RB's own vision/explosiveness, fumble risk shaped
    by the RB's actual ball-security (carrying) rating. The defense's
    Sec 6.6.3 Step 4 run tactic (Plug Gaps/Contain Edge) penalizes the
    zone(s) it committed to stop before point-of-attack is chosen; a
    stacked-box "Run Defense" primary call also drags down the mean
    regardless of direction, and a "Pass Defense" primary (light box)
    helps the offense if it runs into it anyway. `defense_gameplan`
    (GDD Sec 10.4.1) can add an extra red-zone penalty on top of that via
    its Run-Sellout Red Zone Defense style -- None for every AI team.

    Returns (yards, outcome, who, defender_name, fumble_recovered_by).
    defender_name is the real tackler on a "gain" (see _run_tackler) or
    the real defender who forced a "turnover" (fumble) -- same
    attribution logic either way. fumble_recovered_by is only set on a
    fumble, and can be a different player than defender_name (forcing
    and recovering are separate GDD stat categories, Sec 6.7.2) --
    picked from the front seven (DL+LB), not the whole defense, since a
    run-play fumble is recovered in the box, not by a deep secondary
    player."""
    extra_penalty = defense_run_tactic_extra_penalty(defense_gameplan, in_red_zone=field_pos >= 80)
    zones = apply_run_tactic(ctx.zones, defcall.run_tactic, extra_penalty=extra_penalty)
    run_ctx = replace(ctx, zones=zones) if defcall.run_tactic else ctx
    choice = choose_run_point_of_attack(run_ctx, rb, rng)
    advantage = choice.advantage  # roughly -20..+20

    mean = 3.6 + advantage * 0.06 + (rb.ball_carrier_vision - 70) * 0.015
    if defcall.primary == "run_defense":
        mean -= 1.2
    elif defcall.primary == "pass_defense":
        mean += 1.0
    mean *= ctx.ep_multiplier  # Score Fidelity System (app/engine/score_fidelity.py)
    yards = int(round(rng.gauss(mean, 3.8)))

    if advantage > 8 and rng.prob(0.05 + max(0, rb.juke_move - 70) * 0.001):
        yards += int(abs(rng.gauss(6, 4)))  # explosive run

    fumble_rate = max(0.002, PARAMS["turnover"]["fumble_per_rush"] - (rb.carrying - 70) * 0.0002)
    if rng.prob(fumble_rate):
        yards = max(yards, -2)
        forced_by = _run_tackler(rng, ctx.defense, choice.point_of_attack, yards)
        recovered_by = rng.choice(ctx.defense.defensive_line + ctx.defense.linebackers).full_name
        return yards, "turnover", rb.full_name, forced_by, recovered_by

    tackler = _run_tackler(rng, ctx.defense, choice.point_of_attack, yards)
    return yards, "gain", rb.full_name, tackler, ""


def _sack_defender(rng: RNG, ctx: MatchupContext, defcall: DefensiveCall) -> str:
    """Who gets sack credit: the real blitzer if this was a blitz call
    (they're the specific defender most likely to have gotten home), a
    random defensive lineman otherwise (a non-blitzed sack still came
    from someone up front) -- the SAME heuristic _check_roughing_the_passer
    already used independently; factored out so the sacker and a roughing
    penalty on that same sack are guaranteed to name the same player
    instead of two independent random picks."""
    if defcall.blitz.called and defcall.blitz.blitzer is not None:
        return defcall.blitz.blitzer.full_name
    return rng.choice(ctx.defense.defensive_line).full_name


def _resolve_pass(rng: RNG, ctx: MatchupContext, qb: Player, defcall: DefensiveCall, distance: int = 10) -> Tuple[int, str, str, str, str, bool]:
    """GDD Sec 6.6.2 (pass) + Sec 6.6.6: target chosen from real
    route-running-vs-coverage mismatches, pressure from real OL-vs-DL
    protection, completion from real QB accuracy (by depth) + receiver
    catching + the mismatch score, interception risk from accuracy vs.
    the covering defender's real coverage rating. The Sec 6.6.3 blitz
    call adds pressure scaled by the actual blitzer-vs-blocker
    advantage; Zone coverage dampens the mismatch's effect (keep it in
    front, per the GDD's own rationale) while Man leaves it live
    (boom-or-bust); a "Pass Defense" primary trims completion odds a
    touch, "Run Defense" caught looking gives a bump.

    Returns (yards, outcome, who, receiver_name, defender_name,
    pass_defended). `who` is whoever the play should be NARRATED as --
    the receiver on a completion or incompletion, the QB on a sack, but
    the DEFENDER on an interception (the defender made the play, not the
    receiver who got beaten). `receiver_name` is always the actual
    intended target (empty on a sack, which the GDD/real stat convention
    doesn't count as a target at all) -- app/engine/box_score.py needs
    this to credit an interception as a target/no-catch to the right
    receiver, since `who` alone can't carry both names on that play.
    `defender_name` is the real covering defender on this specific
    attempt (the SACKER on a sack, via _sack_defender) -- the Penalty
    System (Sec 6.9) needs it to attribute DPI/Roughing the Passer to the
    actual player involved, not a random guess. `pass_defended` is only
    ever True on an incomplete pass, and only when the defender's real
    coverage (not just an inaccurate throw) is judged to have caused the
    incompletion -- see the PD roll below for the disclosed heuristic."""
    target = choose_pass_target(ctx, rng, distance)

    pressure_prob = max(0.05, min(0.6, 0.30 - target.protection_score * 0.01))
    if defcall.blitz.called:
        pressure_prob = max(0.05, min(0.85, pressure_prob + 0.15 + defcall.blitz.advantage * 0.01))
    if rng.prob(pressure_prob) and rng.prob(0.35):
        sack_yards = -int(abs(rng.gauss(6.5, 3)))
        return sack_yards, "sack", qb.full_name, "", _sack_defender(rng, ctx, defcall), False

    coverage_factor = 0.6 if defcall.coverage == "zone" else 1.15
    effective_mismatch = target.mismatch_score * coverage_factor

    # Depth distribution shifted toward short (real NFL is roughly
    # 55% short / 30% medium / 15% deep by target depth) -- the original
    # weighting leaned medium/deep too often relative to how often a
    # double-digit mismatch score actually occurs, which was a big part
    # of why per-completion yardage came out at ~18 instead of ~11-12.
    if effective_mismatch > 18:
        depth = "deep" if rng.prob(0.35) else "medium"
    elif effective_mismatch < -8:
        depth = "short"
    else:
        depth = "short" if rng.prob(0.6) else "medium"

    accuracy = {"short": qb.throw_accuracy_short, "medium": qb.throw_accuracy_mid, "deep": qb.throw_accuracy_deep}[depth]
    completion_pct = 0.50 + (accuracy - 70) * 0.004 + (target.receiver.catching - 70) * 0.003 + effective_mismatch * 0.005
    if defcall.primary == "pass_defense":
        completion_pct -= 0.03
    elif defcall.primary == "run_defense":
        completion_pct += 0.05
    completion_pct *= ctx.ep_multiplier  # Score Fidelity System (app/engine/score_fidelity.py)
    completion_pct = max(0.20, min(0.88, completion_pct))

    if rng.prob(1 - completion_pct):
        int_rate = max(0.01, 0.05 - (accuracy - 70) * 0.0005 + (coverage_rating(target.defender) - 70) * 0.0004)
        if rng.prob(int_rate):
            # who = the player who made the play, not the intended target --
            # an interception is credited to the defender who caught it.
            return 0, "turnover", target.defender.full_name, target.receiver.full_name, target.defender.full_name, False
        # Pass Defended (PD) roll: a disclosed, GDD-underspecified split
        # between a real pass breakup (the defender won the coverage
        # matchup) and a plain incompletion (an inaccurate/uncontested
        # throw with no real defensive play) -- more negative
        # effective_mismatch (the defender winning) raises the odds.
        pd_prob = max(0.05, min(0.55, 0.15 - effective_mismatch * 0.01))
        pass_defended = rng.prob(pd_prob)
        return 0, "incomplete", target.receiver.full_name, target.receiver.full_name, target.defender.full_name, pass_defended

    air_yards = {"short": 5, "medium": 10, "deep": 19}[depth]
    yac = max(0, rng.gauss((target.receiver.change_of_direction - 75) * 0.08, 2.5))
    yards = int((air_yards + yac) * ctx.ep_multiplier)  # Score Fidelity System (app/engine/score_fidelity.py)
    return yards, "gain", target.receiver.full_name, target.receiver.full_name, target.defender.full_name, False


def _fg_distance_bucket(attempt_yards: int) -> str:
    if attempt_yards < 30:
        return "<30"
    if attempt_yards < 40:
        return "30-39"
    if attempt_yards < 50:
        return "40-49"
    return "50+"


def _kicker_adjusted_prob(base_prob: float, kicker: Player | None) -> float:
    """A real kicker's rating nudges a league-average bucket probability
    up or down rather than replacing it outright -- used for both field
    goals and PATs (a PAT is functionally a ~33-yard field goal)."""
    if kicker is None:
        return base_prob
    return max(0.35, min(0.99, base_prob + (kicker.kick_accuracy - 80) * 0.004))


def _attempt_field_goal(rng: RNG, pos: int, kicker: Player | None) -> Tuple[bool, int]:
    attempt_yards = (100 - pos) + 17  # line of scrimmage to goal + snap/hold depth
    base_prob = PARAMS["special"]["fg_make_prob"][_fg_distance_bucket(attempt_yards)]
    return rng.prob(_kicker_adjusted_prob(base_prob, kicker)), attempt_yards


# GDD Sec 6.9 Penalty System -- a real weighted type table + attribution +
# situational accept/decline, but a deliberate SUBSET of the full catalog:
# 7 types total (false start, delay of game, illegal formation, offside,
# offensive holding, defensive pass interference, roughing the passer),
# not the dozen-plus real penalty types the GDD lists. No
# Team_Discipline_Modifier/Coach_Modifier: neither a
# "discipline" player attribute nor a Coach entity exists in the real
# (Madden-derived) data, so attribution picks from the relevant personnel
# group rather than being rating-weighted -- the same category of gap as
# player_ai.py's documented composite-attribute mappings. Also scoped
# out entirely: penalties on touchdowns, turnovers, and safeties (real
# NFL accept/decline gets genuinely complicated there -- e.g. a defense
# can decline a holding call to let an interception return stand) --
# in-play penalties here only apply to "normal" continuing plays.
@dataclass(frozen=True)
class PenaltyOutcome:
    desc: str
    down: int
    distance: int
    pos: int


def _check_pre_snap_penalty(rng: RNG, ctx: MatchupContext) -> Tuple[str, str] | None:
    """False start / delay of game / illegal formation / offside --
    rolled before the play type is even decided, since these happen
    before anyone knows what was coming. Always enforced (no
    accept/decline: there's no completed play yet to compare against,
    matching real NFL practice). Returns (description, side) or None."""
    off, defn = ctx.offense, ctx.defense
    p = PARAMS["penalty"]["pre_snap"]
    if rng.prob(p["false_start"]):
        return f"False start, {rng.choice(off.offensive_line).full_name}: 5 yards", "offense"
    if rng.prob(p["delay_of_game"]):
        return f"Delay of game, {off.qb.full_name}: 5 yards", "offense"
    if rng.prob(p["illegal_formation"]):
        return f"Illegal formation, {rng.choice(off.offensive_line).full_name}: 5 yards", "offense"
    if rng.prob(p["offside"]):
        return f"Offside, {rng.choice(defn.defensive_line).full_name}: 5 yards", "defense"
    return None


def _check_offensive_holding(rng: RNG, ctx: MatchupContext, down: int, distance: int, pos: int, real_yards: int) -> PenaltyOutcome | None:
    """Rolled only on run plays. Real accept/decline: the defense (the
    beneficiary -- holding is called against the offense) compares the
    real play's result against enforcing the penalty, and only accepts
    if enforcement leaves the offense worse off. This is the one case in
    this subset where the comparison is genuinely non-trivial: a run
    stuffed for a bigger loss than the penalty yardage is worse for the
    offense already, so the defense should (and here does) decline and
    let the real result stand."""
    if not rng.prob(PARAMS["penalty"]["in_play"]["offensive_holding"]):
        return None
    if not _holding_would_be_accepted(distance, real_yards):
        return None  # real result already worse for the offense -- defense declines
    holding_yards = PARAMS["penalty"]["holding_yards"]
    who = rng.choice(ctx.offense.offensive_line).full_name
    return PenaltyOutcome(
        desc=f"Holding, {who}: {holding_yards} yards, repeat {down}{_ordinal_suffix(down)} down",
        down=down, distance=distance + holding_yards, pos=max(0, pos - holding_yards),
    )


def _holding_would_be_accepted(distance: int, real_yards: int) -> bool:
    """Pure accept/decline decision, split out from _check_offensive_holding
    so the logic itself (not just the RNG-gated wrapper) is directly
    testable: the defense accepts only if enforcing the 10-yard penalty
    leaves the offense with MORE distance-to-go than the real play result
    already did."""
    holding_yards = PARAMS["penalty"]["holding_yards"]
    distance_if_declined = max(0, distance - real_yards)
    distance_if_accepted = distance + holding_yards
    return distance_if_accepted > distance_if_declined


def _check_defensive_pass_interference(rng: RNG, pos: int, defender_name: str) -> PenaltyOutcome | None:
    """Rolled only on incomplete passes, attributed to the real covering
    defender from that specific attempt (app/engine/player_ai.py's
    choose_pass_target result, threaded through _resolve_pass) rather
    than a random guess. No accept/decline needed -- a spot foul +
    automatic first down is essentially always better for the offense
    than the 0 yards of an incomplete pass. Enforced yardage is a flat
    value (tuning.py's dpi_yards), not the real spot of the (simulated)
    foul -- modeling exactly where downfield the pass was broken up is
    more precision than this subset aims for. Capped so it can't itself
    produce a touchdown, matching the "no penalties on scores" scope cut."""
    if not defender_name or not rng.prob(PARAMS["penalty"]["in_play"]["defensive_pass_interference"]):
        return None
    new_pos = min(99, pos + PARAMS["penalty"]["dpi_yards"])
    return PenaltyOutcome(
        desc=f"Defensive pass interference, {defender_name}: {PARAMS['penalty']['dpi_yards']} yards, automatic first down",
        down=1, distance=10, pos=new_pos,
    )


def _check_roughing_the_passer(rng: RNG, sacker_name: str, pos: int) -> PenaltyOutcome | None:
    """Rolled only on sacks. Attributed to the SAME real defender who got
    sack credit on this exact play (drive_sim.py's _sack_defender,
    computed once in _resolve_pass and threaded through as
    defender_name) -- previously this rolled its own independent random
    pick, which could (and did) name a different player than the sack
    itself for the same play; a real hit on the QB and the resulting
    penalty should always be the same person. No accept/decline needed,
    same reasoning as DPI: automatic first down + 15 yards from the
    previous spot is always better for the offense than the sack that
    just happened."""
    if not rng.prob(PARAMS["penalty"]["in_play"]["roughing_the_passer"]):
        return None
    who = sacker_name
    yards = PARAMS["penalty"]["roughing_yards"]
    new_pos = min(99, pos + yards)
    return PenaltyOutcome(
        desc=f"Roughing the passer, {who}: {yards} yards, automatic first down",
        down=1, distance=10, pos=new_pos,
    )


def _ordinal_suffix(n: int) -> str:
    return {1: "st", 2: "nd", 3: "rd"}.get(n, "th")


def _decide_fourth_down(
    pos: int, distance: int, trailing: bool, aggression: float, rng: RNG,
    offense_gameplan: Gameplan | None = None,
) -> str:
    """Simplified stand-in for the GDD's EP-based 4th-down model (Sec
    6.6.4), which needs full P(convert) tables this project doesn't have
    yet. Returns "go", "field_goal", or "punt". `offense_gameplan`'s
    Off. Aggressiveness (GDD Sec 10.4.1) adds to the existing
    ratings-derived `aggression` term -- None for every AI team."""
    in_fg_range = pos >= 62  # roughly a <=55-yard attempt
    short_yardage = distance <= 2

    go_chance = P.fourth_down_boost + 0.05 * (aggression - 0.5) + offense_fourth_down_bias(offense_gameplan)
    if trailing:
        go_chance += 0.15
    if short_yardage:
        go_chance += 0.15
    if not in_fg_range and pos < 45:
        go_chance += 0.10  # too far to punt for great value, too far to kick

    if rng.prob(max(0.0, min(0.9, go_chance))):
        return "go"
    if in_fg_range:
        return "field_goal"
    return "punt"


def _punt_result(rng: RNG, pos: int) -> int:
    """Returns the receiving team's new field position (0..100 from their
    own perspective)."""
    net = P.punt_net_mu + rng.gauss(0, P.punt_net_sigma)
    receiving_spot_from_kicking_pov = pos + net  # how far up the (kicking team's) field the ball ends up
    new_pos = 100 - receiving_spot_from_kicking_pov
    return max(2, min(40, int(round(new_pos))))


def simulate_drive(
    rng: RNG,
    ctx: MatchupContext,
    offense_ratings: TeamRatings,
    field_pos: int,
    *,
    is_two_minute: bool = False,
    trailing: bool = False,
    fourth_down_ok: bool = False,
    off_ypc: float = LEAGUE_AVG_YPC,
    off_ypa: float = LEAGUE_AVG_YPA,
    offense_gameplan: Gameplan | None = None,
    defense_gameplan: Gameplan | None = None,
) -> Tuple[int, str, int, int, int, int, List[PlayEvent]]:
    """
    Simulates one drive down-by-down using real starters (ctx). Returns:
        points, summary, next_field_pos, plays, yards, turnovers, play_events

    field_pos is 0..100: the offense's distance traveled toward the
    opponent's end zone (100 = touchdown). offense_ratings is only used
    for aggression (4th-down tendency) -- a coaching-tendency proxy until
    a real Coach entity exists (Post-MVP). off_ypc/off_ypa are the
    offense's own yards-per-carry/attempt SO FAR THIS GAME (not this
    drive) -- the "offensive in-game performance" input to the
    defense's Sec 6.6.3 Step 1 anticipation (game_sim.py passes in the
    running totals from before this drive); defaults to league average
    for a drive with no prior offensive plays yet. offense_gameplan/
    defense_gameplan (GDD Sec 10.4.1's Weekly Gameplan) are None for
    every AI team -- only the user's team ever has one set
    (season_state.py's simulate_current_week looks it up).
    """
    down = 1
    distance = 10
    pos = field_pos
    total_yards = 0
    total_plays = 0
    turnovers = 0
    play_events: List[PlayEvent] = []

    aggression = offense_ratings.aggression + (0.15 if fourth_down_ok else 0.0)
    matchup_adj = matchup_adjustment(ctx)
    qb = ctx.offense.qb
    rb = ctx.offense.hb
    kicker = ctx.offense.k

    while total_plays < MAX_PLAYS_PER_DRIVE:
        total_plays += 1

        if down == 4:
            decision = _decide_fourth_down(pos, distance, trailing, aggression, rng, offense_gameplan=offense_gameplan)
            if decision == "punt":
                next_pos = _punt_result(rng, pos)
                play_events.append(PlayEvent(down, distance, pos, "punt", 0, "Punt", "punt"))
                return 0, "Punt", next_pos, total_plays, total_yards, turnovers, play_events
            if decision == "field_goal":
                made, attempt_yards = _attempt_field_goal(rng, pos, kicker)
                if made:
                    play_events.append(PlayEvent(down, distance, pos, "field_goal", 0,
                                                  f"{attempt_yards}-yard field goal is GOOD", "field_goal"))
                    return 3, "FG", 25, total_plays, total_yards, turnovers, play_events
                play_events.append(PlayEvent(down, distance, pos, "field_goal", 0,
                                              f"{attempt_yards}-yard field goal is NO GOOD", "turnover"))
                return 0, "Missed FG", max(2, 100 - pos), total_plays, total_yards, turnovers, play_events
            # else "go" -- fall through to a normal play below

        # Pre-snap penalty check (GDD Sec 6.9, see PenaltyOutcome section
        # above for what's modeled and what's cut). Independent of play
        # type -- rolled before is_pass is even decided.
        pre_snap = _check_pre_snap_penalty(rng, ctx)
        if pre_snap is not None:
            pre_down, pre_distance, pre_pos = down, distance, pos
            desc, side = pre_snap
            if side == "offense":
                pos = max(0, pos - 5)
                distance += 5
            else:
                pos = min(99, pos + 5)
                distance = max(1, distance - 5)
                if distance <= 0:
                    down, distance = 1, 10
            play_events.append(PlayEvent(pre_down, pre_distance, pre_pos, "penalty", 0, desc, "penalty"))
            continue

        # Captured before resolving the play: a PlayEvent should record the
        # down/distance/field-position the play was actually run under, not
        # whatever down/distance/pos become afterward (a real bug this had
        # before -- e.g. a 2nd-and-9 sack was being logged as "3rd & 19").
        play_down, play_distance, play_start_pos = down, distance, pos

        # GDD Sec 6.6.3: the defense's own four-step call, computed fresh
        # every play since it depends on down/distance/field position,
        # unlike the per-drive MatchupContext.
        defcall = decide_defensive_call(
            ctx, down, distance, pos, trailing, is_two_minute, off_ypc, off_ypa, rng,
            gameplan=defense_gameplan,
        )

        pass_prob = _pass_probability(
            down, distance, trailing, is_two_minute, matchup_adj,
            field_pos=pos, gameplan=offense_gameplan,
        )
        is_pass = rng.prob(pass_prob)

        fumble_recovered_by = ""
        if is_pass:
            yards, outcome, who, receiver_name, defender_name, pass_defended = _resolve_pass(rng, ctx, qb, defcall, distance)
            play_type = "pass"
        else:
            yards, outcome, who, defender_name, fumble_recovered_by = _resolve_run(
                rng, ctx, rb, defcall, field_pos=pos, defense_gameplan=defense_gameplan,
            )
            play_type = "run"
            receiver_name = ""
            pass_defended = False

        if outcome == "turnover":
            turnovers += 1
            spot = max(0, min(100, pos + yards))
            kind = f"Interception ({who})" if is_pass else f"Fumble lost ({who})"
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, kind, "turnover", defensive_call=defcall.description, receiver_name=receiver_name, defender_name=defender_name, fumble_recovered_by=fumble_recovered_by))
            return 0, kind, max(2, 100 - spot), total_plays, total_yards, turnovers, play_events

        total_yards += max(0, yards)
        raw_pos = pos + yards

        if raw_pos <= 0:
            # Safety: tackled (or sacked) behind their own goal line. Points
            # go to the *defense*, not this (offense's) drive -- the caller
            # (game_sim.py) special-cases the "Safety" summary text to award
            # them there, since this function only reports the offense's score.
            desc = f"{who} {'sacked' if outcome == 'sack' else 'tackled'} for a safety"
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, "safety", defensive_call=defcall.description, receiver_name=receiver_name, defender_name=defender_name))
            return 0, "Safety", 35, total_plays, total_yards, turnovers, play_events

        # In-play penalty check (GDD Sec 6.9) -- only for plays that stay
        # in the "normal" zone: the safety case already returned above,
        # and raw_pos < 100 excludes a would-be touchdown here (see the
        # PenaltyOutcome section's docstring for why TDs/turnovers/
        # safeties are scoped out of in-play penalty consideration).
        if raw_pos < 100:
            penalty = None
            if not is_pass:
                penalty = _check_offensive_holding(rng, ctx, down, distance, pos, yards)
            elif outcome == "incomplete":
                penalty = _check_defensive_pass_interference(rng, pos, defender_name)
            elif outcome == "sack":
                penalty = _check_roughing_the_passer(rng, defender_name, pos)
            if penalty is not None:
                play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, penalty.desc, "penalty", defensive_call=defcall.description, receiver_name=receiver_name, defender_name=defender_name))
                down, distance, pos = penalty.down, penalty.distance, penalty.pos
                continue

        pos = min(100, raw_pos)

        if pos >= 100:
            made_pat = rng.prob(_kicker_adjusted_prob(P.pat_make, kicker))
            pts = 7 if made_pat else 6
            verb = "pass to" if is_pass else "run by"
            desc = f"{qb.full_name if is_pass else ''} {verb} {who} for {yards} yards, TOUCHDOWN".strip()
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, "touchdown", defensive_call=defcall.description, receiver_name=receiver_name))
            return pts, "TD", 25, total_plays, total_yards, turnovers, play_events

        gained_first_down = yards >= distance
        if outcome == "sack":
            desc = f"{who} sacked for a loss of {-yards} yards" if yards < 0 else f"{who} sacked, no loss"
        elif outcome == "incomplete":
            desc = f"Incomplete pass intended for {who}"
        elif is_pass:
            desc = f"Pass to {who} for {yards} yards"
        else:
            desc = f"{who} run for {yards} yards"

        if gained_first_down:
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, "first_down", defensive_call=defcall.description, receiver_name=receiver_name, defender_name=defender_name, pass_defended=pass_defended))
            down, distance = 1, 10
            continue

        # A loss (sack, tackle for loss) must increase distance-to-go, not
        # just fail to decrease it -- max(0, yards) was silently treating
        # every loss as a 0-yard play for down/distance purposes.
        play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, outcome, defensive_call=defcall.description, receiver_name=receiver_name, defender_name=defender_name, pass_defended=pass_defended))
        distance -= yards
        down += 1

        if down > 4:
            spot = max(2, 100 - pos)
            return 0, "Turnover on downs", spot, total_plays, total_yards, turnovers, play_events

    # Safety valve: ran out of play budget mid-drive (shouldn't happen in
    # practice) -- treat it as a punt from the current spot.
    next_pos = _punt_result(rng, pos)
    return 0, "Punt (drive length limit)", next_pos, total_plays, total_yards, turnovers, play_events
