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


def _week_games_to_dict(schedule) -> list:
    return [
        [
            {
                "home_abbr": g.home_abbr,
                "away_abbr": g.away_abbr,
                "result": _result_to_dict(g.result),
            }
            for g in week
        ]
        for week in schedule
    ]


def season_to_dict(season) -> dict:
    return {
        "league_seed": season.league_seed,
        "current_week": season.current_week,
        "sfs": asdict(season.sfs),
        "user_team_abbr": season.user_team_abbr,
        "season_number": season.season_number,
        "playoffs": _bracket_to_dict(season.playoffs),
        "schedule": _week_games_to_dict(season.schedule),
        # R10 (GDD preseason): same real WeekGame/GameResult shape as the
        # regular schedule above -- a preseason game's box score is real
        # data (progression's usage nudge, Week-1 scouting/stats
        # backfill) and needs to survive a save/reload exactly like any
        # other simulated game.
        "preseason_schedule": _week_games_to_dict(getattr(season, "preseason_schedule", [])),
        # Offseason stage (None/"staff"/"resign", Brian's ask 2026-09-13)
        # -- must survive a save/reload same as everything else here, or
        # a server restart mid-offseason would silently forget the pause.
        "offseason_stage": getattr(season, "offseason_stage", None),
        "records": {
            abbr: asdict(rec) for abbr, rec in season.records.items()
        },
        # R16 Sec 5.2: the pending weekly poach gate, and the guard that
        # keeps re-clicking Sim Week from re-rolling this week's AI
        # poaching decisions -- both must survive a save/reload like
        # every other in-progress gate state here.
        "pending_poach": getattr(season, "pending_poach", None),
        "poaching_evaluated_through_week": getattr(season, "poaching_evaluated_through_week", 0),
    }


def _week_games_from_dict(raw_schedule, WeekGame) -> list:
    return [
        [
            WeekGame(
                home_abbr=g["home_abbr"],
                away_abbr=g["away_abbr"],
                result=_result_from_dict(g["result"]),
            )
            for g in week
        ]
        for week in raw_schedule
    ]


def season_from_dict(d: dict):
    # Imported lazily to avoid a circular import (season_state imports this module).
    from app.services.season_state import Season, WeekGame, TeamRecord
    from app.engine.score_fidelity import SFSState

    schedule = _week_games_from_dict(d["schedule"], WeekGame)
    # .get(...) fallback: a save file from before R10 (preseason) won't
    # have this key -- an existing franchise just has no preseason games
    # on record, not an error.
    preseason_schedule = _week_games_from_dict(d.get("preseason_schedule", []), WeekGame)
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
        preseason_schedule=preseason_schedule,
        # .get(...) fallback: a save file from before this offseason
        # staging existed won't have this key (or may still have the
        # old boolean "awaiting_resign" key from this feature's first,
        # single-stage cut) -- both treated as "not in the offseason".
        offseason_stage=d.get("offseason_stage") or ("resign" if d.get("awaiting_resign") else None),
        # .get(...) fallback: a save file from before R16 poaching existed
        # won't have these keys -- "no pending poach, nothing evaluated
        # yet" is the correct read for an old save either way.
        pending_poach=d.get("pending_poach"),
        poaching_evaluated_through_week=d.get("poaching_evaluated_through_week", 0),
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
