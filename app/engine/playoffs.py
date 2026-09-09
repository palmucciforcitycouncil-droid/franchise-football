"""
Playoffs & Tie-Breakers (GDD Part 1 Sec 7.3): real 14-team bracket
seeding (7 per conference: 4 division winners seeded 1-4, 3 wild cards
seeded 5-7), the full multi-step tie-breaker chain the GDD specifies
for both division ties and wild-card ties, and bracket-round pairing
(Wild Card -> Divisional -> Conference Championship -> Super Bowl).

The GDD's own text flags this as a real risk area: "Multi-team
tie-breakers are easy to implement incorrectly... write at least one
worked 3-team tie scenario, stepped through by hand, and turn it into a
regression test" (Sec 7.3's own "Test-plan gap" note, repeated in the
Part 2 to-do list). See tests/test_playoffs.py for that worked example.

Deliberate scope simplifications, documented rather than silently cut:
- "Combined ranking...in points scored and points allowed" is
  implemented as -(rank_by_points_scored + rank_by_points_allowed)
  within the relevant pool (lower combined rank sum = better), the
  standard reading of this NFL tie-breaker step.
- "Common games" requires at least one common opponent to produce a
  result at all; the GDD's own "min. four" common games threshold for
  the wild-card chain is honored (fewer than 4 shared games -> this
  step doesn't discriminate, matching real NFL practice).
- Head-to-head is evaluated as combined win% among games actually
  played between members of the currently-tied group (0.5 -- neutral,
  a non-discriminating value -- if a team has no such games) rather
  than the full real-NFL edge-case rulebook (partial sweeps, etc.).
- The final "Coin toss" step is a deterministic value seeded from
  LEAGUE_SEED (via app.engine.rng.stable_seed), not a true coin flip --
  keeps the whole bracket reproducible for a given seed, consistent
  with GDD Sec 1.3's determinism policy.
- Playoff overtime: the GDD specifies full 15-minute overtime periods
  (Sec 6, "Playoff Overtime"), which needs a real clock/quarter model
  this engine doesn't have (see drive_sim.py's module docstring for the
  same limitation in the regular season). A playoff game's winner is
  decided the same way a regular-season game already is --
  game_sim.simulate_game's `winner = "home" if h >= a else "away"` --
  so a tied score (rare but possible) goes to the home team rather than
  a simulated overtime period.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from app.data.teams import TEAMS, TEAMS_BY_ABBR
from app.engine.rng import stable_seed
from app.engine.game_state import GameResult

# ---------------------------------------------------------------------------
# Per-team derived data from real games played this season
# ---------------------------------------------------------------------------

def _played_games(season):
    """(WeekGame, home_abbr, away_abbr) for every game simulated this
    season, regardless of team -- the shared basis every tiebreaker
    below filters down from."""
    return [
        (g, g.home_abbr, g.away_abbr)
        for week in season.schedule
        for g in week
        if g.result is not None
    ]


def _team_games(season, team_abbr: str):
    """(WeekGame, opponent_abbr, team_is_home) for team_abbr's own played games."""
    out = []
    for g, home, away in _played_games(season):
        if home == team_abbr:
            out.append((g, away, True))
        elif away == team_abbr:
            out.append((g, home, False))
    return out


def _win_loss_tie(games_with_scores) -> tuple[int, int, int]:
    """games_with_scores: iterable of (my_score, opp_score). Returns (W, L, T)."""
    w = l = t = 0
    for my, opp in games_with_scores:
        if my > opp:
            w += 1
        elif my < opp:
            l += 1
        else:
            t += 1
    return w, l, t


def _pct(w: int, l: int, t: int) -> float:
    total = w + l + t
    return (w + 0.5 * t) / total if total else 0.0


def _scores_for(season, team_abbr: str, opponent_filter=None):
    for g, opp, is_home in _team_games(season, team_abbr):
        if opponent_filter is not None and opp not in opponent_filter:
            continue
        my = g.result.home_score if is_home else g.result.away_score
        theirs = g.result.away_score if is_home else g.result.home_score
        yield my, theirs, opp


def head_to_head_pct(season, team_abbr: str, group: list[str]) -> float:
    others = set(group) - {team_abbr}
    scores = list(_scores_for(season, team_abbr, opponent_filter=others))
    if not scores:
        return 0.5  # no head-to-head games played -- neutral, doesn't discriminate
    return _pct(*_win_loss_tie((my, opp) for my, opp, _ in scores))


