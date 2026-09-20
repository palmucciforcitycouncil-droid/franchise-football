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
  DPOY now uses (0.27 sacks + 0.27 interceptions + 0.13 TFL + 0.09 solo
  tackles + 0.09 forced fumbles + 0.05 passes defended + 0.10 defensive
  touchdowns, each normalized within the whole defensive candidate pool
  -- no positional split,
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
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

from app.engine.awards import AwardCandidate, CoachAwardCandidate, AwardsRace, season_awards
from app.engine.playoffs import final_division_standings
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
    # Added 2026-09-11 for the Team History box (ROADMAP.md, History/HOF
    # merge): this team's real final rank (1st..4th) within its own
    # division that season, via playoffs.final_division_standings() --
    # the SAME tie-break chain division-winner seeding uses, not a naive
    # W-L sort. 0 for archives written before this field existed (real
    # NFL-history imports included -- see scripts/import_nfl_history.py,
    # which has no real bracket data to derive this from); the template
    # treats 0 as "unknown", not "4th".
    division_rank: int = 0
    # Added 2026-09-19 alongside the regular-season ties fix
    # (season_state.TeamRecord.ties): 0 for every archive written before
    # ties existed (real NFL-history imports included -- a genuine tie
    # simply never happened in this engine before now, so 0 there is the
    # real number, not a placeholder).
    ties: int = 0


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
    # Added 2026-09-11 for the History/HOF merge (ROADMAP.md): real data
    # this project already had (season.playoffs.rounds' CONF/SB matchups,
    # live at archive_season() time) but never archived -- closes the
    # "runner-up/final score not archived" gap hof.html's Super Bowl
    # History table used to disclose. All None for archives written
    # before this field existed, or for a season with no playoffs object
    # (e.g. an incomplete-season smoke-test archive) -- NOT fabricated.
    afc_champion_abbr: str | None = None
    nfc_champion_abbr: str | None = None
    super_bowl_home_abbr: str | None = None
    super_bowl_away_abbr: str | None = None
    super_bowl_home_score: int | None = None
    super_bowl_away_score: int | None = None


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
            # Coach of the Year (GDD Sec 7.4.6) -- archived from the
            # season this coach actually won it in, since a coach's
            # ratings and team change afterward and the award shouldn't.
            "coty": [asdict(c) for c in record.awards.coty],
        },
        "passing_leaders": [asdict(p) for p in record.passing_leaders],
        "rushing_leaders": [asdict(r) for r in record.rushing_leaders],
        "receiving_leaders": [asdict(r) for r in record.receiving_leaders],
        "defensive_leaders": [asdict(d) for d in record.defensive_leaders],
        "afc_champion_abbr": record.afc_champion_abbr,
        "nfc_champion_abbr": record.nfc_champion_abbr,
        "super_bowl_home_abbr": record.super_bowl_home_abbr,
        "super_bowl_away_abbr": record.super_bowl_away_abbr,
        "super_bowl_home_score": record.super_bowl_home_score,
        "super_bowl_away_score": record.super_bowl_away_score,
    }


def _record_from_dict(d: dict) -> SeasonRecord:
    return SeasonRecord(
        season_number=d["season_number"],
        team_results=[TeamSeasonResult(**{"division_rank": 0, "ties": 0, **t}) for t in d["team_results"]],
        champion_abbr=d.get("champion_abbr"),
        afc_seeds=d.get("afc_seeds"),
        nfc_seeds=d.get("nfc_seeds"),
        awards=AwardsRace(
            mvp=[AwardCandidate(**c) for c in d["awards"]["mvp"]],
            opoy=[AwardCandidate(**c) for c in d["awards"]["opoy"]],
            dpoy=[AwardCandidate(**c) for c in d["awards"]["dpoy"]],
            roy=[AwardCandidate(**c) for c in d["awards"]["roy"]],
            # .get(), not [] -- every season archived before COTY
            # existed has no "coty" key at all, and must keep loading.
            coty=[CoachAwardCandidate(**c) for c in d["awards"].get("coty", [])],
        ),
        passing_leaders=[SeasonPassingLine(**p) for p in d["passing_leaders"]],
        rushing_leaders=[SeasonRushingLine(**r) for r in d["rushing_leaders"]],
        receiving_leaders=[SeasonReceivingLine(**r) for r in d["receiving_leaders"]],
        # .get() with a [] default: a season archived before this field existed
        # shouldn't fail to load, just have no defensive leaders recorded.
        defensive_leaders=[SeasonDefensiveLine(**d_) for d_ in d.get("defensive_leaders", [])],
        afc_champion_abbr=d.get("afc_champion_abbr"),
        nfc_champion_abbr=d.get("nfc_champion_abbr"),
        super_bowl_home_abbr=d.get("super_bowl_home_abbr"),
        super_bowl_away_abbr=d.get("super_bowl_away_abbr"),
        super_bowl_home_score=d.get("super_bowl_home_score"),
        super_bowl_away_score=d.get("super_bowl_away_score"),
    )


