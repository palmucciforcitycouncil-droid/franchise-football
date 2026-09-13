"""
Injury generation and Return-to-Play (RTP) lifecycle -- GDD Part 1 Sec
3.8 / Sec 6.10, R1 of ROADMAP.md's R-series.

**Read app/models/injury.py's module docstring first** -- it has the
full accounting of where this deviates from Sec 6.10.1's letter (a live
per-play check inside drive_sim.py) and why: injuries are rolled once
per game, per player, from that player's REAL accumulated exposure in
the game's own already-built box score (carries, targets, pass attempts,
tackles, sacks, kicks), not a live hook threaded through
drive_sim.py's 10+ tuned, `test_stat_realism.py`-calibrated play-
resolution branches.

**Multipliers Sec 6.10.1 lists that this engine skips, disclosed, not
silently dropped:** fatigue (`app/engine/ratings.py`'s own fatigue
concept is dead code -- nothing in app/ imports that module, so there is
no real fatigue system to read from), tempo (Sec 6.5.9 isn't built),
weather (Sec 6.9 / ROADMAP.md's R7 isn't built). Only proneness (real,
derived from every Player's `durability` -- there is no separate
`injury_proneness` field on the model despite the GDD's field list
naming one; `durability` is Madden's real "Injury" rating and
`app/models/player.py`'s own module docstring already establishes
`proneness = 99 - durability` as the real inversion, same formula
`main.py`'s `_roster_injury_risk()` uses) and exposure volume/type (real,
from the real box score) drive risk here.

**Exposure rates (`EXPOSURE_RATES`) are this module's own calibrated
choice** -- there is no real official per-play-type injury-rate dataset
to import, the same disclosed-heuristic category as
`app/engine/rotation.py`'s own DECAY constants. Tuned so a full 18-week
simulated season lands in the real NFL's rough ballpark of ~350-500
players missing time leaguewide -- see `tests/test_injuries.py`'s own
season-level sanity check for the actual verified range.

Weekly lifecycle (Sec 6.10.4/6.10.5), hooked into
`season_state.simulate_current_week()`:
1. `apply_weekly_decay()` runs BEFORE that week's games simulate --
   decrements every active injury's `weeks_out`, transitions a player
   into RTP taper the week `weeks_out` first hits 0, tapers
   `rtp_penalty` by `RTP_TAPER_PER_WEEK` each week after that, and
   auto-closes the injury (`is_active=False`) once both hit 0. This
   ordering means a player whose `weeks_out` reaches 0 this week is
   correctly available for THIS week's games, not next week's.
2. Games simulate. `app/services/depth_chart.py` reads
   `injury_store.currently_out_player_ids()`/`rtp_penalties()` while
   building rosters/starters -- an OUT player is excluded from
   selection entirely (Sec 6.10.5's "promote the next slot" falls out
   of the existing rating-sorted depth-chart fallback for free once the
   injured player leaves the candidate pool), an RTP-taper player plays
   but with temporarily scaled attributes (`apply_rtp_penalty()`).
3. `roll_injuries_for_week()` runs AFTER that week's games, generating
   any new injuries from what just happened.
"""
from __future__ import annotations
import copy
from collections import defaultdict

from app.engine import coaching
from app.engine.box_score import build_box_score
from app.engine.defensive_box_score import build_defensive_box_score
from app.engine.position_groups import POSITION_TO_GROUP
from app.engine.rng import RNG, stable_seed
from app.engine.schedule import N_WEEKS
from app.models.injury import INITIAL_RTP_PENALTY, RTP_TAPER_PER_WEEK, Injury, InjurySeverity, InjuryType
from app.models.player import Player

