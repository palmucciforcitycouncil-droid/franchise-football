"""
Deterministic placeholder team ratings, derived from LEAGUE_SEED + team abbr.

There is no real roster/player data yet (Player model and roster generation
are future work -- see GDD Part 1 Sec 3), so real "Overall" team ratings
(Sec 7.1) can't be computed from actual rosters. This gives every team a
stable, distinct rating derived only from the seed, so the vertical slice
has 32 teams that actually play differently from each other, without
pretending any of it is real scouting data.
"""
from __future__ import annotations
import random

from app.engine.rating import TeamRatings
from app.data.teams import TEAMS, TeamInfo


def ratings_for(team: TeamInfo, league_seed: int) -> TeamRatings:
    rng = random.Random(f"{league_seed}:{team.abbr}")
    return TeamRatings(
        offense=rng.uniform(55, 90),
        defense=rng.uniform(55, 90),
        special=rng.uniform(55, 90),
        run_bias=rng.uniform(0.35, 0.65),
        aggression=rng.uniform(0.3, 0.75),
        pace=rng.uniform(0.3, 0.75),
    )


def all_ratings(league_seed: int) -> dict[str, TeamRatings]:
    return {t.abbr: ratings_for(t, league_seed) for t in TEAMS}