def _awards_for_archive(season) -> AwardsRace:
    """The season's FROZEN final awards (app/services/honors_store.py,
    decided the moment the regular season ended) when they exist, so
    League History always matches what the Awards page announced; a live
    recomputation otherwise (an incomplete smoke-test season, or one that
    predates season honors). Top 5 per award, the archive's long-standing
    depth -- the full top 10 stays in honors_store."""
    from app.services import honors_store

    final = honors_store.get_final_awards(season.season_number)
    if not final:
        return season_awards(season)

    def players(key: str) -> list[AwardCandidate]:
        return [AwardCandidate(name=c["name"], team_abbr=c["team_abbr"], position=c["position"],
                               stat_line=c["stat_line"], score=c["score"]) for c in final.get(key, [])[:5]]

    return AwardsRace(
        mvp=players("mvp"), opoy=players("opoy"), dpoy=players("dpoy"), roy=players("roy"),
        coty=[CoachAwardCandidate(**{k: c[k] for k in ("coach_id", "name", "team_abbr", "record", "stat_line", "score")})
              for c in final.get("coty", [])[:5]],
    )


def archive_season(season, path: Path | None = None) -> SeasonRecord:
    """Snapshots `season` (the caller -- season_state.start_new_season()
    -- is responsible for calling this on the just-completed season
    BEFORE replacing it with a fresh one) into a permanent SeasonRecord,
    appended to the history file. Safe to call on an incomplete season
    too (e.g. for a smoke test) -- champion_abbr/seeds are just None."""
    # Real per-team division rank (1st..4th), same tie-break chain
    # division-winner seeding already uses -- not a naive W-L sort.
    # Guarded the same way champion_abbr/seeds below are: only real
    # when a completed `season.playoffs` bracket exists.
    division_rank_by_abbr: dict[str, int] = {}
    if season.playoffs:
        for ranked_abbrs in final_division_standings(season).values():
            for i, abbr in enumerate(ranked_abbrs, start=1):
                division_rank_by_abbr[abbr] = i

    team_results = [
        TeamSeasonResult(
            abbr=r.abbr, location=r.location, wins=r.wins, losses=r.losses,
            points_for=r.points_for, points_against=r.points_against, power_rating=r.power_rating,
            division_rank=division_rank_by_abbr.get(r.abbr, 0),
            ties=getattr(r, "ties", 0),
        )
        for r in season.records.values()
    ]
    champion_abbr = season.playoffs.champion_abbr if season.playoffs else None
    afc_seeds = season.playoffs.afc_seeds if season.playoffs else None
    nfc_seeds = season.playoffs.nfc_seeds if season.playoffs else None

    # Real AFC/NFC conference champions + the real Super Bowl matchup
    # (both teams + final score) -- both already live on
    # season.playoffs.rounds at archive time, just never read before
    # this. Closes the "runner-up/final score not archived" disclosed
    # gap hof.html's old Super Bowl History table carried. Still no
    # quarter-by-quarter (this engine has no clock/quarter model
    # anywhere, same disclosed gap as the Dashboard's Box Score box). The
    # Super Bowl MVP and dated coach/player titles live in
    # app/services/honors_store.py (2026-09-14), not in this archive.
    afc_champion_abbr = nfc_champion_abbr = None
    sb_home_abbr = sb_away_abbr = None
    sb_home_score = sb_away_score = None
    if season.playoffs and season.playoffs.is_complete:
        all_matchups = [m for round_ in season.playoffs.rounds for m in round_]
        afc_conf = next((m for m in all_matchups if m.round_name == "CONF" and m.conference == "AFC"), None)
        nfc_conf = next((m for m in all_matchups if m.round_name == "CONF" and m.conference == "NFC"), None)
        afc_champion_abbr = afc_conf.winner_abbr if afc_conf else None
        nfc_champion_abbr = nfc_conf.winner_abbr if nfc_conf else None
        sb = next((m for m in all_matchups if m.round_name == "SB"), None)
        if sb is not None:
            sb_home_abbr, sb_away_abbr = sb.home_abbr, sb.away_abbr
            if sb.result is not None:
                sb_home_score, sb_away_score = sb.result.home_score, sb.result.away_score

    passing, rushing, receiving = aggregate_season_stats(season)
    defense = aggregate_season_defensive_stats(season)

    record = SeasonRecord(
        season_number=season.season_number,
        team_results=team_results,
        champion_abbr=champion_abbr,
        afc_seeds=afc_seeds,
        nfc_seeds=nfc_seeds,
        awards=_awards_for_archive(season),
        passing_leaders=sorted(passing.values(), key=lambda l: -l.yards),
        rushing_leaders=sorted(rushing.values(), key=lambda l: -l.yards),
        receiving_leaders=sorted(receiving.values(), key=lambda l: -l.yards),
        defensive_leaders=sorted(defense.values(), key=lambda l: -l.solo_tackles),
        afc_champion_abbr=afc_champion_abbr,
        nfc_champion_abbr=nfc_champion_abbr,
        super_bowl_home_abbr=sb_home_abbr,
        super_bowl_away_abbr=sb_away_abbr,
        super_bowl_home_score=sb_home_score,
        super_bowl_away_score=sb_away_score,
    )

    records = _load(path)
    records.append(_record_to_dict(record))
    _save(records, path)
    return record


