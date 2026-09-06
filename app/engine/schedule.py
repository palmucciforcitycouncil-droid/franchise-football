"""
Simplified schedule generator.

This is NOT the GDD's full opponent-selection formula (Part 1 Sec 5.1:
6 divisional + 4 intra-conference rotation + 4 inter-conference rotation
+ 2 standings-based + 1 seventeenth game, with bye weeks 5-14 except 6).
That formula needs multi-year rotation tables and prior-season standings
that don't exist yet. This is a placeholder that hits the right *shape*
(every team plays 17 distinct opponents, no repeats, no self-play) using
a plain round-robin, so a season can actually be played and simulated
end-to-end. Swap this out for the real formula without touching anything
downstream -- callers only depend on `generate_season_schedule`'s output
shape (a list of weeks, each a list of (home_abbr, away_abbr) tuples).
"""
from __future__ import annotations
import hashlib

from app.data.teams import TEAMS

N_WEEKS = 17  # simplified: no bye weeks yet, one game per team per week


def _circle_method_rounds(n_teams: int) -> list[list[tuple[int, int]]]:
    """Standard round-robin circle method. n_teams must be even."""
    assert n_teams % 2 == 0
    idx = list(range(n_teams))
    rounds = []
    for _ in range(n_teams - 1):
        pairings = [(idx[i], idx[n_teams - 1 - i]) for i in range(n_teams // 2)]
        rounds.append(pairings)
        idx = [idx[0]] + [idx[-1]] + idx[1:-1]
    return rounds


def generate_season_schedule(league_seed: int) -> list[list[tuple[str, str]]]:
    """
    Returns a list of N_WEEKS weeks; each week is a list of
    (home_abbr, away_abbr) tuples covering all 32 teams (16 games/week).
    Deterministic in league_seed (only affects home/away assignment --
    the round-robin pairing order itself is fixed by team list order).
    """
    abbrs = [t.abbr for t in TEAMS]
    n = len(abbrs)
    rounds = _circle_method_rounds(n)[:N_WEEKS]

    weeks: list[list[tuple[str, str]]] = []
    for week_num, pairings in enumerate(rounds, start=1):
        week_games = []
        for a_idx, b_idx in pairings:
            a, b = abbrs[a_idx], abbrs[b_idx]
            # Deterministic home/away coin flip, seeded per matchup.
            h = hashlib.sha256(f"{league_seed}:{week_num}:{a}:{b}".encode()).digest()
            if h[0] % 2 == 0:
                week_games.append((a, b))
            else:
                week_games.append((b, a))
        weeks.append(week_games)
    return weeks
