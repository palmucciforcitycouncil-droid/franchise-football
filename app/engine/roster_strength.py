"""
Roster Strength -- A1 of docs/handoff_prestige_and_coach_impact.md.

There was no roster-to-team-strength aggregator anywhere in this codebase
before this module (app/engine/scouting.py is entirely in-season
play-derived and cannot produce a week-0 number; app/engine/rating.py's
`TeamRatings` is a dead placeholder never read by the sim -- see that
module's own history in ROADMAP.md). This is the real thing: a pure
function of real player attributes, the real depth chart, and the real
Coach table. It has three consumers, none built yet: the position-rank
sheet (A2), JSS's `PreseasonPowerRankDelta` (A2), and team prestige (A4).

Confirmed the roster-derived approach doesn't conflict with the sim
(handoff Sec 2.1): play outcomes already run off individual player
attributes via player_ai.py/depth_chart.py/rotation.py, not the dead
`TeamRatings.offense/defense/special` placeholder, so a roster-derived
rating reads the exact same source of truth the sim already reads.

**Design decisions settled 2026-09-11 (Brian):**

1. **Group aggregation is snap-share weighted**, reusing
   app/engine/rotation.py's real per-position decay curves wherever they
   already exist (RB/WR/TE, and the DL/LB/DB per-slot curves) rather than
   a flat top-N average. This is a deliberate, not incidental, choice:
   rotation.py's decay constants already encode each position's REAL
   playing-time share (a WR corps' snaps spread close to evenly,
   WR_DECAY=0.80; a safety duo is closest to iron-man, no decay constant
   at all because no backup rotation is modeled there) -- and playing-
   time share is exactly what a roster-strength weight should track. For
   the positions the live sim treats as pure iron-man (QB, every OL slot,
   K, P, and the two safety spots -- none of which the in-game rotation
   system ever substitutes), `IRON_MAN_DECAY`/`IRON_MAN_MAX_DEPTH` below
   are this module's own new constant, steeper than rotation.py's own
   steepest (DB_DECAY=0.12), since these positions are even more fixed
   than a cornerback duo.

2. **Starter/depth split settled at "heavy starters" (~80/20).** That is
   the roster-WIDE average outcome of decision 1's real per-position
   decay curves, not a single per-group knob -- some groups land far more
   starter-heavy than 80/20 (a safety duo: ~90/10, via `IRON_MAN_DECAY`)
   and some land less so (a WR corps: closer to 60/40, via `WR_DECAY`).
   That variance is realistic, not a bug -- it is the same variance the
   live sim's own rotation already encodes for exactly the same reason.

3. **Coach contribution is additive, not multiplicative** (`COACH_WEIGHT`
   below): the blend keeps `Coach.overall` as its own term, so a strong
   coach can genuinely lift a weak roster's rating rather than merely
   scaling a total that talent alone could never reach. `COACH_WEIGHT` is
   set below `QB`'s own share of `roster_score` but comparable to it --
   "heavy," per the settled decision, without letting one number
   outweigh the other ~40 real rostered players combined.

4. **Positional weights (`POSITION_WEIGHTS`) were tuned by A3, 2026-09-12**
   (`scripts/tune_roster_strength_weights.py`) -- not hand-guessed
   anymore, but still a first real pass, not a final calibration. Method
   (matches the handoff's own A3 instructions): 14 seeds correlating the
   fixed preseason `team_rating`/`roster_score` against real simulated
   seasons' final win_pct/power_rating (pooled n=448; team_rating vs
   win_pct r=+0.43, vs power_rating r=+0.49 -- a real, moderate, honest
   signal, not a fabricated near-1.0), plus 3-seed swap-sensitivity
   trials on 6 representative groups (QB/T/WR/DE/LB/K), each swapping a
   mid-pack baseline team's REAL roster at one group for the league's
   actual best team's real players at that group and measuring the
   shift in final power_rating (steadier than win_pct over one 18-game
   season). Findings: **T (offensive tackle) measured essentially tied
   with QB** at the top -- both far above the rest, consistent with
   `Player`'s own module docstring calling out a real, direct "LT & LG
   vs. opponent RDE & RDT" zone-blocking matchup formula, i.e. this
   isn't noise, it's the sim's actual matchup math. WR and DE measured
   statistically indistinguishable from each other. LB measured well
   below its old weight. K measured at/below zero (consistent with "low
   importance," not evidence to push it lower still off 3 noisy seeds).
   **G/C were bumped by inference, not direct measurement** -- they sit
   in the same blocking-matchup family as T (`Player`'s own docstring
   again: interior linemen share that formula) -- flagged separately
   from the directly-tested groups for exactly that reason.
   **RB/TE/DT/CB/S/P were not tested and are UNCHANGED placeholders.**
   A full A3 pass covering all 14 groups, and more seeds per group for
   tighter confidence, remains a real further-refinement opportunity --
   see `ROADMAP.md`'s A3 entry for the full run output and caveats.

**Not done here, deliberately:** persistence/storage (the handoff's own
open question -- "a week-0 entry [in power_rank_history.py] is the
obvious fit" -- has no consumer yet, so wiring it now would be a store
nothing reads) and the position-rank sheet UI (A2). Both are the next
increment once this function exists to feed them.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from sqlmodel import select

from app.core.db import get_session
from app.engine import rotation
from app.engine.position_groups import POSITION_TO_GROUP, QUOTA_GROUPS
from app.models.player import Player, Position
from app.services import coach_store, depth_chart_overrides

# Positions the live sim never rotates at all (no backup ever plays a
# snap in this engine) -- see module docstring decision 1. Steeper than
# rotation.py's own steepest real curve (DB_DECAY=0.12) since these are
# even more fixed than a cornerback duo.
IRON_MAN_DECAY = 0.10
IRON_MAN_MAX_DEPTH = 2

# Position -> (decay, max_depth) for snap-share weighting within that
# position's own depth chart. Reuses rotation.py's real curves wherever
# rotation.py already models that position; IRON_MAN_* everywhere the
# live sim has no backup rotation at all.
_DECAY_MAX_DEPTH: dict[Position, tuple[float, int]] = {
    Position.QB: (IRON_MAN_DECAY, IRON_MAN_MAX_DEPTH),
    Position.HB: (rotation.RB_DECAY, rotation.RB_MAX_DEPTH),
    Position.WR: (rotation.WR_DECAY, rotation.WR_MAX_DEPTH),
    Position.TE: (rotation.TE_DECAY, rotation.TE_MAX_DEPTH),
    Position.T: (IRON_MAN_DECAY, IRON_MAN_MAX_DEPTH),
    Position.G: (IRON_MAN_DECAY, IRON_MAN_MAX_DEPTH),
    Position.C: (IRON_MAN_DECAY, IRON_MAN_MAX_DEPTH),
    Position.EDGE: (rotation.DL_DECAY, rotation.DL_MAX_DEPTH),
    Position.DT: (rotation.DL_DECAY, rotation.DL_MAX_DEPTH),
    Position.LB: (rotation.LB_DECAY, rotation.LB_MAX_DEPTH),
    Position.CB: (rotation.DB_DECAY, rotation.DB_MAX_DEPTH),
    Position.S: (IRON_MAN_DECAY, IRON_MAN_MAX_DEPTH),
    Position.K: (IRON_MAN_DECAY, IRON_MAN_MAX_DEPTH),
    Position.P: (IRON_MAN_DECAY, IRON_MAN_MAX_DEPTH),
}

# A3-tuned (2026-09-12) -- see module docstring decision 4 for the full
# method and results. QB/T/WR/DE/LB/K were directly measured; G/C were
# bumped by inference from T's result (same blocking-matchup family);
# RB/TE/DT/CB/S/P are untested first-pass placeholders, unchanged.
POSITION_WEIGHTS: dict[str, float] = {
    "QB": 3.00,   # measured: tied for highest
    "RB": 1.00,   # untested placeholder
    "WR": 1.50,   # measured: matches its old weight well
    "TE": 0.75,   # untested placeholder
    "C": 0.75,    # inferred from T (was 0.50) -- interior OL, same blocking-matchup family
    "G": 1.25,    # inferred from T (was 0.75) -- same formula pairs G with T directly
    "T": 3.00,    # measured: essentially tied with QB (was 1.00) -- the single biggest correction
    "EDGE": 1.50,   # measured: statistically indistinguishable from WR (was 1.25)
    "DT": 1.00,   # untested placeholder
    "LB": 0.75,   # measured: well below its old weight (was 1.25)
    "CB": 1.25,   # untested placeholder
    "S": 1.00,    # untested placeholder
    "K": 0.25,    # measured: at/below zero -- consistent with a low weight, unchanged
    "P": 0.25,    # untested placeholder, paired with K
}
assert set(POSITION_WEIGHTS) == set(QUOTA_GROUPS)
assert POSITION_WEIGHTS["QB"] > POSITION_WEIGHTS["K"] + POSITION_WEIGHTS["P"]

# See module docstring decision 3. A share of the FINAL blended number,
# not of roster_score's own internal weight pool -- at 0.15 the coach's
# share of team_rating (15%) lands close to QB's own effective share
# ((3.00 / sum(POSITION_WEIGHTS)) * (1 - 0.15) ~= 17%), i.e. "heavy":
# on the order of the single most important position weight, not a
# token nudge and not a dominant override of ~40 real rostered players.
COACH_WEIGHT = 0.15

_POSITIONS_BY_GROUP: dict[str, list[Position]] = {
    group: [p for p, g in POSITION_TO_GROUP.items() if g == group]
    for group in QUOTA_GROUPS
}


@dataclass(frozen=True)
class RosterStrength:
    team_abbr: str
    # One 0-99ish rating per QUOTA_GROUPS entry present on this roster.
    # A group is absent only if the roster has zero players at every one
    # of that group's constituent positions (a data anomaly, not a
    # normal empty-depth case).
    group_ratings: dict[str, float] = field(default_factory=dict)
    roster_score: float = 0.0       # weighted composite of group_ratings alone
    coach_overall: int | None = None  # None = no head coach on record for this team
    team_rating: float = 0.0        # roster_score blended with coach_overall


def _load_roster(team_abbr: str) -> list[Player]:
    with get_session() as session:
        return list(session.exec(select(Player).where(Player.team_abbr == team_abbr)))


def _slot_rating(team_abbr: str, position: Position, players_at_position: list[Player]) -> float | None:
    """Snap-share-weighted average overall_rating within one real depth
    chart (one Position value), respecting any saved user override the
    same way depth_chart.py's own starter selection does."""
    if not players_at_position:
        return None
    decay, max_depth = _DECAY_MAX_DEPTH[position]
    ordered = depth_chart_overrides.resolve_order(team_abbr, position.value, players_at_position)
    shares = rotation.snap_shares(ordered, decay, max_depth)
    if not shares:
        return None
    return sum(p.overall_rating * share for p, share in shares)


