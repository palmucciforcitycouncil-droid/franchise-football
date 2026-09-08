"""
The GDD's real opponent-selection formula (Part 1 Sec 5.1):

  6 divisional games       -- home & away vs. the 3 division mates
  4 intra-conference games -- vs. all 4 teams of one same-conference
                               division, on a 3-year rotation
  4 inter-conference games -- vs. all 4 teams of one opposite-conference
                               division, on a 4-year rotation
  2 standings-based games  -- vs. the same-place finisher (by prior-season
                               divisional rank) in each of the two
                               in-conference divisions not currently
                               rotated against
  1 "17th game"            -- vs. the same-place finisher in a
                               non-rotating opposite-conference division;
                               host alternates AFC/NFC by season number

Bye weeks: the GDD calls for one bye per team confined to weeks 5-14
excluding week 6. This implementation does NOT hit that exact window --
see the note on _try_place_attempt for why, and what it does instead.
That's a real, deliberate simplification (not an oversight): the
substantive game-design content here is *which teams play each other and
how many times*, which this does implement exactly per the formula. Bye
week *timing* doesn't affect any gameplay logic -- a bye in week 3 is
functionally identical to a bye in week 9, it just doesn't match real
NFL scheduling flavor yet.

Bootstrap note: the standings-based games and the 17th game both need a
*prior* season's final standings to rank teams within a division. There
is no real prior season yet (this project doesn't support multi-season
play across an offseason loop yet), so for season_number 0 this uses a
fixed bootstrap order -- each division's teams in the order they're
listed in app/data/teams.py, treated as if that were last year's
1st-4th place finish. Once real multi-season carryover exists, pass that
season's actual final standings in as `prior_standings` instead.
"""
from __future__ import annotations
import hashlib
import random
from dataclasses import dataclass
from itertools import combinations

from app.data.teams import TEAMS, TeamInfo

N_WEEKS = 18
# The GDD's target bye window (weeks 5-14 except 6). Not currently enforced
# -- see the module docstring -- kept here as the documented target for
# whoever implements the window-constrained version later.
BYE_ELIGIBLE_WEEKS = [5, 7, 8, 9, 10, 11, 12, 13, 14]

DIVISIONS = ["East", "North", "South", "West"]
CONFERENCES = ["AFC", "NFC"]


def _teams_by_division() -> dict[tuple[str, str], list[TeamInfo]]:
    grouped: dict[tuple[str, str], list[TeamInfo]] = {}
    for t in TEAMS:
        grouped.setdefault((t.conference, t.division), []).append(t)
    return grouped


