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

Deliberate scope decision: this archives SEASON-level totals (what a
player/team did in that one season), not a running CAREER-cumulative
total across all of a player's seasons. Building real career totals
means summing across every archived season a player appears in by
player_id (stable across seasons) rather than by (team_abbr, name) --
straightforward to add on top of this once a "Career" view actually
needs it, but this module doesn't do that aggregation itself.
"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.engine.awards import AwardCandidate, AwardsRace, season_awards
from app.engine.season_stats import SeasonPassingLine, SeasonRushingLine, SeasonReceivingLine, aggregate_season_stats

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

    record = SeasonRecord(
        season_number=season.season_number,
        team_results=team_results,
        champion_abbr=champion_abbr,
        afc_seeds=afc_seeds,
        nfc_seeds=nfc_seeds,
        awards=season_awards(season),
        passing_leaders=sorted(passing.values(), key=lambda l: -l.yards)[:15],
        rushing_leaders=sorted(rushing.values(), key=lambda l: -l.yards)[:15],
        receiving_leaders=sorted(receiving.values(), key=lambda l: -l.yards)[:15],
    )

    records = _load(path)
    records.append(_record_to_dict(record))
    _save(records, path)
    return record


def get_history(path: Path | None = None) -> list[SeasonRecord]:
    """All archived seasons, oldest first (matches append order)."""
    return [_record_from_dict(d) for d in _load(path)]