# This module's own calibrated per-exposure-event base injury rate --
# see module docstring. "ol_snap" applies once per real offensive play
# the team ran (no direct per-lineman block-count stat exists) to each
# of the 5 real starting OL, since GDD Sec 6.10.6 explicitly calls out
# OL injury risk without this engine tracking individual blocks.
EXPOSURE_RATES: dict[str, float] = {
    "carry": 0.0031,
    "pass_attempt": 0.0012,
    "target": 0.0027,
    "sack": 0.0270,
    "tackle_involvement": 0.0014,
    "ol_snap": 0.0009,
    "kick": 0.0005,
}

# Sec 6.10.1: "+0% to +50% risk" from injury_proneness (0-100).
PRONENESS_MAX_MULT = 1.5

# Sec 6.10.2's severity split, used as written (context-independent --
# the GDD's own "tuned by type and context" is left as a documented
# future refinement, same as roster_strength.py's own first-pass weights).
_SEVERITIES = (InjurySeverity.MINOR, InjurySeverity.MODERATE, InjurySeverity.MAJOR)
_SEVERITY_WEIGHTS = (0.65, 0.25, 0.10)

# Sec 6.10.2's type-by-position table, collapsed to this module's 8-type
# enum (see injury.py's module docstring for the collapse). Grouped by
# QUOTA_GROUPS (app/engine/position_groups.py), the project's one real
# position-group taxonomy, not a second one invented here.
_QB_TYPES = {InjuryType.SHOULDER: 0.30, InjuryType.HAND: 0.20, InjuryType.CONCUSSION: 0.20,
             InjuryType.BACK: 0.15, InjuryType.OTHER: 0.15}
_SKILL_TYPES = {InjuryType.HAMSTRING: 0.30, InjuryType.ANKLE: 0.25, InjuryType.KNEE: 0.25,
                InjuryType.SHOULDER: 0.10, InjuryType.OTHER: 0.10}
_OL_TYPES = {InjuryType.KNEE: 0.35, InjuryType.SHOULDER: 0.25, InjuryType.BACK: 0.25,
             InjuryType.ANKLE: 0.10, InjuryType.OTHER: 0.05}
_DL_TYPES = {InjuryType.KNEE: 0.30, InjuryType.SHOULDER: 0.25, InjuryType.BACK: 0.20,
             InjuryType.ANKLE: 0.15, InjuryType.OTHER: 0.10}
_LB_TYPES = {InjuryType.KNEE: 0.30, InjuryType.SHOULDER: 0.25, InjuryType.HAMSTRING: 0.20,
             InjuryType.ANKLE: 0.15, InjuryType.CONCUSSION: 0.10}
_DB_TYPES = {InjuryType.HAMSTRING: 0.30, InjuryType.ANKLE: 0.30, InjuryType.KNEE: 0.20,
             InjuryType.CONCUSSION: 0.15, InjuryType.SHOULDER: 0.05}
_ST_TYPES = {InjuryType.BACK: 0.35, InjuryType.OTHER: 0.35, InjuryType.KNEE: 0.20, InjuryType.HAMSTRING: 0.10}

TYPE_WEIGHTS_BY_GROUP: dict[str, dict[InjuryType, float]] = {
    "QB": _QB_TYPES, "RB": _SKILL_TYPES, "WR": _SKILL_TYPES, "TE": _SKILL_TYPES,
    "C": _OL_TYPES, "G": _OL_TYPES, "T": _OL_TYPES,
    "DE": _DL_TYPES, "DT": _DL_TYPES, "LB": _LB_TYPES,
    "CB": _DB_TYPES, "S": _DB_TYPES, "K": _ST_TYPES, "P": _ST_TYPES,
}

# Sec 6.10.6's position-specific effects, generalized to a broad uniform
# scale over every real performance attribute rather than the GDD's
# fuller per-position table -- rtp_penalty is small (0.05-0.15) and
# short-lived (decays over 1-3 weeks), so the marginal realism of a full
# position-effect table is small relative to its added complexity; this
# module's own documented simplification. overall_rating is included so
# a weakened player can genuinely lose their starting slot to a healthy
# backup via depth_chart.py's existing rating-sorted fallback.
RTP_SCALED_ATTRS = (
    "overall_rating", "speed", "acceleration", "strength", "agility", "jumping", "stamina",
    "throw_power", "throw_accuracy_short", "throw_accuracy_mid", "throw_accuracy_deep",
    "catching", "carrying", "tackle", "hit_power", "run_block", "pass_block",
    "man_coverage", "zone_coverage", "block_shedding", "pursuit",
    "kick_power", "kick_accuracy",
)