def get_history(path: Path | None = None) -> list[SeasonRecord]:
    """All archived seasons, oldest first (matches append order). A thin
    wrapper resolving `path` before handing off to the cached
    implementation below -- same reasoning as career_stats()'s own
    wrapper just below (never cache on a raw `None` default, or tests
    redirecting DEFAULT_PATH would collide on one shared cache key)."""
    return _get_history_cached(path if path is not None else DEFAULT_PATH)


@lru_cache(maxsize=32)
def _get_history_cached(path: Path) -> list[SeasonRecord]:
    """Real perf fix found live while verifying ROADMAP.md Sec2d-B item 11:
    history.json is a real ~13.5MB file (24 archived real/simulated
    seasons) -- reading + json.loads + reconstructing every SeasonRecord
    dataclass from it costs ~0.4s per call, and season_by_season_stats()
    (the Player Card Stats tab's year-by-year table) called this with
    zero caching of its own on every single player-card render. The
    Dashboard's new Top Performers box renders up to 100 player-card
    links in one request, which is what actually exposed this (a 46s+
    real Dashboard load) -- not something item 11 itself directly added.
    Same lru_cache-plus-explicit-clear pattern career_stats() already
    uses below; see clear_career_stats_cache(), extended to also clear
    this cache at the same call site (right after archive_season()/
    append_season_record() add a new season to this file)."""
    return [_record_from_dict(d) for d in _load(path)]


def append_season_record(record: SeasonRecord, path: Path | None = None) -> None:
    """Appends an already-built SeasonRecord directly, bypassing
    archive_season()'s live-Season-object requirement -- for a caller
    that already has real data in this exact shape (e.g. scripts/
    import_nfl_history.py building SeasonRecords from real NFL stats,
    not a simulated Season). Same append-oldest-first ordering as
    archive_season(); the caller is responsible for calling this in the
    order the records should appear."""
    records = _load(path)
    records.append(_record_to_dict(record))
    _save(records, path)


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
    sacks_taken: int = 0  # Player Card season-by-season redesign: sums SeasonPassingLine.sacks_taken (M13)


@dataclass
class CareerRushingLine:
    name: str
    team_abbr: str
    seasons: int = 0
    carries: int = 0
    yards: int = 0
    touchdowns: int = 0
    fumbles_lost: int = 0  # sums SeasonRushingLine.fumbles_lost (M13)


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
    defensive_touchdowns: int = 0


