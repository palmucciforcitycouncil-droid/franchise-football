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
narration. What's still NOT here: weather modifiers and the full
penalty-type catalog (Sec 6.9). Coaching-tendency inputs (aggression,
pace) still come from the placeholder TeamRatings, since there's no
Coach entity yet (Post-MVP).
"""
from __future__ import annotations
from dataclasses import replace
from typing import List, Tuple

from .rng import RNG
from .rating import TeamRatings
from .tuning import PARAMS, DRIVE_SIM_PARAMS as P
from .game_state import PlayEvent
from .player_ai import MatchupContext, choose_run_point_of_attack, choose_pass_target, coverage_rating, matchup_adjustment
from .defensive_ai import DefensiveCall, decide_defensive_call, apply_run_tactic, LEAGUE_AVG_YPC, LEAGUE_AVG_YPA
from app.models.player import Player

MAX_PLAYS_PER_DRIVE = 20  # safety valve against pathological loops


def _pass_probability(down: int, distance: int, trailing: bool, is_two_minute: bool, matchup_adjustment: float) -> float:
    """GDD Sec 6.6.1: Layer 1 (situational baseline by down & distance),
    Layer 2 (game-state adjustment), Layer 3 (performance/matchup
    adjustment -- now the real OL/DL-vs-DL/OL composite from
    player_ai.matchup_adjustment(), not a team-level run_bias knob)."""
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

    return max(0.1, min(0.92, base))


def _resolve_run(rng: RNG, ctx: MatchupContext, rb: Player, defcall: DefensiveCall) -> Tuple[int, str, str]:
    """GDD Sec 6.6.2 (run) + Sec 6.6.7: point-of-attack chosen from real
    zone blocking advantages, yardage shaped by the winning zone's
    advantage and the RB's own vision/explosiveness, fumble risk shaped
    by the RB's actual ball-security (carrying) rating. The defense's
    Sec 6.6.3 Step 4 run tactic (Plug Gaps/Contain Edge) penalizes the
    zone(s) it committed to stop before point-of-attack is chosen; a
    stacked-box "Run Defense" primary call also drags down the mean
    regardless of direction, and a "Pass Defense" primary (light box)
    helps the offense if it runs into it anyway."""
    zones = apply_run_tactic(ctx.zones, defcall.run_tactic)
    run_ctx = replace(ctx, zones=zones) if defcall.run_tactic else ctx
    choice = choose_run_point_of_attack(run_ctx, rb, rng)
    advantage = choice.advantage  # roughly -20..+20

    mean = 3.6 + advantage * 0.06 + (rb.ball_carrier_vision - 70) * 0.015
    if defcall.primary == "run_defense":
        mean -= 1.2
    elif defcall.primary == "pass_defense":
        mean += 1.0
    yards = int(round(rng.gauss(mean, 3.8)))

    if advantage > 8 and rng.prob(0.05 + max(0, rb.juke_move - 70) * 0.001):
        yards += int(abs(rng.gauss(6, 4)))  # explosive run

    fumble_rate = max(0.002, PARAMS["turnover"]["fumble_per_rush"] - (rb.carrying - 70) * 0.0002)
    if rng.prob(fumble_rate):
        return max(yards, -2), "turnover", rb.full_name

    return yards, "gain", rb.full_name


def _resolve_pass(rng: RNG, ctx: MatchupContext, qb: Player, defcall: DefensiveCall) -> Tuple[int, str, str, str]:
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

    Returns (yards, outcome, who, receiver_name). `who` is whoever the
    play should be NARRATED as -- the receiver on a completion or
    incompletion, the QB on a sack, but the DEFENDER on an interception
    (the defender made the play, not the receiver who got beaten).
    `receiver_name` is always the actual intended target (empty on a
    sack, which the GDD/real stat convention doesn't count as a target
    at all) -- app/engine/box_score.py needs this to credit an
    interception as a target/no-catch to the right receiver, since
    `who` alone can't carry both names on that play."""
    target = choose_pass_target(ctx)

    pressure_prob = max(0.05, min(0.6, 0.30 - target.protection_score * 0.01))
    if defcall.blitz.called:
        pressure_prob = max(0.05, min(0.85, pressure_prob + 0.15 + defcall.blitz.advantage * 0.01))
    if rng.prob(pressure_prob) and rng.prob(0.35):
        sack_yards = -int(abs(rng.gauss(6.5, 3)))
        return sack_yards, "sack", qb.full_name, ""

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
    completion_pct = max(0.20, min(0.88, completion_pct))

    if rng.prob(1 - completion_pct):
        int_rate = max(0.01, 0.05 - (accuracy - 70) * 0.0005 + (coverage_rating(target.defender) - 70) * 0.0004)
        if rng.prob(int_rate):
            # who = the player who made the play, not the intended target --
            # an interception is credited to the defender who caught it.
            return 0, "turnover", target.defender.full_name, target.receiver.full_name
        return 0, "incomplete", target.receiver.full_name, target.receiver.full_name

    air_yards = {"short": 5, "medium": 10, "deep": 19}[depth]
    yac = max(0, rng.gauss((target.receiver.change_of_direction - 75) * 0.08, 2.5))
    yards = int(air_yards + yac)
    return yards, "gain", target.receiver.full_name, target.receiver.full_name