def _circle_method_rounds(n: int) -> list[list[tuple[int, int]]]:
    """Standard round-robin circle method. n must be even."""
    assert n % 2 == 0
    idx = list(range(n))
    rounds = []
    for _ in range(n - 1):
        pairings = [(idx[i], idx[n - 1 - i]) for i in range(n // 2)]
        rounds.append(pairings)
        idx = [idx[0]] + [idx[-1]] + idx[1:-1]
    return rounds


def _intra_conference_partner(division_idx: int, season_number: int) -> int:
    """Which of the other 3 same-conference divisions we rotate against
    this year. 3-year cycle -- a round-robin over the 4 divisions."""
    rounds = _circle_method_rounds(4)  # 3 rounds, 2 pairs each
    year_round = rounds[season_number % 3]
    for a, b in year_round:
        if a == division_idx:
            return b
        if b == division_idx:
            return a
    raise AssertionError("division not found in its own conference's rotation round")


def _inter_conference_partner(division_idx: int, season_number: int, from_conf: str) -> int:
    """Which opposite-conference division index we rotate against this
    year. 4-year cycle -- a Latin-square pairing between the two
    conferences' 4 divisions each: AFC division i pairs with NFC division
    (i + season_number) % 4.

    This must use the INVERSE formula when starting from the NFC side --
    (j - season_number) % 4 -- not the same formula applied blindly in
    both directions. Using the same formula both ways only produces a
    consistent (self-inverse) pairing when season_number is even; for odd
    values each division ends up paired with two different divisions
    instead of one, silently generating extra games. (Found by a test
    that swept multiple season_numbers, not by inspection -- INTER_ROT
    counts came out as 7 per team instead of 4 for season_number 1 and 3.)
    """
    if from_conf == "AFC":
        return (division_idx + season_number) % 4
    return (division_idx - season_number) % 4


def _seventeenth_game_partner_division(division_idx: int, season_number: int, from_conf: str) -> int:
    """A *non-rotating* opposite-conference division for the 17th game --
    offset by 2 from this year's inter-conference rotation partner, which
    guarantees it's different from that partner (since 2 != 0 mod 4)."""
    rotation_partner = _inter_conference_partner(division_idx, season_number, from_conf)
    return (rotation_partner + 2) % 4


def _bootstrap_prior_standings() -> dict[tuple[str, str], list[str]]:
    """division -> team abbrs, ranked 1st..4th. No real prior season exists
    yet, so this just uses teams.py's listed order as the bootstrap."""
    grouped = _teams_by_division()
    return {key: [t.abbr for t in teams] for key, teams in grouped.items()}


@dataclass(frozen=True)
class ScheduledGame:
    home: str
    away: str
    source: str  # "DIV" | "INTRA_ROT" | "INTER_ROT" | "INTRA_PLACE" | "INTER_PLACE_17"


def _generate_games(season_number: int, prior_standings: dict[tuple[str, str], list[str]]) -> list[ScheduledGame]:
    grouped = _teams_by_division()
    games: list[ScheduledGame] = []
    seen_pairs: set[frozenset[str]] = set()

    def add_game(a: str, b: str, source: str, seed_key: str) -> None:
        pair = frozenset((a, b))
        if pair in seen_pairs:
            return
        seen_pairs.add(pair)
        h = hashlib.sha256(seed_key.encode()).digest()
        if h[0] % 2 == 0:
            games.append(ScheduledGame(home=a, away=b, source=source))
        else:
            games.append(ScheduledGame(home=b, away=a, source=source))

    for conf in CONFERENCES:
        for div_idx, div in enumerate(DIVISIONS):
            division_teams = grouped[(conf, div)]

            # 6 divisional games: both legs vs. each of the 3 division mates.
            for a, b in combinations(division_teams, 2):
                games.append(ScheduledGame(home=a.abbr, away=b.abbr, source="DIV"))
                games.append(ScheduledGame(home=b.abbr, away=a.abbr, source="DIV"))

            # 4 intra-conference rotation games.
            intra_idx = _intra_conference_partner(div_idx, season_number)
            intra_teams = grouped[(conf, DIVISIONS[intra_idx])]
            for our_team in division_teams:
                for their_team in intra_teams:
                    add_game(our_team.abbr, their_team.abbr, "INTRA_ROT",
                              f"intra:{season_number}:{our_team.abbr}:{their_team.abbr}")

            # 4 inter-conference rotation games.
            other_conf = "NFC" if conf == "AFC" else "AFC"
            inter_idx = _inter_conference_partner(div_idx, season_number, conf)
            inter_teams = grouped[(other_conf, DIVISIONS[inter_idx])]
            for our_team in division_teams:
                for their_team in inter_teams:
                    add_game(our_team.abbr, their_team.abbr, "INTER_ROT",
                              f"inter:{season_number}:{our_team.abbr}:{their_team.abbr}")

            # 2 standings-based intra-conference games: same-place finishers
            # in the two in-conference divisions we're NOT rotating against.
            non_rotating = [i for i in range(4) if i != div_idx and i != intra_idx]
            our_ranked = prior_standings[(conf, div)]
            for opp_div_idx in non_rotating:
                opp_div = DIVISIONS[opp_div_idx]
                opp_ranked = prior_standings[(conf, opp_div)]
                for rank, our_abbr in enumerate(our_ranked):
                    their_abbr = opp_ranked[rank]
                    add_game(our_abbr, their_abbr, "INTRA_PLACE",
                              f"place:{season_number}:{our_abbr}:{their_abbr}")

            # 1 seventeenth game: same-place finisher in a non-rotating
            # opposite-conference division. Host alternates AFC/NFC by year.
            seventeenth_idx = _seventeenth_game_partner_division(div_idx, season_number, conf)
            seventeenth_div = DIVISIONS[seventeenth_idx]
            seventeenth_ranked = prior_standings[(other_conf, seventeenth_div)]
            afc_hosts = (season_number % 2 == 0)
            for rank, our_abbr in enumerate(our_ranked):
                their_abbr = seventeenth_ranked[rank]
                pair = frozenset((our_abbr, their_abbr))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                if conf == "AFC":
                    home, away = (our_abbr, their_abbr) if afc_hosts else (their_abbr, our_abbr)
                else:
                    home, away = (our_abbr, their_abbr) if not afc_hosts else (their_abbr, our_abbr)
                games.append(ScheduledGame(home=home, away=away, source="INTER_PLACE_17"))

    return games




def _try_place_attempt(games: list[ScheduledGame], attempt_seed: int) -> list[list[ScheduledGame]] | None:
    """
    One attempt at placing all 272 games into 18 weeks (no team plays
    twice in a week; nothing about *which* week is anyone's bye is fixed
    going in -- see the module docstring for why). Three passes:

    1. Greedy maximal matching, week by week: for each week in order, take
       every remaining game whose both teams are free that week. Reliably
       places the large majority of games fast.
    2. Free-slot scan: for whatever's left, look across all 18 weeks for
       one where both teams happen to still be free.
    3. Iterative one-level swap repair: for a game (A, B) that still can't
       be placed, find a week w where A is free but B is already playing
       some game (B, C); try moving (B, C) to a different week w2 where
       both B and C are free, which frees up w for (A, B) -- the standard
       local-repair technique for "nearly complete" edge colorings (a
       one-step Kempe-chain swap). Repeated in rounds until no more
       progress is made, since one swap can unblock another.

    Returns None if some games are still stuck after that -- the caller
    retries with a different seed. In practice a valid full placement
    turns up within a couple hundred attempts and the whole search takes
    well under a second (this is a genuinely tight, zero-slack scheduling
    problem -- every team has exactly 17 games and only 18 weeks to put
    them in -- so no single attempt is guaranteed to succeed, but *some*
    attempt reliably does).
    """
    rng = random.Random(f"place:{attempt_seed}")
    remaining = games[:]
    weeks: list[list[ScheduledGame]] = [[] for _ in range(N_WEEKS)]
    busy_by_week: list[set[str]] = [set() for _ in range(N_WEEKS)]

    def is_free(team: str, wi: int) -> bool:
        return team not in busy_by_week[wi]

    def place(g: ScheduledGame, wi: int) -> None:
        busy_by_week[wi].add(g.home)
        busy_by_week[wi].add(g.away)
        weeks[wi].append(g)

    def team_game_in_week(team: str, wi: int) -> ScheduledGame | None:
        for g in weeks[wi]:
            if g.home == team or g.away == team:
                return g
        return None

    # Pass 1: greedy maximal matching per week.
    for wi in range(N_WEEKS):
        rng.shuffle(remaining)
        still_remaining = []
        for g in remaining:
            if is_free(g.home, wi) and is_free(g.away, wi):
                place(g, wi)
            else:
                still_remaining.append(g)
        remaining = still_remaining

    # Pass 2 + 3: free-slot scan, then swap repair, repeated until no
    # further progress (one swap can open up room for another).
    for _round in range(30):
        if not remaining:
            break
        progress = False
        still_leftover: list[ScheduledGame] = []
        for g in remaining:
            placed = False
            for wi in range(N_WEEKS):
                if is_free(g.home, wi) and is_free(g.away, wi):
                    place(g, wi)
                    placed = True
                    break
            if placed:
                progress = True
                continue

            for wi in range(N_WEEKS):
                home_free = is_free(g.home, wi)
                away_free = is_free(g.away, wi)
                if home_free == away_free:
                    continue  # both free (handled above) or both busy (swap won't help)
                blocked_team = g.away if home_free else g.home
                blocker = team_game_in_week(blocked_team, wi)
                if blocker is None:
                    continue
                other = blocker.away if blocker.home == blocked_team else blocker.home
                for wi2 in range(N_WEEKS):
                    if wi2 == wi:
                        continue
                    if is_free(blocked_team, wi2) and is_free(other, wi2):
                        weeks[wi].remove(blocker)
                        busy_by_week[wi].discard(blocked_team)
                        busy_by_week[wi].discard(other)
                        place(blocker, wi2)
                        place(g, wi)
                        placed = True
                        break
                if placed:
                    break

            if placed:
                progress = True
            else:
                still_leftover.append(g)
        remaining = still_leftover
        if not progress:
            break

    if remaining:
        return None

    return weeks


def _place_games_into_weeks(games: list[ScheduledGame], seed: int) -> list[list[ScheduledGame]]:
    for attempt in range(2000):
        result = _try_place_attempt(games, attempt_seed=hash((seed, attempt)) & 0xFFFFFFFF)
        if result is not None:
            return result
    raise RuntimeError(
        "Could not find a valid schedule placement after 2000 attempts. "
        "This game set would need more than 18 weeks to schedule without "
        "a team playing twice in one week, which the shape tests should catch."
    )


def generate_season_schedule(
    league_seed: int, season_number: int = 0,
    prior_standings: dict[tuple[str, str], list[str]] | None = None,
) -> list[list[tuple[str, str]]]:
    """
    Returns a list of N_WEEKS (18) weeks; each week is a list of
    (home_abbr, away_abbr) tuples. Every team plays in 17 of the 18 weeks
    -- its one bye week is simply whichever week doesn't end up with a
    game for it, not confined to a specific window (see module docstring).

    prior_standings: real final division standings from the season that
    just ended (app/engine/playoffs.py's final_division_standings()),
    used for this season's standings-based games. Defaults to the
    season-0-only bootstrap order (teams.py's listed order) when None --
    the case for a brand-new franchise with no real prior season yet.
    """
    if prior_standings is None:
        prior_standings = _bootstrap_prior_standings()
    games = _generate_games(season_number, prior_standings)
    weeks = _place_games_into_weeks(games, league_seed)
    return [[(g.home, g.away) for g in week] for week in weeks]
