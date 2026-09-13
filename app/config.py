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


# The real calendar year season_number 0 corresponds to -- MUST match
# scripts/import_nfl_history.py's own FIRST_SEASON (2002, "the modern
# 32-team NFL era"): that script archives real 2002-2025 NFL seasons as
# season_number = year - FIRST_SEASON, and a fresh franchise's own
# season_number picks up chronologically right after whatever's already
# archived (season_state.py's _bootstrap_season_number()). Brian's own
# ask (2026-09-12): every user-facing "Season N" label should show this
# real calendar year, not a bare 1-indexed sequence number ("Season 25")
# that has no obvious real-world meaning.
FIRST_SEASON = 2002


def season_year(season_number: int) -> int:
    return FIRST_SEASON + season_number