def career_stats(path: Path | None = None) -> tuple[dict, dict, dict, dict]:
    """Sums every archived season's full passing/rushing/receiving/
    defensive line for a player into a running career total, keyed by
    (team_abbr, name) -- see this module's docstring for why that key is
    safe here. Returns (passing, rushing, receiving, defense) dicts of
    (team_abbr, name) -> Career*Line. No truncation; callers slice
    however they need (hall_of_fame() below is one such caller).

    A thin wrapper that resolves `path` to a concrete Path (never None)
    before handing off to the cached implementation below -- caching on
    the raw `path=None` default directly would key every default-path
    call the same regardless of what DEFAULT_PATH actually points to at
    call time, which tests exploit deliberately (many redirect
    history_store.DEFAULT_PATH to an isolated file and then call
    career_stats() with no args) and would otherwise silently serve one
    test's stale cached totals to the next."""
    return _career_stats_cached(path if path is not None else DEFAULT_PATH)


@lru_cache(maxsize=32)
def _career_stats_cached(path: Path) -> tuple[dict, dict, dict, dict]:
    """The real implementation, cached (M6: Player Card Stats tab) -- a
    real 24-real-season history file takes ~230ms to parse, and the
    Player Card now calls career_stats() once per player-card render
    (roster.html alone renders one per player on a team), so an uncached
    call here would make a single Roster page load take tens of
    seconds. Same lru_cache-plus-explicit-clear pattern depth_chart.py's
    get_offensive_starters/get_defensive_starters already use; see
    clear_career_stats_cache() below, invoked by
    season_state.start_new_season() right after archive_season() writes
    a new season into this same file."""
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
            line.sacks_taken += p.sacks_taken
        for r in rec.rushing_leaders:
            key = (r.team_abbr, r.name)
            line = rushing.setdefault(key, CareerRushingLine(name=r.name, team_abbr=r.team_abbr))
            line.seasons += 1
            line.carries += r.carries
            line.yards += r.yards
            line.touchdowns += r.touchdowns
            line.fumbles_lost += r.fumbles_lost
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
            line.defensive_touchdowns += dl.defensive_touchdowns

    return passing, rushing, receiving, defense


def season_by_season_stats(team_abbr: str, name: str, path: Path | None = None) -> dict[str, list]:
    """Real per-SEASON (not summed) Passing/Rushing/Receiving/Defense
    lines for one player -- Brian's own request: a Madden-style year-
    by-year table on the Player Card's Stats tab, not just one career-
    cumulative total (career_stats() above still covers that, unchanged,
    for the Career summary row the UI appends after these).

    Not a new aggregation: every archived SeasonRecord's passing_leaders/
    etc. lists ALREADY hold that player's full real season line (despite
    the "leaders" name, these cover every player who touched the ball
    that season -- see aggregate_season_stats()'s own docstring) -- this
    just looks the player up in each season instead of summing across
    all of them. Most-recent-season first, matching how a Madden career
    stat table reads. Doesn't include the CURRENT in-progress season --
    same reasoning career_stats() already documents (that's a genuinely
    different, not-yet-final number); main.py's own caller adds that
    separately from the live, not-yet-archived Season."""
    passing: list[dict] = []
    rushing: list[dict] = []
    receiving: list[dict] = []
    defense: list[dict] = []
    for rec in get_history(path):
        p = next((x for x in rec.passing_leaders if x.name == name and x.team_abbr == team_abbr), None)
        if p:
            passing.append({"season_number": rec.season_number, **asdict(p)})
        r = next((x for x in rec.rushing_leaders if x.name == name and x.team_abbr == team_abbr), None)
        if r:
            rushing.append({"season_number": rec.season_number, **asdict(r)})
        rc = next((x for x in rec.receiving_leaders if x.name == name and x.team_abbr == team_abbr), None)
        if rc:
            receiving.append({"season_number": rec.season_number, **asdict(rc)})
        d = next((x for x in rec.defensive_leaders if x.name == name and x.team_abbr == team_abbr), None)
        if d:
            defense.append({"season_number": rec.season_number, **asdict(d)})
    return {
        "passing": list(reversed(passing)),
        "rushing": list(reversed(rushing)),
        "receiving": list(reversed(receiving)),
        "defense": list(reversed(defense)),
    }


