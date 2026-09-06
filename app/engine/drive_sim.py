"""
Down-by-down drive simulation.

This replaces the earlier single-Gaussian-per-drive model (one dice roll
decided the whole drive) with an actual down/distance/field-position loop:
a real sequence of plays, each one a run/pass decision, a yardage result,
a first-down check, and (on 4th down) a go/kick/punt decision -- much
closer to how a football drive actually unfolds.

What this is NOT: the GDD's full player-level play-calling AI (Part 1
Sec 6.6) -- the 4-layer offensive model, zone-based blocking-advantage
scoring, receiver mismatch identification, pass-rush-vs-protection
pipelines, and so on. All of that is specified in terms of individual
player attributes (QB accuracy, WR route running, OL/DL matchups, RB
traits) that don't exist yet -- there is no Player model or roster data
in this project yet, only team-level ratings (offense, defense, special,
run_bias, aggression, pace). This implements the same *structure* (a
down-by-down loop with situational decisions) using only those team-level
inputs. Swapping in real player-level formulas later means replacing the
decision functions below (_pass_probability, _resolve_run, _resolve_pass,
_decide_fourth_down) -- the drive loop itself and the PlayEvent log shape
don't need to change.
"""
from __future__ import annotations
from typing import List, Tuple

from .rng import RNG
from .rating import TeamRatings
from .tuning import PARAMS, DRIVE_SIM_PARAMS as P
from .game_state import PlayEvent

MAX_PLAYS_PER_DRIVE = 20  # safety valve against pathological loops


def _pass_probability(down: int, distance: int, trailing: bool, is_two_minute: bool, run_bias: float) -> float:
    """Simplified stand-in for the GDD's 4-layer offensive play-calling
    model (Sec 6.6.1), using team-level run_bias instead of player/coach
    attributes. Layer 1 (situational baseline by down & distance), then
    Layer 2 (game-state adjustment for score/clock)."""
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

    base -= (run_bias - 0.5) * 0.30  # team identity nudge

    return max(0.1, min(0.92, base))


def _resolve_run(rng: RNG, offense: TeamRatings, defense: TeamRatings) -> Tuple[int, str]:
    rating_diff = offense.offense - defense.defense
    mean = 4.2 + rating_diff * 0.03
    yards = int(round(rng.gauss(mean, 4.5)))

    fumble_rate = max(0.002, PARAMS["turnover"]["fumble_per_rush"] - rating_diff * 0.00005)
    if rng.prob(fumble_rate):
        return max(yards, -2), "turnover"

    return yards, "gain"


def _resolve_pass(rng: RNG, offense: TeamRatings, defense: TeamRatings) -> Tuple[int, str]:
    rating_diff = offense.offense - defense.defense
    completion_pct = max(0.35, min(0.75, 0.62 + rating_diff * 0.003))

    if rng.prob(1 - completion_pct):
        # incompletion, or a sack if pressure "wins" (simplified: flat share of incompletions are sacks)
        if rng.prob(0.12):
            sack_yards = -int(abs(rng.gauss(6.5, 3)))
            return sack_yards, "sack"
        return 0, "incomplete"

    mean = 8.5 + rating_diff * 0.04
    yards = int(round(max(-3, rng.gauss(mean, 8))))

    int_rate = max(0.005, PARAMS["turnover"]["int_per_pass_att"] - rating_diff * 0.0001)
    if rng.prob(int_rate):
        return max(yards, 0), "turnover"

    return yards, "gain"


def _fg_distance_bucket(attempt_yards: int) -> str:
    if attempt_yards < 30:
        return "<30"
    if attempt_yards < 40:
        return "30-39"
    if attempt_yards < 50:
        return "40-49"
    return "50+"


def _attempt_field_goal(rng: RNG, pos: int) -> Tuple[bool, int]:
    attempt_yards = (100 - pos) + 17  # line of scrimmage to goal + snap/hold depth
    make_prob = PARAMS["special"]["fg_make_prob"][_fg_distance_bucket(attempt_yards)]
    return rng.prob(make_prob), attempt_yards