def apply_rtp_penalty(player: Player, rtp_penalty: float) -> Player:
    """Sec 6.10.4: effective_attribute = base * (1 - rtp_penalty). Returns
    a scaled COPY -- never mutates the real stored rating, which is what
    the player recovers back to once rtp_penalty decays to 0."""
    if rtp_penalty <= 0.0:
        return player
    scaled = copy.copy(player)
    factor = 1.0 - rtp_penalty
    for attr in RTP_SCALED_ATTRS:
        setattr(scaled, attr, round(getattr(scaled, attr) * factor))
    return scaled


def _proneness_multiplier(player: Player) -> float:
    """Player has no separate `injury_proneness` field -- `durability`
    (Madden's "Injury" rating, higher = tougher) is the real attribute,
    inverted here the exact way player.py's own module docstring and
    main.py's _roster_injury_risk() both already establish:
    proneness = 99 - durability."""
    proneness = 99 - player.durability
    return 1.0 + (proneness / 100.0) * (PRONENESS_MAX_MULT - 1.0)


def _team_injury_risk_multiplier(team_abbr: str) -> float:
    """R13 Sec 5.2: this team's Training-focused staff (via
    motivation_chemistry) raises or lowers every one of its players'
    injury probability this week -- 1.0 for a league-average Training
    investment (or no coaches at all), same neutral-degradation guarantee
    every other coaching hook in this engine already has."""
    return coaching.injury_risk_multiplier(coaching.staff_effect_for(team_abbr))


def _no_injury_probability(exposure: dict[str, int], proneness_mult: float) -> float:
    p_survive = 1.0
    for kind, count in exposure.items():
        if count <= 0:
            continue
        rate = min(EXPOSURE_RATES[kind] * proneness_mult, 0.95)
        p_survive *= (1.0 - rate) ** count
    return p_survive


def _compute_game_exposures(plays, abbr: str) -> dict[str, dict[str, int]]:
    """{player_full_name: {exposure_kind: count}} for one team in one
    game, built entirely from that game's already-real box score --
    see module docstring for why this replaces a live per-play hook."""
    from app.services.depth_chart import get_offensive_starters

    box = build_box_score(plays, abbr)
    defense = build_defensive_box_score(plays, abbr)
    exposures: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for p in box.passing:
        exposures[p.name]["pass_attempt"] += p.attempts
        exposures[p.name]["sack"] += p.sacks
    for r in box.rushing:
        exposures[r.name]["carry"] += r.carries
    for rc in box.receiving:
        exposures[rc.name]["target"] += rc.targets
    for k in box.kicking:
        exposures[k.name]["kick"] += k.fg_attempted + k.xp_attempted
    for pu in box.punting:
        exposures[pu.name]["kick"] += pu.punts
    for d in defense:
        exposures[d.name]["tackle_involvement"] += (
            d.solo_tackles + d.tackles_for_loss + d.sacks
            + d.interceptions + d.passes_defended + d.forced_fumbles
        )

    total_off_plays = sum(p.attempts for p in box.passing) + sum(r.carries for r in box.rushing)
    if total_off_plays:
        starters = get_offensive_starters(abbr)
        for lineman in starters.offensive_line:
            exposures[lineman.full_name]["ol_snap"] += total_off_plays

    return exposures


