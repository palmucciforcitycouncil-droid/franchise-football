"""
Deterministic RNG Helper for Franchise Football Engine

Implements GDD v3.2 determinism requirements using Blake2b hashing
to create stable 64-bit seeds from league configuration.

CRITICAL: This is the ONLY place where random seeds should be set.
All other modules MUST use make_rng() - never call random.seed() directly.
"""

import random
import hashlib
from typing import Optional


def make_rng(
    league_seed: int,
    season: int,
    week: Optional[int] = None,
    game_id: Optional[int] = None,
    subsystem: str = "default"
) -> random.Random:
    """
    Create a deterministic Random instance using Blake2b hashing.
    
    This function implements GDD v3.2 determinism requirements:
    - Same inputs always produce identical random sequences
    - Different subsystems produce different random streams
    - Stable across Python versions and platforms
    
    Args:
        league_seed: Master seed for the entire league (e.g., 2025)
        season: Season year (e.g., 2025)
        week: Week number (None for season-level operations)
        game_id: Specific game identifier (None for week-level operations)
        subsystem: Subsystem identifier (e.g., "engine_boot", "play_sim", "injury")
    
    Returns:
        random.Random: Deterministic random number generator
        
    Raises:
        ValueError: If league_seed is not a positive integer
    """
    if not isinstance(league_seed, int) or league_seed <= 0:
        raise ValueError("league_seed must be a positive integer")
    
    if not isinstance(season, int) or season <= 0:
        raise ValueError("season must be a positive integer")
    
    if not isinstance(subsystem, str) or not subsystem.strip():
        raise ValueError("subsystem must be a non-empty string")
    
    # Normalize optional parameters
    week_val = week if week is not None else 0
    game_id_val = game_id if game_id is not None else 0
    
    # Create deterministic seed using Blake2b
    # Blake2b provides cryptographic-quality hashing with 64-bit output
    seed_data = f"{league_seed}:{season}:{week_val}:{game_id_val}:{subsystem}"
    seed_bytes = hashlib.blake2b(seed_data.encode('utf-8'), digest_size=8).digest()
    
    # Convert to 64-bit integer
    seed_int = int.from_bytes(seed_bytes, byteorder='big')
    
    # Create and return deterministic Random instance
    rng = random.Random()
    rng.seed(seed_int)
    
    return rng


def get_seed_info(
    league_seed: int,
    season: int,
    week: Optional[int] = None,
    game_id: Optional[int] = None,
    subsystem: str = "default"
) -> dict:
    """
    Get debugging information about a seed configuration.
    
    Args:
        league_seed: Master seed for the entire league
        season: Season year
        week: Week number (None for season-level operations)
        game_id: Specific game identifier (None for week-level operations)
        subsystem: Subsystem identifier
    
    Returns:
        dict: Seed information including the computed seed value
    """
    week_val = week if week is not None else 0
    game_id_val = game_id if game_id is not None else 0
    
    seed_data = f"{league_seed}:{season}:{week_val}:{game_id_val}:{subsystem}"
    seed_bytes = hashlib.blake2b(seed_data.encode('utf-8'), digest_size=8).digest()
    seed_int = int.from_bytes(seed_bytes, byteorder='big')
    
    return {
        "league_seed": league_seed,
        "season": season,
        "week": week,
        "game_id": game_id,
        "subsystem": subsystem,
        "seed_data": seed_data,
        "seed_int": seed_int,
        "seed_hex": hex(seed_int)
    }


# Lint guard: CRITICAL - This is the ONLY place where random.seed() should be called
# All other modules MUST use make_rng() function above
# 
# If you see random.seed() anywhere else in the codebase, it's a violation
# of GDD v3.2 determinism requirements and should be removed immediately.