def compute_group_ratings(team_abbr: str, roster: list[Player] | None = None) -> dict[str, float]:
    """One rating per QUOTA_GROUPS entry. A multi-position group (e.g.
    "G" = LG+RG, "LB" = LOLB+MLB+ROLB) is the plain average of its
    constituent positions' own slot ratings -- each real starting slot
    counted equally, a first-pass choice like the weights above."""
    if roster is None:
        roster = _load_roster(team_abbr)
    ratings: dict[str, float] = {}
    for group, positions in _POSITIONS_BY_GROUP.items():
        slot_ratings = []
        for position in positions:
            players_at_position = [p for p in roster if p.position == position]
            r = _slot_rating(team_abbr, position, players_at_position)
            if r is not None:
                slot_ratings.append(r)
        if slot_ratings:
            ratings[group] = sum(slot_ratings) / len(slot_ratings)
    return ratings


def compute_roster_score(group_ratings: dict[str, float]) -> float:
    """Weighted average of group_ratings, renormalized over whichever
    groups are actually present -- same 0-99ish scale as a group rating
    or a player's overall_rating."""
    total_weight = sum(POSITION_WEIGHTS[g] for g in group_ratings)
    if total_weight == 0:
        return 0.0
    return sum(POSITION_WEIGHTS[g] * r for g, r in group_ratings.items()) / total_weight


def compute_roster_strength(team_abbr: str) -> RosterStrength:
    """The one real entry point: everything needed for one team's row on
    the future position-rank sheet, and the future input to prestige."""
    roster = _load_roster(team_abbr)
    group_ratings = compute_group_ratings(team_abbr, roster)
    r_score = compute_roster_score(group_ratings)

    head_coach = coach_store.head_coach(team_abbr)
    coach_overall = head_coach.overall if head_coach is not None else None
    # No coach on record degrades to "no coach bias," the same contract
    # app/engine/coaching.py's StaffEffect already keeps for a missing
    # staff -- never fabricate a league-average stand-in.
    team_rating = r_score if coach_overall is None else (
        (1 - COACH_WEIGHT) * r_score + COACH_WEIGHT * coach_overall
    )

    return RosterStrength(
        team_abbr=team_abbr,
        group_ratings=group_ratings,
        roster_score=r_score,
        coach_overall=coach_overall,
        team_rating=team_rating,
    )


def compute_all(team_abbrs: list[str]) -> dict[str, RosterStrength]:
    return {abbr: compute_roster_strength(abbr) for abbr in team_abbrs}
