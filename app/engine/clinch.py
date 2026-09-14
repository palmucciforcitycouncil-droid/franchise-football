"""
Clinch detection: division title, playoff berth, first-round bye.

Brian's ask, 2026-09-14: a small "x" next to a team that has clinched a
playoff spot and "*" once it has clinched the first-round bye, in every
Standings box -- and the Weekly Headlines' "clinches" stories must fire
only in the week the clinch actually happens (they used to repeat every
week, because the old check re-tested "is this team still clear?"
instead of "did this team just become clear?").

This league's format (app/engine/playoffs.py): 7 seeds per conference --
the 4 division winners are seeds 1-4, 3 wild cards are 5-7, and only the
#1 seed gets a bye.

The math is deliberately CONSERVATIVE: a mark is never shown unless it's
guaranteed. Two simplifications, both of which can only ever withhold a
mark (never award a false one):
- Any rival who can still reach a team's CURRENT win total is assumed to
  finish ahead of it (every tiebreaker goes against the team being
  tested -- the real chain in playoffs.py isn't decidable before the
  games are played).
- Rivals are assumed to be able to win out simultaneously, even when
  they still play each other (ignoring that one of them must lose those
  games). A late-season clinch can therefore show up a week later than
  a full combinatorial solver would show it, never earlier.

Once every regular-season game is played there's nothing left to be
conservative about: the real seeding (playoffs.seed_conference, with the
full tiebreak chain) decides the marks exactly.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.data.teams import TEAMS, TEAMS_BY_ABBR

PLAYOFF_SEEDS = 7
WILD_CARD_SLOTS = 3


@dataclass(frozen=True)
class ClinchStatus:
    division: bool = False
    berth: bool = False
    bye: bool = False

    @property
    def mark(self) -> str:
        """"*" for a clinched bye (which implies a berth), "x" for a
        clinched berth, "" otherwise -- the Standings-box legend's own
        two symbols."""
        if self.bye:
            return "*"
        if self.berth:
            return "x"
        return ""


def compute_clinches(wins: dict[str, int], remaining: dict[str, int]) -> dict[str, ClinchStatus]:
    """Pure core over plain dicts (every team in TEAMS must be present in
    both): `wins` so far and regular-season games still to play."""
    max_wins = {abbr: wins[abbr] + remaining[abbr] for abbr in wins}
    by_conf_div: dict[tuple[str, str], list[str]] = {}
    for t in TEAMS:
        by_conf_div.setdefault((t.conference, t.division), []).append(t.abbr)

    out: dict[str, ClinchStatus] = {}
    for t in TEAMS:
        abbr, floor = t.abbr, wins[t.abbr]
        conf_teams = [x.abbr for x in TEAMS if x.conference == t.conference and x.abbr != abbr]

        # A "threat" is any rival that can still finish level with or
        # above this team's worst case (losing out) -- see module docstring.
        def threats(teams: list[str]) -> int:
            return sum(1 for x in teams if x != abbr and max_wins[x] >= floor)

        own_division = by_conf_div[(t.conference, t.division)]
        division = threats(own_division) == 0

        if division:
            berth = True
        else:
            # Worst case: this team is a wild card. Each division sends its
            # best team to seeds 1-4; in a division with k threats that
            # winner is one of them, so k-1 threats spill into the wild-card
            # pool (0 if k == 0). The team is safe while at most 2 teams can
            # be ahead of it in that pool.
            pool_threats = 0
            for (conf, _div), members in by_conf_div.items():
                if conf != t.conference:
                    continue
                k = threats(members)
                pool_threats += max(k - 1, 0)
            berth = pool_threats <= WILD_CARD_SLOTS - 1

        bye = threats(conf_teams) == 0
        out[abbr] = ClinchStatus(division=division, berth=berth or bye, bye=bye)
    return out


def _remaining_games(season, through_week: int | None = None) -> dict[str, int]:
    """Unplayed regular-season games per team. `through_week` (1-indexed)
    treats every game AFTER that week as unplayed regardless of whether it
    has a result -- used to rebuild the standings as they stood before a
    given week."""
    remaining = {t.abbr: 0 for t in TEAMS}
    for week_idx, week in enumerate(season.schedule, start=1):
        for g in week:
            unplayed = g.result is None or (through_week is not None and week_idx > through_week)
            if unplayed:
                for abbr in (g.home_abbr, g.away_abbr):
                    if abbr in remaining:
                        remaining[abbr] += 1
    return remaining


def season_clinches(season) -> dict[str, ClinchStatus]:
    """Clinch status for every team as the season stands right now."""
    remaining = _remaining_games(season)
    if all(v == 0 for v in remaining.values()) and any(g.result is not None for w in season.schedule for g in w):
        # Every game is in: the real seeding (full tiebreak chain) is exact.
        from app.engine.playoffs import seed_conference
        out = {}
        for conf in ("AFC", "NFC"):
            seeds = seed_conference(season, conf)
            for i, abbr in enumerate(seeds):
                out[abbr] = ClinchStatus(division=i < 4, berth=True, bye=i == 0)
        return {t.abbr: out.get(t.abbr, ClinchStatus()) for t in TEAMS}
    wins = {t.abbr: season.records[t.abbr].wins for t in TEAMS}
    return compute_clinches(wins, remaining)


def clinches_before_week(season, week_num: int) -> dict[str, ClinchStatus]:
    """Clinch status as it stood BEFORE `week_num`'s games -- rebuilt from
    the real per-game results of weeks 1..week_num-1 (literal scores are
    not used for W/L: season_state credits a tied score to the home team,
    and season.records is what the standings show, so this mirrors that
    same convention via GameResult.winner)."""
    wins = {t.abbr: 0 for t in TEAMS}
    for week in season.schedule[: max(week_num - 1, 0)]:
        for g in week:
            if g.result is None:
                continue
            winner = g.home_abbr if g.result.winner == "home" else g.away_abbr
            if winner in wins:
                wins[winner] += 1
    return compute_clinches(wins, _remaining_games(season, through_week=week_num - 1))


def clinch_marks(season) -> dict[str, str]:
    """{abbr: "x" | "*" | ""} for the Standings boxes' templates."""
    return {abbr: status.mark for abbr, status in season_clinches(season).items()}


def division_label(abbr: str) -> str:
    t = TEAMS_BY_ABBR[abbr]
    return f"{t.conference} {t.division}"
