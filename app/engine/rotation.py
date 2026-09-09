"""
Real roster-depth rotation / snap-share modeling (GDD Part 1 Sec 6.6 area
-- not spec'd in the GDD at all, a real gap this fills; see HANDOFF.md
item 37).

The problem this fixes: every position group used to funnel through a
single fixed "starter" -- literally every offensive/defensive snap of an
entire season went to the same 11 players per team, with zero
substitution, committee backfield, receiver-corps depth, or defensive
rotation. Comparing a full simulated season against this project's own
imported real NFL data (data/saves/history.json, via
scripts/import_nfl_history.py) showed the resulting gap wasn't just
"leaders are a bit high" -- real NFL credits solo tackles to ~1384
distinct defenders in a season; this engine credited only 352 (11 per
team, the fixed starting lineup). Real NFL has ~250 wide receivers with
20+ targets in a season; this engine had 128 (4 per team -- the only
slots choose_pass_target considered). The MEDIAN defender's tackle count
was ~9.6x real.

Design: a per-player "share" of a position group's touches/snaps, built
from two real, disclosed factors:
  1. Depth-chart rank -- a position-specific geometric decay (share(rank)
     proportional to DECAY^rank), hand-calibrated against real NFL usage
     patterns (a workhorse RB's ~60% carry share, a #1 WR's ~28-30%
     target share, heavy DL rotation vs. light secondary rotation). Not
     GDD-specified (nothing here is) -- a disclosed heuristic, same
     category as drive_sim.py's _run_tackler/_sack_defender.
  2. The player's own stamina/durability -- Brian's explicit request
     ("tied into individual player attributes, like injury and any stat
     we have for stamina"). durability is Madden's "Injury" rating
     (higher = tougher, less likely hurt -- see app/models/player.py's
     module docstring); stamina is in-game endurance. Both nudge a
     player's share of the workload up or down from the pure rank-based
     baseline: a below-average-conditioned "starter" cedes some real
     share to the depth chart behind him, an elite-conditioned one holds
     a bit more. This is a WORKLOAD-DISTRIBUTION proxy, not a live
     injury system -- no in-season injury EVENT exists in this engine at
     all (Post-MVP, see HANDOFF's Known Gaps), so this shapes
     season-long share, not a specific missed-game absence.

Age and overall_rating were considered and deliberately left out of this
factor: age's real-world effect (the "RB workload cliff") is already
substantially reflected in durability for an older player in this
Madden-derived data, and overall_rating differences between depth-chart
slots are already what determines the STARTER/backup ORDER itself (via
depth_chart.py's rating-sorted default) -- folding it in again here
would double-count the same signal rather than add a new one.
"""
from __future__ import annotations

from app.models.player import Player

# Per-rank decay for raw (pre-reliability) share within a position group,
# hand-calibrated against real usage patterns -- see module docstring.
RB_DECAY = 0.46      # workhorse back ~60% carry share among a 3-deep RB room
WR_DECAY = 0.80      # WR looks spread fairly evenly across a 5-deep corps
TE_DECAY = 0.33      # TE1 clearly dominant over TE2
DL_DECAY = 0.60      # heavy rotation -- a real starter still leads, but a lot less
LB_DECAY = 0.28      # moderate rotation
DB_DECAY = 0.12      # least rotation -- corners/safeties are the closest to "iron man"

RB_MAX_DEPTH = 3
WR_MAX_DEPTH = 5
TE_MAX_DEPTH = 2
DL_MAX_DEPTH = 3   # starter + up to 2 real backups at one specific slot (e.g. LE1/LE2/LE3)
LB_MAX_DEPTH = 3
DB_MAX_DEPTH = 3


def reliability_factor(p: Player) -> float:
    """durability + stamina, averaged and centered on Madden's typical
    ~70 baseline, clamped to a modest +/-25-35% swing so this nudges
    share rather than dominating the depth-chart-rank signal."""
    avg = (p.durability + p.stamina) / 2
    return max(0.65, min(1.25, 1.0 + (avg - 70) * 0.008))


def snap_shares(depth_chart: list[Player], decay: float, max_depth: int) -> list[tuple[Player, float]]:
    """(player, share) pairs summing to 1.0 for a depth-chart-ordered
    list (rank 0 = starter) at one rotation group. Truncates to
    `max_depth` -- real usage falls off enough beyond that, that a 4th-
    or 5th-string player's snap share rounds to functionally zero."""
    pool = depth_chart[:max_depth]
    if not pool:
        return []
    raw = [decay ** i * reliability_factor(p) for i, p in enumerate(pool)]
    total = sum(raw)
    return [(p, w / total) for p, w in zip(pool, raw)]


def choose_by_snap_share(depth_chart: list[Player], decay: float, max_depth: int, rng) -> Player:
    """Weighted-random pick across a depth-ordered pool -- the offensive-
    skill-position equivalent of player_ai.py's choose_pass_target /
    choose_run_point_of_attack and defensive_ai.py's decide_blitz: a
    fresh draw every time this is called (once per relevant play), not a
    persistent per-game/per-drive substitution schedule, so the season-
    long distribution converges to the real target share by the law of
    large numbers without needing explicit rest/substitution tracking."""
    shares = snap_shares(depth_chart, decay, max_depth)
    if not shares:
        raise ValueError("empty depth chart passed to choose_by_snap_share")
    players, weights = zip(*shares)
    return rng.weighted_choice(list(players), list(weights))


def choose_slot_player(starter: Player, backups: list[Player], decay: float, max_depth: int, rng) -> Player:
    """The defensive equivalent for a single starter/backup(s) slot (e.g.
    LE1/LE2/LE3) -- DefensiveStarters.backups carries the real backups
    for each rotation-eligible slot (see depth_chart.py)."""
    pool = [starter] + backups
    return choose_by_snap_share(pool, decay, max_depth, rng)
