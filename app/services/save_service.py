"""
JSON save/load for Season state (GDD Part 1 Sec 8: "JSON-based save/export").

Serializes everything needed to reconstruct a Season exactly: schedule,
every simulated game's result (score, drive-by-drive events, totals),
records, current week, and the seed that produced it all. A save file
alone is enough to resume a season -- nothing else is derived at runtime.
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import asdict

from app.engine.game_state import DriveEvent, GameResult, PlayEvent
from app.engine.game_sim import TeamTotals
from app.engine.playoffs import PlayoffBracket, PlayoffMatchup

DEFAULT_SAVE_PATH = Path("data/saves/current_season.json")


def _totals_to_dict(totals: TeamTotals | None) -> dict | None:
    if totals is None:
        return None
    return asdict(totals)


def _totals_from_dict(d: dict | None) -> TeamTotals | None:
    if d is None:
        return None
    return TeamTotals(**d)


def _result_to_dict(result: GameResult | None) -> dict | None:
    if result is None:
        return None
    return {
        "home_score": result.home_score,
        "away_score": result.away_score,
        "winner": result.winner,
        "events": [asdict(e) for e in result.events],
        "plays": [asdict(p) for p in result.plays],
        "home_totals": _totals_to_dict(getattr(result, "home_totals", None)),
        "away_totals": _totals_to_dict(getattr(result, "away_totals", None)),
    }


def _result_from_dict(d: dict | None) -> GameResult | None:
    if d is None:
        return None
    result = GameResult(
        home_score=d["home_score"],
        away_score=d["away_score"],
        winner=d["winner"],
        events=[DriveEvent(**e) for e in d["events"]],
        plays=[PlayEvent(**p) for p in d.get("plays", [])],
    )
    result.home_totals = _totals_from_dict(d.get("home_totals"))  # type: ignore[attr-defined]
    result.away_totals = _totals_from_dict(d.get("away_totals"))  # type: ignore[attr-defined]
    return result


def _matchup_to_dict(m: PlayoffMatchup) -> dict:
    return {
        "round_name": m.round_name,
        "conference": m.conference,
        "home_abbr": m.home_abbr,
        "away_abbr": m.away_abbr,
        "home_seed": m.home_seed,
        "away_seed": m.away_seed,
        "result": _result_to_dict(m.result),
    }


def _matchup_from_dict(d: dict) -> PlayoffMatchup:
    return PlayoffMatchup(
        round_name=d["round_name"],
        conference=d["conference"],
        home_abbr=d["home_abbr"],
        away_abbr=d["away_abbr"],
        home_seed=d["home_seed"],
        away_seed=d["away_seed"],
        result=_result_from_dict(d["result"]),
    )


def _bracket_to_dict(bracket: PlayoffBracket | None) -> dict | None:
    if bracket is None:
        return None
    return {
        "afc_seeds": bracket.afc_seeds,
        "nfc_seeds": bracket.nfc_seeds,
        "rounds": [[_matchup_to_dict(m) for m in round_] for round_ in bracket.rounds],
    }


def _bracket_from_dict(d: dict | None) -> PlayoffBracket | None:
    if d is None:
        return None
    return PlayoffBracket(
        afc_seeds=d["afc_seeds"],
        nfc_seeds=d["nfc_seeds"],
        rounds=[[_matchup_from_dict(m) for m in round_] for round_ in d["rounds"]],
    )


def season_to_dict(season) -> dict:
    return {
        "league_seed": season.league_seed,
        "current_week": season.current_week,
        "sfs": asdict(season.sfs),
        "user_team_abbr": season.user_team_abbr,
        "season_number": season.season_number,
        "playoffs": _bracket_to_dict(season.playoffs),
        "schedule": [
            [
                {
                    "home_abbr": g.home_abbr,
                    "away_abbr": g.away_abbr,
                    "result": _result_to_dict(g.result),
                }
                for g in week
            ]
            for week in season.schedule
        ],
        "records": {
            abbr: asdict(rec) for abbr, rec in season.records.items()
        },
    }


def season_from_dict(d: dict):
    # Imported lazily to avoid a circular import (season_state imports this module).
    from app.services.season_state import Season, WeekGame, TeamRecord
    from app.engine.score_fidelity import SFSState

    schedule = [
        [
            WeekGame(
                home_abbr=g["home_abbr"],
                away_abbr=g["away_abbr"],
                result=_result_from_dict(g["result"]),
            )
            for g in week
        ]
        for week in d["schedule"]
    ]
    records = {abbr: TeamRecord(**rec) for abbr, rec in d["records"].items()}
    # .get(...) with a fresh-default fallback: a save file from before the
    # Score Fidelity System existed won't have "sfs" (or "power_rating" on
    # each record, but TeamRecord's own field default covers that case).
    sfs = SFSState(**d["sfs"]) if "sfs" in d else SFSState()
    # .get(...) fallback: a save file from before user-team selection existed
    # (GDD Sec 10.1) won't have this key -- treated as "no team chosen yet",
    # not an error.
    return Season(
        league_seed=d["league_seed"],
        schedule=schedule,
        records=records,
        current_week=d["current_week"],
        sfs=sfs,
        user_team_abbr=d.get("user_team_abbr"),
        playoffs=_bracket_from_dict(d.get("playoffs")),
        season_number=d.get("season_number", 0),
    )


def save_season(season, path: Path | None = None) -> None:
    # Resolved at call time (not as a default-arg value) so tests can redirect
    # DEFAULT_SAVE_PATH at the module level without it being baked in at import.
    p = path if path is not None else DEFAULT_SAVE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(season_to_dict(season), indent=2), encoding="utf-8")


def load_season(path: Path | None = None):
    p = path if path is not None else DEFAULT_SAVE_PATH
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    return season_from_dict(data)