def _fg_distance_bucket(attempt_yards: int) -> str:
    if attempt_yards < 30:
        return "<30"
    if attempt_yards < 40:
        return "30-39"
    if attempt_yards < 50:
        return "40-49"
    return "50+"


def _attempt_field_goal(rng: RNG, pos: int, kicker: Player | None) -> Tuple[bool, int]:
    attempt_yards = (100 - pos) + 17  # line of scrimmage to goal + snap/hold depth
    base_prob = PARAMS["special"]["fg_make_prob"][_fg_distance_bucket(attempt_yards)]
    if kicker is not None:
        # Real kicker rating nudges the league-average bucket probability
        # up or down rather than replacing it outright.
        base_prob = max(0.35, min(0.99, base_prob + (kicker.kick_accuracy - 80) * 0.004))
    return rng.prob(base_prob), attempt_yards


def _decide_fourth_down(pos: int, distance: int, trailing: bool, aggression: float, rng: RNG) -> str:
    """Simplified stand-in for the GDD's EP-based 4th-down model (Sec
    6.6.4), which needs full P(convert) tables this project doesn't have
    yet. Returns "go", "field_goal", or "punt"."""
    in_fg_range = pos >= 62  # roughly a <=55-yard attempt
    short_yardage = distance <= 2

    go_chance = P.fourth_down_boost + 0.05 * (aggression - 0.5)
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
    for a drive with no prior offensive plays yet.
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
    kicker = None  # no dedicated K in OffensiveStarters yet -- see Known Gaps

    while total_plays < MAX_PLAYS_PER_DRIVE:
        total_plays += 1

        if down == 4:
            decision = _decide_fourth_down(pos, distance, trailing, aggression, rng)
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

        # Small pre-snap penalty chance, independent of play type (GDD Sec
        # 6.9's full type catalog / accept-decline logic isn't implemented
        # yet -- this is just a flat-rate yardage nudge for texture).
        if rng.prob(0.03):
            pre_down, pre_distance, pre_pos = down, distance, pos
            offense_penalty = rng.prob(0.5)
            if offense_penalty:
                pos = max(0, pos - 5)
                distance += 5
                desc = "Holding, offense: 5 yards"
            else:
                pos = min(99, pos + 5)
                distance = max(1, distance - 5)
                desc = "Defensive penalty: 5 yards"
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
        defcall = decide_defensive_call(ctx, down, distance, pos, trailing, is_two_minute, off_ypc, off_ypa, rng)

        pass_prob = _pass_probability(down, distance, trailing, is_two_minute, matchup_adj)
        is_pass = rng.prob(pass_prob)

        if is_pass:
            yards, outcome, who, receiver_name = _resolve_pass(rng, ctx, qb, defcall)
            play_type = "pass"
        else:
            yards, outcome, who = _resolve_run(rng, ctx, rb, defcall)
            play_type = "run"
            receiver_name = ""

        if outcome == "turnover":
            turnovers += 1
            spot = max(0, min(100, pos + yards))
            kind = f"Interception ({who})" if is_pass else f"Fumble lost ({who})"
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, kind, "turnover", defensive_call=defcall.description, receiver_name=receiver_name))
            return 0, kind, max(2, 100 - spot), total_plays, total_yards, turnovers, play_events

        total_yards += max(0, yards)
        raw_pos = pos + yards

        if raw_pos <= 0:
            # Safety: tackled (or sacked) behind their own goal line. Points
            # go to the *defense*, not this (offense's) drive -- the caller
            # (game_sim.py) special-cases the "Safety" summary text to award
            # them there, since this function only reports the offense's score.
            desc = f"{who} {'sacked' if outcome == 'sack' else 'tackled'} for a safety"
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, "safety", defensive_call=defcall.description, receiver_name=receiver_name))
            return 0, "Safety", 35, total_plays, total_yards, turnovers, play_events

        pos = min(100, raw_pos)

        if pos >= 100:
            made_pat = rng.prob(P.pat_make)
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
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, "first_down", defensive_call=defcall.description, receiver_name=receiver_name))
            down, distance = 1, 10
            continue

        # A loss (sack, tackle for loss) must increase distance-to-go, not
        # just fail to decrease it -- max(0, yards) was silently treating
        # every loss as a 0-yard play for down/distance purposes.
        play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, outcome, defensive_call=defcall.description, receiver_name=receiver_name))
        distance -= yards
        down += 1

        if down > 4:
            spot = max(2, 100 - pos)
            return 0, "Turnover on downs", spot, total_plays, total_yards, turnovers, play_events

    # Safety valve: ran out of play budget mid-drive (shouldn't happen in
    # practice) -- treat it as a punt from the current spot.
    next_pos = _punt_result(rng, pos)
    return 0, "Punt (drive length limit)", next_pos, total_plays, total_yards, turnovers, play_events