def division_record_pct(season, team_abbr: str) -> float:
    division = TEAMS_BY_ABBR[team_abbr].division
    conference = TEAMS_BY_ABBR[team_abbr].conference
    division_mates = {
        t.abbr for t in TEAMS if t.conference == conference and t.division == division and t.abbr != team_abbr
    }
    scores = list(_scores_for(season, team_abbr, opponent_filter=division_mates))
    return _pct(*_win_loss_tie((my, opp) for my, opp, _ in scores))


def conference_record_pct(season, team_abbr: str) -> float:
    conference = TEAMS_BY_ABBR[team_abbr].conference
    conf_teams = {t.abbr for t in TEAMS if t.conference == conference and t.abbr != team_abbr}
    scores = list(_scores_for(season, team_abbr, opponent_filter=conf_teams))
    return _pct(*_win_loss_tie((my, opp) for my, opp, _ in scores))


def _common_opponents(season, group: list[str]) -> set[str]:
    opponent_sets = []
    for team_abbr in group:
        opponent_sets.append({opp for _, opp, _ in _team_games(season, team_abbr)} - set(group))
    if not opponent_sets:
        return set()
    common = opponent_sets[0]
    for s in opponent_sets[1:]:
        common &= s
    return common


def common_games_pct(season, team_abbr: str, group: list[str], min_games: int = 4) -> float:
    common = _common_opponents(season, group)
    scores = list(_scores_for(season, team_abbr, opponent_filter=common))
    if len(scores) < min_games:
        return 0.5  # not enough shared games -- doesn't discriminate, matches real NFL practice
    return _pct(*_win_loss_tie((my, opp) for my, opp, _ in scores))


def strength_of_victory(season, team_abbr: str) -> float:
    """Combined win% of every team this team has beaten."""
    beaten = {opp for my, theirs, opp in _scores_for(season, team_abbr) if my > theirs}
    if not beaten:
        return 0.0
    total_w = total_l = total_t = 0
    for opp in beaten:
        w, l, t = _win_loss_tie((my, theirs) for my, theirs, _ in _scores_for(season, opp))
        total_w += w
        total_l += l
        total_t += t
    return _pct(total_w, total_l, total_t)


def strength_of_schedule(season, team_abbr: str) -> float:
    """Combined win% of every opponent actually played (each occurrence, not deduped)."""
    opponents = [opp for _, opp, _ in _team_games(season, team_abbr)]
    if not opponents:
        return 0.0
    total_w = total_l = total_t = 0
    for opp in opponents:
        w, l, t = _win_loss_tie((my, theirs) for my, theirs, _ in _scores_for(season, opp))
        total_w += w
        total_l += l
        total_t += t
    return _pct(total_w, total_l, total_t)


def _combined_scoring_rank(season, team_abbr: str, pool: list[str]) -> float:
    """Rank (1 = best) among `pool` by points scored, plus rank (1 = best,
    i.e. fewest allowed) by points allowed, summed and negated so a
    LOWER combined-rank sum (better) becomes a HIGHER return value,
    keeping every tiebreaker step's "higher is better" convention."""
    by_scored = sorted(pool, key=lambda t: -season.records[t].points_for)
    by_allowed = sorted(pool, key=lambda t: season.records[t].points_against)
    rank_scored = by_scored.index(team_abbr) + 1
    rank_allowed = by_allowed.index(team_abbr) + 1
    return -(rank_scored + rank_allowed)


def combined_scoring_rank_conference(season, team_abbr: str) -> float:
    conference = TEAMS_BY_ABBR[team_abbr].conference
    pool = [t.abbr for t in TEAMS if t.conference == conference]
    return _combined_scoring_rank(season, team_abbr, pool)


def combined_scoring_rank_league(season, team_abbr: str) -> float:
    pool = [t.abbr for t in TEAMS]
    return _combined_scoring_rank(season, team_abbr, pool)


def net_points_common(season, team_abbr: str, group: list[str]) -> int:
    common = _common_opponents(season, group)
    return sum(my - theirs for my, theirs, _ in _scores_for(season, team_abbr, opponent_filter=common))