def _duration_weeks(rng: RNG, severity: InjurySeverity, week_num: int) -> int:
    if severity is InjurySeverity.MINOR:
        weeks = rng.r().randint(0, 2)
    elif severity is InjurySeverity.MODERATE:
        weeks = rng.r().randint(2, 5)
    else:
        weeks = rng.r().randint(6, 16)
    # Sec 6.10.2: "cap at season end for MVP" -- no mid-season IR recall
    # (Sec 6.10.5) or offseason carryover modeled yet.
    return min(weeks, max(0, N_WEEKS - week_num))


def _generate_injury(rng: RNG, player: Player, team_abbr: str, season_number: int, week_num: int) -> Injury:
    group = POSITION_TO_GROUP[player.position]
    type_weights = TYPE_WEIGHTS_BY_GROUP[group]
    injury_type = rng.weighted_choice(list(type_weights.keys()), list(type_weights.values()))
    severity = rng.weighted_choice(list(_SEVERITIES), list(_SEVERITY_WEIGHTS))
    weeks_out = _duration_weeks(rng, severity, week_num)

    return Injury(
        injury_id=f"{player.player_id}_{season_number}_{week_num}",
        player_id=player.player_id,
        team_abbr=team_abbr,
        season_number=season_number,
        week_injured=week_num,
        injury_type=injury_type,
        severity=severity,
        weeks_out=weeks_out,
        rtp_penalty=0.0,
        placed_on_ir=weeks_out >= 4,
        is_active=True,
    )


def roll_injuries_for_week(season, week_num: int) -> list[Injury]:
    """Called once, after `week_num`'s games have all simulated. Skips
    any player who already has an active injury (Sec 3.8.2: one active
    injury per player at a time)."""
    from app.services import injury_store

    already_hurt = set(injury_store.currently_out_player_ids()) | {
        i.player_id for i in injury_store.active_injuries()
    }

    with_session_players: dict[tuple[str, str], Player] = {}
    from app.core.db import get_session
    from sqlmodel import select
    week_games = season.schedule[week_num - 1]
    team_abbrs = {abbr for g in week_games if g.result is not None for abbr in (g.home_abbr, g.away_abbr)}
    if team_abbrs:
        with get_session() as s:
            for p in s.exec(select(Player).where(Player.team_abbr.in_(team_abbrs))):
                with_session_players[(p.team_abbr, p.full_name)] = p

    new_injuries: list[Injury] = []
    for game in week_games:
        if game.result is None:
            continue
        for abbr in (game.home_abbr, game.away_abbr):
            exposures = _compute_game_exposures(game.result.plays, abbr)
            team_injury_risk = _team_injury_risk_multiplier(abbr)
            for name, events in exposures.items():
                player = with_session_players.get((abbr, name))
                if player is None or player.player_id in already_hurt:
                    continue
                seed = stable_seed("injury", season.league_seed, season.season_number, week_num, player.player_id)
                rng = RNG.with_seed(seed)
                proneness_mult = _proneness_multiplier(player) * team_injury_risk
                p_no_injury = _no_injury_probability(events, proneness_mult)
                if rng.prob(1.0 - p_no_injury):
                    injury = _generate_injury(rng, player, abbr, season.season_number, week_num)
                    new_injuries.append(injury)
                    already_hurt.add(player.player_id)

    from app.services import injury_store as store
    store.save_injuries(new_injuries)
    return new_injuries


def apply_weekly_decay(season_number: int, week_num: int) -> None:
    """Sec 6.10.4's weekly loop, run BEFORE `week_num`'s games simulate
    so a player whose weeks_out reaches 0 this week is available for
    this week's games, not next week's."""
    from app.services import injury_store

    active = list(injury_store.active_injuries())
    if not active:
        return
    for injury in active:
        if injury.weeks_out > 0:
            injury.weeks_out -= 1
            if injury.weeks_out == 0:
                injury.rtp_penalty = INITIAL_RTP_PENALTY[injury.severity]
        else:
            injury.rtp_penalty = max(0.0, injury.rtp_penalty - RTP_TAPER_PER_WEEK)
            if injury.rtp_penalty <= 0.0:
                injury.is_active = False
    injury_store.save_injuries(active)
