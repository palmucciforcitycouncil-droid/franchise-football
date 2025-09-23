import os
import random
import hashlib
from typing import Optional, Union

# --- Public API -------------------------------------------------------------

def get_league_seed() -> int:
    """
    Single source of truth for the simulation seed.
    Primary: LEAGUE_SEED (env/config)
    Temporary legacy fallback: DEFAULT_SEED (env) for backward compatibility.
    """
    v = os.getenv("LEAGUE_SEED")
    if v and v.isdigit():
        return int(v)

    # Legacy fallback during transition window (do NOT reintroduce DEFAULT_SEED elsewhere)
    v = os.getenv("DEFAULT_SEED")
    if v and v.isdigit():
        return int(v)

    # Final guard: stable default to keep local/dev reproducible
    return 2025


def make_rng(
    season_year: int,
    week: Optional[int],
    game_id: Optional[Union[int, str]],
    subsystem: str,
) -> random.Random:
    """
    Deterministic RNG factory. Never call random.seed() directly elsewhere.

    Seed material = (LEAGUE_SEED, season_year, week, game_id, subsystem)
    hashed to a 64-bit integer via BLAKE2b for stability across platforms.
    """
    league_seed = get_league_seed()
    seed_int = _hash_to_u64(league_seed, season_year, week, game_id, subsystem)
    return random.Random(seed_int)


# --- Internals --------------------------------------------------------------

def _hash_to_u64(*parts: object) -> int:
    """
    Compact, deterministic 64-bit integer from arbitrary parts.
    """
    h = hashlib.blake2b(digest_size=8)
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"|")
    return int.from_bytes(h.digest(), "big", signed=False)