def net_points_conference(season, team_abbr: str) -> int:
    conference = TEAMS_BY_ABBR[team_abbr].conference
    conf_teams = {t.abbr for t in TEAMS if t.conference == conference and t.abbr != team_abbr}
    return sum(my - theirs for my, theirs, _ in _scores_for(season, team_abbr, opponent_filter=conf_teams))


def net_points_all(season, team_abbr: str) -> int:
    rec = season.records[team_abbr]
    return rec.points_for - rec.points_against


def net_touchdowns_all(season, team_abbr: str) -> int:
    tds = 0
    for g, home, away in _played_games(season):
        for p in g.result.plays:
            if p.outcome == "touchdown" and p.offense_abbr == team_abbr:
                tds += 1
    return tds


def coin_toss(season, team_abbr: str) -> float:
    """Deterministic, not a real coin flip -- keeps the bracket
    reproducible for a given LEAGUE_SEED (GDD Sec 1.3)."""
    seed = stable_seed(season.league_seed, "playoff_tiebreak_coin", team_abbr)
    return seed % 1_000_000


# ---------------------------------------------------------------------------
# Tie-break chains (GDD Sec 7.3 A/B), applied via a generic elimination loop
# ---------------------------------------------------------------------------

def _division_steps(group):
    return [
        lambda season, t: head_to_head_pct(season, t, group),
        lambda season, t: division_record_pct(season, t),
        lambda season, t: common_games_pct(season, t, group, min_games=1),
        lambda season, t: conference_record_pct(season, t),
        lambda season, t: strength_of_victory(season, t),
        lambda season, t: strength_of_schedule(season, t),
        lambda season, t: combined_scoring_rank_conference(season, t),
        lambda season, t: combined_scoring_rank_league(season, t),
        lambda season, t: net_points_common(season, t, group),
        lambda season, t: net_points_all(season, t),
        lambda season, t: net_touchdowns_all(season, t),
        lambda season, t: coin_toss(season, t),
    ]


def _wildcard_steps(group):
    return [
        lambda season, t: head_to_head_pct(season, t, group),
        lambda season, t: conference_record_pct(season, t),
        lambda season, t: common_games_pct(season, t, group, min_games=4),
        lambda season, t: strength_of_victory(season, t),
        lambda season, t: strength_of_schedule(season, t),
        lambda season, t: combined_scoring_rank_conference(season, t),
        lambda season, t: combined_scoring_rank_league(season, t),
        lambda season, t: net_points_conference(season, t),
        lambda season, t: net_points_all(season, t),
        lambda season, t: net_touchdowns_all(season, t),
        lambda season, t: coin_toss(season, t),
    ]


def _break_tie(season, tied_group: list[str], step_factory) -> list[str]:
    """GDD Sec 7.3.C: 'Use the same category order... When one team is
    separated at any step, eliminate it and re-apply the procedure to
    the remaining teams.' Recurses with a FRESH step list each time a
    subgroup splits off, since a step that didn't discriminate for the
    original larger group might (or a smaller group's head-to-head/
    common-games computation differs -- both take `group` as a
    parameter) discriminate for the split-off subgroup."""
    if len(tied_group) <= 1:
        return list(tied_group)
    steps = step_factory(tied_group)
    for step in steps:
        values = {t: step(season, t) for t in tied_group}
        best = max(values.values())
        best_teams = [t for t in tied_group if values[t] == best]
        if len(best_teams) < len(tied_group):
            worse_teams = [t for t in tied_group if t not in best_teams]
            return (
                _break_tie(season, best_teams, step_factory)
                + _break_tie(season, worse_teams, step_factory)
            )
    return list(tied_group)  # exhausted every step without discriminating (shouldn't happen -- coin_toss is ~unique)


def rank_teams(season, teams: list[str], step_factory) -> list[str]:
    """Full best-to-worst ranking of `teams` by real win%, breaking any
    ties (equal wins AND losses) via the given tiebreak chain."""
    groups: dict[tuple[int, int], list[str]] = {}
    for t in teams:
        rec = season.records[t]
        groups.setdefault((rec.wins, rec.losses), []).append(t)

    def win_pct(key):
        w, l = key
        return w / (w + l) if (w + l) else 0.0

    ordered: list[str] = []
    for key in sorted(groups.keys(), key=lambda k: -win_pct(k)):
        group = groups[key]
        ordered.extend(group if len(group) == 1 else _break_tie(season, group, step_factory))
    return ordered