def _decide_fourth_down(pos: int, distance: int, trailing: bool, aggression: float, rng: RNG) -> str:
    """Simplified stand-in for the GDD's EP-based 4th-down model (Sec
    6.6.4), which needs P(convert)/P(make_FG) tables keyed to real kicker
    and offensive-line data that doesn't exist yet. Returns "go", "field_goal", or "punt"."""
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
    offense: TeamRatings,
    defense: TeamRatings,
    field_pos: int,
    *,
    is_two_minute: bool = False,
    trailing: bool = False,
    fourth_down_ok: bool = False,
) -> Tuple[int, str, int, int, int, int, List[PlayEvent]]:
    """
    Simulates one drive down-by-down. Returns:
        points, summary, next_field_pos, plays, yards, turnovers, play_events

    field_pos is 0..100: the offense's distance traveled toward the
    opponent's end zone (100 = touchdown). fourth_down_ok mirrors the
    caller's existing "is this team willing to be aggressive" signal from
    game_sim.py and is folded into the 4th-down decision's aggression term.
    """
    down = 1
    distance = 10
    pos = field_pos
    total_yards = 0
    total_plays = 0
    turnovers = 0
    play_events: List[PlayEvent] = []

    aggression = offense.aggression + (0.15 if fourth_down_ok else 0.0)

    while total_plays < MAX_PLAYS_PER_DRIVE:
        total_plays += 1

        if down == 4:
            decision = _decide_fourth_down(pos, distance, trailing, aggression, rng)
            if decision == "punt":
                next_pos = _punt_result(rng, pos)
                play_events.append(PlayEvent(down, distance, pos, "punt", 0, "Punt", "punt"))
                return 0, "Punt", next_pos, total_plays, total_yards, turnovers, play_events
            if decision == "field_goal":
                made, attempt_yards = _attempt_field_goal(rng, pos)
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

        pass_prob = _pass_probability(down, distance, trailing, is_two_minute, offense.run_bias)
        is_pass = rng.prob(pass_prob)

        if is_pass:
            yards, outcome = _resolve_pass(rng, offense, defense)
            play_type = "pass"
        else:
            yards, outcome = _resolve_run(rng, offense, defense)
            play_type = "run"

        if outcome == "turnover":
            turnovers += 1
            spot = max(0, min(100, pos + yards))
            kind = "Interception" if is_pass else "Fumble lost"
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, kind, "turnover"))
            return 0, kind, max(2, 100 - spot), total_plays, total_yards, turnovers, play_events

        total_yards += max(0, yards)
        raw_pos = pos + yards

        if raw_pos <= 0:
            # Safety: tackled (or sacked) behind their own goal line. Points
            # go to the *defense*, not this (offense's) drive -- the caller
            # (game_sim.py) special-cases the "Safety" summary text to award
            # them there, since this function only reports the offense's score.
            desc = f"{'Sacked' if outcome == 'sack' else ('Pass' if is_pass else 'Run')} for a safety"
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, "safety"))
            return 0, "Safety", 35, total_plays, total_yards, turnovers, play_events

        pos = min(100, raw_pos)

        if pos >= 100:
            made_pat = rng.prob(P.pat_make)
            pts = 7 if made_pat else 6
            desc = f"{'Pass' if is_pass else 'Run'} for {yards} yards, TOUCHDOWN"
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, "touchdown"))
            return pts, "TD", 25, total_plays, total_yards, turnovers, play_events

        gained_first_down = yards >= distance
        if outcome == "sack":
            desc = f"Sacked for a loss of {-yards} yards" if yards < 0 else "Sacked, no loss"
        elif outcome == "incomplete":
            desc = "Incomplete pass"
        else:
            desc = f"{'Pass' if is_pass else 'Run'} for {yards} yards"

        if gained_first_down:
            play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, "first_down"))
            down, distance = 1, 10
            continue

        # A loss (sack, tackle for loss) must increase distance-to-go, not
        # just fail to decrease it -- max(0, yards) was silently treating
        # every loss as a 0-yard play for down/distance purposes.
        play_events.append(PlayEvent(play_down, play_distance, play_start_pos, play_type, yards, desc, outcome))
        distance -= yards
        down += 1

        if down > 4:
            spot = max(2, 100 - pos)
            return 0, "Turnover on downs", spot, total_plays, total_yards, turnovers, play_events

    # Safety valve: ran out of play budget mid-drive (shouldn't happen in
    # practice) -- treat it as a punt from the current spot.
    next_pos = _punt_result(rng, pos)
    return 0, "Punt (drive length limit)", next_pos, total_plays, total_yards, turnovers, play_events