def clear_career_stats_cache() -> None:
    """Call right after this module's own history file gains a new
    season (archive_season()/append_season_record()) -- otherwise
    career_stats()'s lru_cache would keep serving the pre-archive
    totals for the rest of the process's life. Also clears
    get_history()'s own cache (added alongside career_stats()'s
    existing one, ROADMAP.md Sec2d-B item 11's perf fix) for the same
    reason -- both read the same underlying file and both need to see
    a just-added season immediately."""
    _career_stats_cached.cache_clear()
    _get_history_cached.cache_clear()


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
    # M14 correction (real source: HOFPage.tsx): the structured per-
    # category stat table member cards show, instead of only the single
    # flattened `stat_line` summary -- (label, value) pairs in display
    # order, built from the same real Career*Line this candidate was
    # scored from. Induction year is NOT included here and stays a
    # disclosed gap: deriving it precisely would mean re-running
    # hall_of_fame() over every prior truncated history to find the
    # first season each member's score cleared HOF_SCORE_THRESHOLD (the
    # same technique _hof_new_inductee_keys() already uses for ONE
    # season), which is real but non-trivial work this chunk didn't
    # scope -- not something to fabricate a placeholder year for.
    stats: list[tuple[str, str]] = field(default_factory=list)


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

    def _induct(pool: dict, position: str, stat_fmt, score_fn, stats_fn):
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
                    stats=stats_fn(line),
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
        td_pool = [l.defensive_touchdowns for _, l in eligible]
        return lambda l: (
            0.27 * _normalize(l.sacks, sacks_pool)
            + 0.27 * _normalize(l.interceptions, ints_pool)
            + 0.13 * _normalize(l.tackles_for_loss, tfl_pool)
            + 0.09 * _normalize(l.solo_tackles, tkl_pool)
            + 0.09 * _normalize(l.forced_fumbles, ff_pool)
            + 0.05 * _normalize(l.passes_defended, pd_pool)
            + 0.10 * _normalize(l.defensive_touchdowns, td_pool)
        )

    _induct(
        passing, "QB", lambda l: f"{l.yards:,} career pass yds, {l.touchdowns} TD, {l.seasons} seasons", _offensive_score_fn,
        lambda l: [
            ("Completions", f"{l.completions:,}"), ("Attempts", f"{l.attempts:,}"),
            ("Passing Yards", f"{l.yards:,}"), ("TDs", f"{l.touchdowns:,}"), ("INTs", f"{l.interceptions:,}"),
        ],
    )
    _induct(
        rushing, "RB", lambda l: f"{l.yards:,} career rush yds, {l.touchdowns} TD, {l.seasons} seasons", _offensive_score_fn,
        lambda l: [("Carries", f"{l.carries:,}"), ("Rushing Yards", f"{l.yards:,}"), ("TDs", f"{l.touchdowns:,}")],
    )
    _induct(
        receiving, "WR/TE", lambda l: f"{l.yards:,} career rec yds, {l.touchdowns} TD, {l.seasons} seasons", _offensive_score_fn,
        lambda l: [
            ("Receptions", f"{l.receptions:,}"), ("Targets", f"{l.targets:,}"),
            ("Receiving Yards", f"{l.yards:,}"), ("TDs", f"{l.touchdowns:,}"),
        ],
    )
    _induct(
        defense, "DEF", lambda l: f"{l.solo_tackles} career tkl, {l.sacks} sacks, {l.interceptions} INT, {l.seasons} seasons", _defensive_score_fn,
        lambda l: [
            ("Solo Tackles", f"{l.solo_tackles:,}"), ("TFL", f"{l.tackles_for_loss:,}"), ("Sacks", f"{l.sacks:,}"),
            ("INTs", f"{l.interceptions:,}"), ("Forced Fumbles", f"{l.forced_fumbles:,}"), ("Def. TDs", f"{l.defensive_touchdowns:,}"),
        ],
    )

    return sorted(candidates, key=lambda c: -c.score)