# ---------------------------------------------------------------------------
# Seeding & bracket
# ---------------------------------------------------------------------------

def seed_conference(season, conference: str) -> list[str]:
    """Returns 7 team abbrs in seed order (index 0 = seed 1) for one
    conference: seeds 1-4 are the four division winners (each division's
    own winner determined via the DIVISION tiebreak chain, then the four
    winners ranked against each other via the WILDCARD chain -- they're
    no longer being compared within one division); seeds 5-7 are the
    three non-division-winners with the best records, via the WILDCARD
    chain. A division's tiebreaker losers go back into the wildcard pool
    and are re-ranked from scratch there, per Sec 7.3.C's instruction to
    "re-apply the procedure to the remaining teams" -- how close they
    came to winning their own division doesn't carry over."""
    conf_teams = [t.abbr for t in TEAMS if t.conference == conference]
    divisions: dict[str, list[str]] = {}
    for abbr in conf_teams:
        divisions.setdefault(TEAMS_BY_ABBR[abbr].division, []).append(abbr)

    division_winners = [rank_teams(season, teams, _division_steps)[0] for teams in divisions.values()]
    division_winners_seeded = rank_teams(season, division_winners, _wildcard_steps)

    wildcard_pool = [t for t in conf_teams if t not in division_winners]
    wildcards_seeded = rank_teams(season, wildcard_pool, _wildcard_steps)[:3]

    return division_winners_seeded + wildcards_seeded


def bubble_teams(season, conference: str, seeded: list[str], limit: int = 5) -> list[str]:
    """The teams "in the hunt" -- closest to a playoff berth but outside
    the real 7-seed bracket (`seeded`, from `seed_conference`). Ranked by
    the same real WILDCARD tiebreak chain the wildcard seeds themselves
    use, applied to the whole conference then filtered down to whoever
    didn't make the cut -- not a separate/approximate ordering. Used by
    the Playoffs page's "In The Hunt" widget (GDD Sec 10.4.6)."""
    conf_teams = [t.abbr for t in TEAMS if t.conference == conference]
    ranked = rank_teams(season, conf_teams, _wildcard_steps)
    return [abbr for abbr in ranked if abbr not in seeded][:limit]


@dataclass
class PlayoffMatchup:
    round_name: str  # "WC" | "DIV" | "CONF" | "SB"
    conference: str | None  # "AFC" | "NFC" | None for the Super Bowl
    home_abbr: str
    away_abbr: str
    home_seed: int
    away_seed: int
    result: GameResult | None = None  # once simulated -- full play-by-play + box score, same as a regular-season WeekGame

    @property
    def is_complete(self) -> bool:
        return self.result is not None

    @property
    def winner_abbr(self) -> str | None:
        if not self.is_complete:
            return None
        return self.home_abbr if self.result.winner == "home" else self.away_abbr

    @property
    def winner_seed(self) -> int | None:
        if not self.is_complete:
            return None
        return self.home_seed if self.result.winner == "home" else self.away_seed


@dataclass
class PlayoffBracket:
    afc_seeds: list[str]  # 7 abbrs, index 0 = seed 1
    nfc_seeds: list[str]
    rounds: list[list[PlayoffMatchup]] = field(default_factory=list)

    @property
    def current_round_name(self) -> str | None:
        """The next round that still needs simulating, or None once the
        Super Bowl is complete."""
        if not self.rounds:
            return "WC"
        last = self.rounds[-1]
        if not all(m.is_complete for m in last):
            return last[0].round_name
        if last[0].round_name == "SB":
            return None
        return {"WC": "DIV", "DIV": "CONF", "CONF": "SB"}[last[0].round_name]

    @property
    def is_complete(self) -> bool:
        return self.current_round_name is None

    @property
    def champion_abbr(self) -> str | None:
        if not self.is_complete:
            return None
        return self.rounds[-1][0].winner_abbr

    def seed_of(self, team_abbr: str, conference: str) -> int:
        seeds = self.afc_seeds if conference == "AFC" else self.nfc_seeds
        return seeds.index(team_abbr) + 1


