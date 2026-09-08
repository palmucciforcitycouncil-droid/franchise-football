"""
League History: a permanent per-season archive (final standings, Super
Bowl champion + seeds, season Awards, and stat leaders), written once
by app/services/season_state.py's start_new_season() right before the
just-completed season's in-memory state is replaced by a fresh one.

Fills a real gap start_new_season() itself surfaced: app/engine/
season_stats.py's aggregate_season_stats() and Season.records only ever
see the CURRENT season -- once a new one starts, the old one's numbers
are gone unless archived first. This is the prerequisite HOF induction
logic and any future "Career" stats view were waiting on (see
HANDOFF.md's Known Gaps entry from the season-rollover session).

Persisted as JSON (data/saves/history.json, gitignored, same pattern as
save_service.py's season state), a plain list of season snapshots in
the order they were archived (oldest first).

Also builds real CAREER-cumulative stats and Hall of Fame induction on
top of the season archive (career_stats(), hall_of_fame() below).

Deliberate, disclosed interpretations:

- Career identity is (team_abbr, name), the SAME key season_stats.py/
  awards.py already use -- not the Player.player_id primary key. This
  project has no trade, free agency, or roster-movement system yet
  (see HANDOFF.md's Known Gaps), so a player's team_abbr never changes
  across their whole career here; (team_abbr, name) is therefore just
  as stable an identity as player_id would be, without requiring
  player_id to be threaded through the entire play-simulation pipeline
  (PlayEvent -> drive_sim.py -> box_score.py) for a system that has no
  roster movement to disambiguate anyway. Worth revisiting once a
  trade system exists and a player's team_abbr CAN change mid-career.
- archive_season() used to keep only the top-15 passing/rushing/
  receiving leaders per season (most players who touched the ball were
  silently dropped). Career totals need every player, not just
  leaders, so the top-15 cap is gone -- passing_leaders/rushing_leaders/
  receiving_leaders now hold every player from that season's full
  aggregate_season_stats(), still sorted by yards descending (index 0
  is still "the leader," matching how history.html already reads it).
- Hall of Fame induction criteria are NOT specified by any GDD source
  document (same situation as the MVP weight formula and DPOY's
  formula in awards.py). This module's own bar: a player becomes a HOF
  candidate at a position (QB/RB/WR-TE/DEF) once they have at least
  MIN_HOF_SEASONS archived seasons of real production AND a composite
  score clears HOF_SCORE_THRESHOLD. For QB/RB/WR-TE: 0.5*normalized
  career yards + 0.5*normalized career touchdowns (normalized within
  their own position's whole eligible pool, same technique awards.py
  uses per-season). For DEF: the SAME weighted composite awards.py's
  DPOY now uses (0.30 sacks + 0.30 interceptions + 0.15 TFL + 0.10 solo
  tackles + 0.10 forced fumbles + 0.05 passes defended, each normalized
  within the whole defensive candidate pool -- no positional split,
  matching how DPOY itself is position-agnostic), applied to CAREER
  totals instead of a single season's. Either way, AWARD_BONUS_PER_WIN
  is then added per MVP/OPOY/DPOY/ROY season actually WON (the season's
  #1 candidate, not a nomination). A threshold (not a fixed top-N) is
  deliberate: it lets the Hall be empty early in a league's history and
  grow into a real class of standouts as more seasons separate elite
  careers from average ones, rather than always forcing exactly N
  players in regardless of how the league has actually played out.
"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.engine.awards import AwardCandidate, AwardsRace, season_awards
from app.engine.season_stats import (
    SeasonPassingLine, SeasonRushingLine, SeasonReceivingLine, SeasonDefensiveLine,
    aggregate_season_stats, aggregate_season_defensive_stats,
)

DEFAULT_PATH = Path("data/saves/history.json")


@dataclass
class TeamSeasonResult:
    abbr: str
    location: str
    wins: int
    losses: int
    points_for: int
    points_against: int
    power_rating: float


@dataclass
class SeasonRecord:
    season_number: int
    team_results: list[TeamSeasonResult]
    champion_abbr: str | None
    afc_seeds: list[str] | None
    nfc_seeds: list[str] | None
    awards: AwardsRace
    passing_leaders: list[SeasonPassingLine]
    rushing_leaders: list[SeasonRushingLine]
    receiving_leaders: list[SeasonReceivingLine]
    defensive_leaders: list[SeasonDefensiveLine]


def _load(path: Path | None) -> list[dict]:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _save(records: list[dict], path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(records, indent=2), encoding="utf-8")


def _record_to_dict(record: SeasonRecord) -> dict:
    return {
        "season_number": record.season_number,
        "team_results": [asdict(t) for t in record.team_results],
        "champion_abbr": record.champion_abbr,
        "afc_seeds": record.afc_seeds,
        "nfc_seeds": record.nfc_seeds,
        "awards": {
            "mvp": [asdict(c) for c in record.awards.mvp],
            "opoy": [asdict(c) for c in record.awards.opoy],
            "dpoy": [asdict(c) for c in record.awards.dpoy],
            "roy": [asdict(c) for c in record.awards.roy],
        },
        "passing_leaders": [asdict(p) for p in record.passing_leaders],
        "rushing_leaders": [asdict(r) for r in record.rushing_leaders],
        "receiving_leaders": [asdict(r) for r in record.receiving_leaders],
        "defensive_leaders": [asdict(d) for d in record.defensive_leaders],
    }


def _record_from_dict(d: dict) -> SeasonRecord:
    return SeasonRecord(
        season_number=d["season_number"],
        team_results=[TeamSeasonResult(**t) for t in d["team_results"]],
        champion_abbr=d.get("champion_abbr"),
        afc_seeds=d.get("afc_seeds"),
        nfc_seeds=d.get("nfc_seeds"),
        awards=AwardsRace(
            mvp=[AwardCandidate(**c) for c in d["awards"]["mvp"]],
            opoy=[AwardCandidate(**c) for c in d["awards"]["opoy"]],
            dpoy=[AwardCandidate(**c) for c in d["awards"]["dpoy"]],
            roy=[AwardCandidate(**c) for c in d["awards"]["roy"]],
        ),
        passing_leaders=[SeasonPassingLine(**p) for p in d["passing_leaders"]],
        rushing_leaders=[SeasonRushingLine(**r) for r in d["rushing_leaders"]],
        receiving_leaders=[SeasonReceivingLine(**r) for r in d["receiving_leaders"]],
        # .get() with a [] default: a season archived before this field existed
        # shouldn't fail to load, just have no defensive leaders recorded.
        defensive_leaders=[SeasonDefensiveLine(**d_) for d_ in d.get("defensive_leaders", [])],
    )


def archive_season(season, path: Path | None = None) -> SeasonRecord:
    """Snapshots `season` (the caller -- season_state.start_new_season()
    -- is responsible for calling this on the just-completed season
    BEFORE replacing it with a fresh one) into a permanent SeasonRecord,
    appended to the history file. Safe to call on an incomplete season
    too (e.g. for a smoke test) -- champion_abbr/seeds are just None."""
    team_results = [
        TeamSeasonResult(
            abbr=r.abbr, location=r.location, wins=r.wins, losses=r.losses,
            points_for=r.points_for, points_against=r.points_against, power_rating=r.power_rating,
        )
        for r in season.records.values()
    ]
    champion_abbr = season.playoffs.champion_abbr if season.playoffs else None
    afc_seeds = season.playoffs.afc_seeds if season.playoffs else None
    nfc_seeds = season.playoffs.nfc_seeds if season.playoffs else None

    passing, rushing, receiving = aggregate_season_stats(season)
    defense = aggregate_season_defensive_stats(season)

    record = SeasonRecord(
        season_number=season.season_number,
        team_results=team_results,
        champion_abbr=champion_abbr,
        afc_seeds=afc_seeds,
        nfc_seeds=nfc_seeds,
        awards=season_awards(season),
        passing_leaders=sorted(passing.values(), key=lambda l: -l.yards),
        rushing_leaders=sorted(rushing.values(), key=lambda l: -l.yards),
        receiving_leaders=sorted(receiving.values(), key=lambda l: -l.yards),
        defensive_leaders=sorted(defense.values(), key=lambda l: -l.solo_tackles),
    )

    records = _load(path)
    records.append(_record_to_dict(record))
    _save(records, path)
    return record


def get_history(path: Path | None = None) -> list[SeasonRecord]:
    """All archived seasons, oldest first (matches append order)."""
    return [_record_from_dict(d) for d in _load(path)]


@dataclass
class CareerPassingLine:
    name: str
    team_abbr: str
    seasons: int = 0
    completions: int = 0
    attempts: int = 0
    yards: int = 0
    touchdowns: int = 0
    interceptions: int = 0


@dataclass
class CareerRushingLine:
    name: str
    team_abbr: str
    seasons: int = 0
    carries: int = 0
    yards: int = 0
    touchdowns: int = 0


@dataclass
class CareerReceivingLine:
    name: str
    team_abbr: str
    seasons: int = 0
    receptions: int = 0
    targets: int = 0
    yards: int = 0
    touchdowns: int = 0


@dataclass
class CareerDefensiveLine:
    name: str
    team_abbr: str
    seasons: int = 0
    solo_tackles: int = 0
    tackles_for_loss: int = 0
    sacks: int = 0
    interceptions: int = 0
    passes_defended: int = 0
    forced_fumbles: int = 0
    fumble_recoveries: int = 0


def career_stats(path: Path | None = None) -> tuple[dict, dict, dict, dict]:
    """Sums every archived season's full passing/rushing/receiving/
    defensive line for a player into a running career total, keyed by
    (team_abbr, name) -- see this module's docstring for why that key is
    safe here. Returns (passing, rushing, receiving, defense) dicts of
    (team_abbr, name) -> Career*Line. No truncation; callers slice
    however they need (hall_of_fame() below is one such caller)."""
    passing: dict[tuple[str, str], CareerPassingLine] = {}
    rushing: dict[tuple[str, str], CareerRushingLine] = {}
    receiving: dict[tuple[str, str], CareerReceivingLine] = {}
    defense: dict[tuple[str, str], CareerDefensiveLine] = {}

    for rec in get_history(path):
        for p in rec.passing_leaders:
            key = (p.team_abbr, p.name)
            line = passing.setdefault(key, CareerPassingLine(name=p.name, team_abbr=p.team_abbr))
            line.seasons += 1
            line.completions += p.completions
            line.attempts += p.attempts
            line.yards += p.yards
            line.touchdowns += p.touchdowns
            line.interceptions += p.interceptions
        for r in rec.rushing_leaders:
            key = (r.team_abbr, r.name)
            line = rushing.setdefault(key, CareerRushingLine(name=r.name, team_abbr=r.team_abbr))
            line.seasons += 1
            line.carries += r.carries
            line.yards += r.yards
            line.touchdowns += r.touchdowns
        for rc in rec.receiving_leaders:
            key = (rc.team_abbr, rc.name)
            line = receiving.setdefault(key, CareerReceivingLine(name=rc.name, team_abbr=rc.team_abbr))
            line.seasons += 1
            line.receptions += rc.receptions
            line.targets += rc.targets
            line.yards += rc.yards
            line.touchdowns += rc.touchdowns
        for dl in rec.defensive_leaders:
            key = (dl.team_abbr, dl.name)
            line = defense.setdefault(key, CareerDefensiveLine(name=dl.name, team_abbr=dl.team_abbr))
            line.seasons += 1
            line.solo_tackles += dl.solo_tackles
            line.tackles_for_loss += dl.tackles_for_loss
            line.sacks += dl.sacks
            line.interceptions += dl.interceptions
            line.passes_defended += dl.passes_defended
            line.forced_fumbles += dl.forced_fumbles
            line.fumble_recoveries += dl.fumble_recoveries

    return passing, rushing, receiving, defense


def _normalize(value: float, pool: list[float]) -> float:
    """Same technique as awards.py's own _normalize: min-max scale
    within a single position's eligible pool so raw yardage (which
    isn't on the same scale across positions) never gets compared
    across them."""
    if not pool:
        return 0.0
    lo, hi = min(pool), max(pool)
    return (value - lo) / (hi - lo) if hi > lo else 0.5


def _award_win_counts(history: list[SeasonRecord]) -> dict[tuple[str, str], int]:
    """(team_abbr, name) -> number of MVP/OPOY/DPOY/ROY seasons actually
    WON (the season's #1 candidate, not merely nominated) across every
    archived season."""
    counts: dict[tuple[str, str], int] = {}
    for rec in history:
        for pool in (rec.awards.mvp, rec.awards.opoy, rec.awards.dpoy, rec.awards.roy):
            if pool:
                winner = pool[0]
                key = (winner.team_abbr, winner.name)
                counts[key] = counts.get(key, 0) + 1
    return counts


MIN_HOF_SEASONS = 2
HOF_SCORE_THRESHOLD = 0.75
AWARD_BONUS_PER_WIN = 0.1


@dataclass
class HOFCandidate:
    name: str
    team_abbr: str
    position: str  # "QB" | "RB" | "WR/TE" | "DEF"
    seasons: int
    stat_line: str
    award_wins: int
    score: float


def hall_of_fame(path: Path | None = None) -> list[HOFCandidate]:
    """Real HOF induction over the real career archive -- see this
    module's docstring for the disclosed, GDD-underspecified induction
    formula (composite production score + award-win bonus, gated by
    MIN_HOF_SEASONS and HOF_SCORE_THRESHOLD). Returns every player who
    currently clears the bar, ranked highest score first; empty until a
    league has enough archived seasons to clear it."""
    history = get_history(path)
    passing, rushing, receiving, defense = career_stats(path)
    award_wins = _award_win_counts(history)

    candidates: list[HOFCandidate] = []

    def _induct(pool: dict, position: str, stat_fmt, score_fn):
        eligible = [(k, l) for k, l in pool.items() if l.seasons >= MIN_HOF_SEASONS]
        if not eligible:
            return
        production_fn = score_fn(eligible)
        for (abbr, name), line in eligible:
            production = production_fn(line)
            wins = award_wins.get((abbr, name), 0)
            score = min(1.0, production + AWARD_BONUS_PER_WIN * wins)
            if score >= HOF_SCORE_THRESHOLD:
                candidates.append(HOFCandidate(
                    name=name, team_abbr=abbr, position=position, seasons=line.seasons,
                    stat_line=stat_fmt(line), award_wins=wins, score=score,
                ))

    def _offensive_score_fn(eligible):
        yards_pool = [l.yards for _, l in eligible]
        td_pool = [l.touchdowns for _, l in eligible]
        return lambda l: 0.5 * _normalize(l.yards, yards_pool) + 0.5 * _normalize(l.touchdowns, td_pool)

    def _defensive_score_fn(eligible):
        sacks_pool = [l.sacks for _, l in eligible]
        ints_pool = [l.interceptions for _, l in eligible]
        tfl_pool = [l.tackles_for_loss for _, l in eligible]
        tkl_pool = [l.solo_tackles for _, l in eligible]
        ff_pool = [l.forced_fumbles for _, l in eligible]
        pd_pool = [l.passes_defended for _, l in eligible]
        return lambda l: (
            0.30 * _normalize(l.sacks, sacks_pool)
            + 0.30 * _normalize(l.interceptions, ints_pool)
            + 0.15 * _normalize(l.tackles_for_loss, tfl_pool)
            + 0.10 * _normalize(l.solo_tackles, tkl_pool)
            + 0.10 * _normalize(l.forced_fumbles, ff_pool)
            + 0.05 * _normalize(l.passes_defended, pd_pool)
        )

    _induct(passing, "QB", lambda l: f"{l.yards:,} career pass yds, {l.touchdowns} TD, {l.seasons} seasons", _offensive_score_fn)
    _induct(rushing, "RB", lambda l: f"{l.yards:,} career rush yds, {l.touchdowns} TD, {l.seasons} seasons", _offensive_score_fn)
    _induct(receiving, "WR/TE", lambda l: f"{l.yards:,} career rec yds, {l.touchdowns} TD, {l.seasons} seasons", _offensive_score_fn)
    _induct(defense, "DEF", lambda l: f"{l.solo_tackles} career tkl, {l.sacks} sacks, {l.interceptions} INT, {l.seasons} seasons", _defensive_score_fn)

    return sorted(candidates, key=lambda c: -c.score)
