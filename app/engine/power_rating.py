"""
Team Power Rating (Elo) system, GDD Part 1 Sec 7.2 -- UI label "Power
Ranking." Feeds Sec 6.2.1's pre-game win probability and Sec 6.2.2's
parity/upset model, both consumed by the Score Fidelity System
(app/engine/score_fidelity.py) to shape each game's scoring.

Sec 6.2.1 cross-references "the Elo system defined in Sec 9.2," but no
distinct Sec 9.2 exists in this GDD document -- likely a stale
cross-reference surviving from the doc's synthesis out of 9
previously-separate GDD exports (see the GDD's own Version History).
Sec 7.2 is the only Elo system actually defined, and is treated as
authoritative here.
"""
from __future__ import annotations
import math

INITIAL_RATING = 1500.0
K_FACTOR = 20.0
HOME_FIELD_ADVANTAGE = 55.0  # applied pre-game only (win prob, rating update expectation) -- does not persist
PARITY_ADJUSTMENT = 50.0
PARITY_WEEK_THRESHOLD = 10


def parity_adjusted_rating(rating: float, wins: int, games_played: int, current_week: int) -> float:
    """GDD Sec 6.2.2: a temporary pre-game adjustment simulating
    late-season pressure/parity, active only after Week 10 for a team on
    an extreme (perfect or winless) streak, so perfect/winless seasons
    stay rare."""
    if current_week <= PARITY_WEEK_THRESHOLD or games_played == 0:
        return rating
    if wins == games_played:
        return rating - PARITY_ADJUSTMENT
    if wins == 0:
        return rating + PARITY_ADJUSTMENT
    return rating


def home_win_probability(
    home_rating: float, home_wins: int, home_games_played: int,
    away_rating: float, away_wins: int, away_games_played: int,
    current_week: int,
) -> float:
    """GDD Sec 6.2.1."""
    home_adj = parity_adjusted_rating(home_rating, home_wins, home_games_played, current_week)
    away_adj = parity_adjusted_rating(away_rating, away_wins, away_games_played, current_week)
    rating_difference = (home_adj + HOME_FIELD_ADVANTAGE) - away_adj
    return 1.0 / (1.0 + 10 ** (-rating_difference / 400.0))


def update_ratings(home_rating: float, away_rating: float, home_score: int, away_score: int) -> tuple[float, float]:
    """GDD Sec 7.2. A pure function of inputs, no RNG. The margin-of-victory
    multiplier dampens blowout swings against a big pre-existing rating
    gap (a huge favorite blowing out a huge underdog moves ratings less
    than the same margin between evenly-matched teams). A tie (home_score
    == away_score) naturally produces point_diff == 0, so
    log(0 + 1) == 0 and delta == 0 -- no rating change, no special case
    needed."""
    expected_home = 1.0 / (1.0 + 10 ** (-((home_rating + HOME_FIELD_ADVANTAGE) - away_rating) / 400.0))
    if home_score > away_score:
        actual_home = 1.0
    elif home_score < away_score:
        actual_home = 0.0
    else:
        actual_home = 0.5

    point_diff = abs(home_score - away_score)
    winner_rating = home_rating if home_score >= away_score else away_rating
    loser_rating = away_rating if home_score >= away_score else home_rating
    mov_multiplier = math.log(point_diff + 1) * (2.2 / (((winner_rating - loser_rating) * 0.001) + 2.2))

    delta = K_FACTOR * mov_multiplier * (actual_home - expected_home)
    return home_rating + delta, away_rating - delta


# ---------------------------------------------------------------------------
# Power RANKING order (display) -- rating plus a record anchor
# ---------------------------------------------------------------------------
# Brian's report, 2026-09-14: late in the season an 8-7 team sat 3 spots
# ahead of an 11-4 team because the rankings sorted on raw Elo alone, which
# can drift away from the standings (a couple of lopsided wins inflate it).
# He wants rankings to reflect team strength, but with losing teams
# anchored downward and winning teams upward as the season goes on.
#
# So the ranking sorts on power_score(): the untouched Elo rating PLUS an
# additive record bonus (never a re-weighting of the rating itself -- the
# Elo value still drives win probability in the sim exactly as before).
# The bonus is (win% - .500) * RECORD_ANCHOR_POINTS, scaled by how much of
# the season is in the books: ~0 in Week 1 (strength dominates early),
# full weight after a full slate. At full weight one extra win is worth
# ~35 rating points, so an 11-4 team outranks an 8-7 team unless the 8-7
# team is ~200+ Elo points stronger -- a genuinely extreme gap.
RECORD_ANCHOR_POINTS = 600.0
RECORD_ANCHOR_FULL_WEIGHT_GAMES = 17  # a full regular-season slate (schedule.py: 17 games + 1 bye)


def record_anchor_bonus(wins: int, losses: int, ties: int = 0) -> float:
    games = wins + losses + ties
    if games <= 0:
        return 0.0
    weight = min(games / RECORD_ANCHOR_FULL_WEIGHT_GAMES, 1.0)
    win_pct = (wins + 0.5 * ties) / games
    return weight * (win_pct - 0.5) * RECORD_ANCHOR_POINTS


def power_score(rating: float, wins: int, losses: int, ties: int = 0) -> float:
    """What the Power Rankings sort (and display) by -- see above."""
    return rating + record_anchor_bonus(wins, losses, ties)


def power_score_for(record) -> float:
    """power_score() for anything shaped like season_state.TeamRecord."""
    return power_score(record.power_rating, record.wins, record.losses, getattr(record, "ties", 0))


def regress_to_mean(rating: float) -> float:
    """GDD Sec 7.2: at season rollover, regress a third of the way back
    toward the league baseline."""
    return 0.67 * rating + 0.33 * INITIAL_RATING