def _reseed_pairs(alive_seeds: list[int]) -> list[tuple[int, int]]:
    """Standard NFL re-seeding: the best remaining seed plays the worst
    remaining seed, the next-best plays the next-worst, and so on
    inward. Works identically for the Divisional round (4 -> 2 games)
    and the Conference Championship (2 -> 1 game)."""
    seeds = sorted(alive_seeds)
    return [(seeds[i], seeds[-(i + 1)]) for i in range(len(seeds) // 2)]


def build_wild_card_round(season) -> PlayoffBracket:
    afc_seeds = seed_conference(season, "AFC")
    nfc_seeds = seed_conference(season, "NFC")
    matchups = []
    for conference, seeds in (("AFC", afc_seeds), ("NFC", nfc_seeds)):
        for better_seed, worse_seed in [(2, 7), (3, 6), (4, 5)]:
            matchups.append(PlayoffMatchup(
                round_name="WC", conference=conference,
                home_abbr=seeds[better_seed - 1], away_abbr=seeds[worse_seed - 1],
                home_seed=better_seed, away_seed=worse_seed,
            ))
    return PlayoffBracket(afc_seeds=afc_seeds, nfc_seeds=nfc_seeds, rounds=[matchups])


def build_next_round(bracket: PlayoffBracket) -> list[PlayoffMatchup]:
    """Builds the matchups for the round after the bracket's most
    recently completed one. Assumes that round is fully complete."""
    last_round = bracket.rounds[-1]
    last_name = last_round[0].round_name

    if last_name == "WC":
        matchups = []
        for conference, seeds in (("AFC", bracket.afc_seeds), ("NFC", bracket.nfc_seeds)):
            alive = [1] + [m.winner_seed for m in last_round if m.conference == conference]
            for better, worse in _reseed_pairs(alive):
                matchups.append(PlayoffMatchup(
                    round_name="DIV", conference=conference,
                    home_abbr=seeds[better - 1], away_abbr=seeds[worse - 1],
                    home_seed=better, away_seed=worse,
                ))
        return matchups

    if last_name == "DIV":
        matchups = []
        for conference, seeds in (("AFC", bracket.afc_seeds), ("NFC", bracket.nfc_seeds)):
            alive = [m.winner_seed for m in last_round if m.conference == conference]
            (better, worse), = _reseed_pairs(alive)
            matchups.append(PlayoffMatchup(
                round_name="CONF", conference=conference,
                home_abbr=seeds[better - 1], away_abbr=seeds[worse - 1],
                home_seed=better, away_seed=worse,
            ))
        return matchups

    if last_name == "CONF":
        afc_champ = next(m for m in last_round if m.conference == "AFC").winner_abbr
        nfc_champ = next(m for m in last_round if m.conference == "NFC").winner_abbr
        afc_seed = bracket.seed_of(afc_champ, "AFC")
        nfc_seed = bracket.seed_of(nfc_champ, "NFC")
        # Neutral site (no real GDD-specified home team for the Super Bowl) --
        # the better overall seed is designated "home" purely for engine
        # bookkeeping (box score layout, home-field Elo term); see this
        # module's docstring for the disclosed simplification.
        if afc_seed <= nfc_seed:
            home_abbr, home_seed, home_conf = afc_champ, afc_seed, "AFC"
            away_abbr, away_seed = nfc_champ, nfc_seed
        else:
            home_abbr, home_seed, home_conf = nfc_champ, nfc_seed, "NFC"
            away_abbr, away_seed = afc_champ, afc_seed
        return [PlayoffMatchup(
            round_name="SB", conference=None,
            home_abbr=home_abbr, away_abbr=away_abbr,
            home_seed=home_seed, away_seed=away_seed,
        )]

    raise ValueError(f"No round follows {last_name!r}")


def final_division_standings(season) -> dict[tuple[str, str], list[str]]:
    """Real final standings for every division -- (conference, division)
    -> team abbrs ranked 1st..4th -- using the SAME real tie-break chain
    as playoff division-winner seeding (Sec 7.3.A). Feeds
    schedule.py's `prior_standings` parameter for the next season's
    standings-based games (GDD Sec 5.1), replacing the bootstrap order
    schedule.py falls back to when no real prior season exists yet --
    see app/services/season_state.py's start_new_season()."""
    grouped: dict[str, dict[str, list[str]]] = {}
    for t in TEAMS:
        grouped.setdefault(t.conference, {}).setdefault(t.division, []).append(t.abbr)
    return {
        (conf, div): rank_teams(season, teams, _division_steps)
        for conf, divisions in grouped.items()
        for div, teams in divisions.items()
    }
