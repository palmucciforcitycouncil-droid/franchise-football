"""
Determinism policy (GDD Part 1 Sec 1.3): LEAGUE_SEED is required. There is
no DEFAULT_SEED fallback -- fail loudly at startup if it's unset, rather
than silently running with a different seed than the caller expects.
"""
import os


def get_league_seed() -> int:
    raw = os.environ.get("LEAGUE_SEED")
    if raw is None:
        raise RuntimeError(
            "LEAGUE_SEED is not set. Set it in the environment or a .env file "
            "before starting the app -- there is no fallback seed."
        )
    return int(raw)
