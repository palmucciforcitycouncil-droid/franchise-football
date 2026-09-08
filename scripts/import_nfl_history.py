"""
Seeds League History (and, through it, real career-cumulative stats +
Hall of Fame induction) with REAL NFL data: real team standings, real
Super Bowl results, and real per-player season stat lines for the
modern 32-team era (2002-present).

Data source: nflverse, via the `nflreadpy` Python package (pip install
nflreadpy). Confirmed CC-BY 4.0 licensed -- free to reuse with
attribution -- as of this script being written (2026-09). Pulls real
schedules/scores (`load_schedules`), real per-player season stats
(`load_player_stats`), and real roster/experience data for rookie
determination (`load_rosters`).

Team abbreviation mapping: nflverse uses the historical abbreviation a
franchise played under AT THE TIME (STL/OAK/SD for the Rams/Raiders/
Chargers before their respective relocations), while this engine's own
32 teams (app/data/teams.py) use each franchise's CURRENT abbreviation
throughout. TEAM_ABBR_MAP below normalizes nflverse's abbreviations to
this engine's -- confirmed empirically (see this script's own dev
history) that this produces an exact 32-team match with no leftover
extras/missing teams for every season from 2002 onward, which is why
2002 is FIRST_SEASON: the modern 32-team NFL era began that year
(Houston Texans expansion), so every earlier season would need
additional franchise-relocation/expansion handling this script doesn't
attempt.

Deliberate, disclosed scope decisions:
- No real division/conference playoff SEEDS or bracket -- champion_abbr
  and the real Super Bowl score ARE imported (straightforward: one game,
  one real winner), but reconstructing who actually made the playoffs
  at what seed needs the GDD's full real tie-breaker chain applied to
  real historical standings, which is a substantial undertaking on its
  own and out of scope for this pass. afc_seeds/nfc_seeds are left None
  for every imported season, same as this engine already renders for
  an incomplete/no-playoffs season.
- Real MVP/OPOY/DPOY/ROY are NOT the actual real-world AP award
  winners -- they're computed by THIS ENGINE'S OWN formula
  (app/engine/awards.py's offensive_candidates_from_stats/
  defensive_candidates_from_stats/mvp_from_candidates, the exact same
  pure functions a live simulated season's Awards Race uses) applied to
  the real imported season stats. A disclosed, deliberate choice: using
  the real official AP winners would need a second real data source
  (nflverse doesn't publish awards) and would be inconsistent with the
  "one continuous timeline" design (a simulated season's awards are
  always computed this way, not looked up) -- so real seasons compute
  their awards the identical way for consistency, not because the real
  official winners are unknowable.
- No real Team Power Rating history exists to import (this engine's
  own Elo system, app/engine/power_rating.py, has no real-world
  equivalent) -- every imported season's TeamSeasonResult.power_rating
  is the same 1500.0 baseline every fresh simulated team also starts
  at, not a real historical rating.
- HOF induction for real players is NOT separately seeded from a real
  Hall of Fame inductee list (e.g. Wikipedia's) -- real players whose
  CAREERS fall substantially within the imported 2002-2025 window will
  be evaluated (and, if they clear the bar, inducted) by this engine's
  own existing hall_of_fame() formula automatically, once their real
  season stats are archived here, the same as any simulated player.
  This deliberately does NOT attempt to seed the full real ~370-member
  Hall of Fame (most of whom played mostly or entirely before 2002, or
  are coaches/contributors/O-line with no stat-based formula this
  engine could evaluate them by even with real data) -- a real, bounded
  scope, not the complete historical record.

Usage:
    .venv/Scripts/python.exe scripts/import_nfl_history.py
    .venv/Scripts/python.exe scripts/import_nfl_history.py --first-season 2015 --last-season 2020
    .venv/Scripts/python.exe scripts/import_nfl_history.py --dry-run
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import nflreadpy as nfl

from app.services import history_store
from app.services.history_store import SeasonRecord, TeamSeasonResult
from app.engine.season_stats import SeasonPassingLine, SeasonRushingLine, SeasonReceivingLine, SeasonDefensiveLine
from app.engine.awards import (
    AwardsRace, offensive_candidates_from_stats, defensive_candidates_from_stats, mvp_from_candidates,
)
from app.data.teams import TEAMS

FIRST_SEASON = 2002
LAST_SEASON = 2025  # last real season with a completed Super Bowl as of this script being written (2026-09)

TEAM_ABBR_MAP = {"LA": "LAR", "OAK": "LV", "SD": "LAC", "STL": "LAR"}
MY_ABBRS = {t.abbr for t in TEAMS}
LOCATION_BY_ABBR = {t.abbr: t.location for t in TEAMS}
DEFAULT_POWER_RATING = 1500.0  # this engine's own Elo baseline -- no real historical rating exists to import


def _map_abbr(abbr: str) -> str:
    return TEAM_ABBR_MAP.get(abbr, abbr)


def _real_standings(schedules) -> dict[str, TeamSeasonResult]:
    """Real regular-season wins/losses/points, aggregated from real game
    scores -- one TeamSeasonResult per team, same shape archive_season()
    already produces for a simulated season."""
    reg = schedules.filter(schedules["game_type"] == "REG")
    records: dict[str, TeamSeasonResult] = {
        abbr: TeamSeasonResult(abbr=abbr, location=LOCATION_BY_ABBR[abbr], wins=0, losses=0, points_for=0, points_against=0, power_rating=DEFAULT_POWER_RATING)
        for abbr in MY_ABBRS
    }
    for row in reg.iter_rows(named=True):
        home = _map_abbr(row["home_team"])
        away = _map_abbr(row["away_team"])
        hs, aws = row["home_score"], row["away_score"]
        if hs is None or aws is None:
            continue  # an unplayed/postponed game -- shouldn't happen for a real completed season, skip defensively
        if home in records:
            records[home].points_for += hs
            records[home].points_against += aws
            if hs > aws:
                records[home].wins += 1
            elif hs < aws:
                records[home].losses += 1
        if away in records:
            records[away].points_for += aws
            records[away].points_against += hs
            if aws > hs:
                records[away].wins += 1
            elif aws < hs:
                records[away].losses += 1
    return records


def _real_champion(schedules) -> str | None:
    sb = schedules.filter(schedules["game_type"] == "SB")
    if sb.height == 0:
        return None
    row = sb.row(0, named=True)
    home, away = _map_abbr(row["home_team"]), _map_abbr(row["away_team"])
    return home if row["home_score"] > row["away_score"] else away


def _real_season_stat_lines(player_stats) -> tuple[dict, dict, dict, dict]:
    """Real per-player season lines, keyed by (team_abbr, name) exactly
    like aggregate_season_stats()/aggregate_season_defensive_stats()
    already produce for a simulated season -- a player can appear in
    more than one dict (e.g. a scrambling QB has both a passing and a
    rushing line), matching real box-score convention."""
    passing: dict[tuple[str, str], SeasonPassingLine] = {}
    rushing: dict[tuple[str, str], SeasonRushingLine] = {}
    receiving: dict[tuple[str, str], SeasonReceivingLine] = {}
    defense: dict[tuple[str, str], SeasonDefensiveLine] = {}

    for row in player_stats.iter_rows(named=True):
        abbr = _map_abbr(row["recent_team"] or "")
        if abbr not in MY_ABBRS:
            continue
        name = row["player_display_name"]
        if not name:
            continue
        key = (abbr, name)

        if (row["attempts"] or 0) > 0:
            line = passing.setdefault(key, SeasonPassingLine(name=name, team_abbr=abbr))
            line.completions += row["completions"] or 0
            line.attempts += row["attempts"] or 0
            line.yards += row["passing_yards"] or 0
            line.touchdowns += row["passing_tds"] or 0
            line.interceptions += row["passing_interceptions"] or 0

        if (row["carries"] or 0) > 0:
            line = rushing.setdefault(key, SeasonRushingLine(name=name, team_abbr=abbr))
            line.carries += row["carries"] or 0
            line.yards += row["rushing_yards"] or 0
            line.touchdowns += row["rushing_tds"] or 0

        if (row["receptions"] or 0) > 0 or (row["targets"] or 0) > 0:
            # `targets` is a real, genuine 0 for seasons before the NFL
            # tracked it league-wide (confirmed empirically: 2003-2008
            # have real receptions/receiving_yards but targets == 0 for
            # every player that far back) -- trigger on receptions too,
            # not targets alone, or almost every real pre-2009 receiver
            # would be silently dropped entirely.
            line = receiving.setdefault(key, SeasonReceivingLine(name=name, team_abbr=abbr))
            line.receptions += row["receptions"] or 0
            line.targets += row["targets"] or 0
            line.yards += row["receiving_yards"] or 0
            line.touchdowns += row["receiving_tds"] or 0

        def_total = (row["def_tackles_solo"] or 0) + (row["def_sacks"] or 0) + (row["def_interceptions"] or 0) \
            + (row["def_tackles_for_loss"] or 0) + (row["def_pass_defended"] or 0) + (row["def_fumbles_forced"] or 0)
        if def_total > 0:
            line = defense.setdefault(key, SeasonDefensiveLine(name=name, team_abbr=abbr))
            line.solo_tackles += int(row["def_tackles_solo"] or 0)
            line.tackles_for_loss += int(row["def_tackles_for_loss"] or 0)
            line.sacks += int(row["def_sacks"] or 0)
            line.interceptions += row["def_interceptions"] or 0
            line.passes_defended += row["def_pass_defended"] or 0
            line.forced_fumbles += row["def_fumbles_forced"] or 0
            line.fumble_recoveries += (row["fumble_recovery_own"] or 0) + (row["fumble_recovery_opp"] or 0)

    return passing, rushing, receiving, defense


def _real_rookie_keys(rosters) -> set[tuple[str, str]]:
    rookies = rosters.filter(rosters["years_exp"] == 0)
    return {(_map_abbr(row["team"]), row["full_name"]) for row in rookies.iter_rows(named=True) if row["full_name"]}


def _real_awards(passing, rushing, receiving, defense, rookie_keys, win_pct_by_abbr) -> AwardsRace:
    """Same formula a live simulated season's Awards Race uses (this
    module's own docstring explains why real seasons compute awards
    this way rather than looking up the actual real-world winners)."""
    offensive = offensive_candidates_from_stats(passing, rushing, receiving)
    offensive_rookies = offensive_candidates_from_stats(passing, rushing, receiving, rookie_keys)
    defensive = defensive_candidates_from_stats(defense)
    defensive_rookies = defensive_candidates_from_stats(defense, rookie_keys)

    return AwardsRace(
        mvp=mvp_from_candidates(offensive, win_pct_by_abbr)[:5],
        opoy=sorted(offensive, key=lambda c: -c.score)[:5],
        dpoy=sorted(defensive, key=lambda c: -c.score)[:5],
        roy=sorted(offensive_rookies + defensive_rookies, key=lambda c: -c.score)[:5],
    )


def import_season(year: int) -> SeasonRecord:
    schedules = nfl.load_schedules(seasons=[year])
    player_stats = nfl.load_player_stats(seasons=[year], summary_level="reg")
    rosters = nfl.load_rosters(seasons=[year])

    team_results = list(_real_standings(schedules).values())
    win_pct_by_abbr = {
        r.abbr: (r.wins / (r.wins + r.losses) if (r.wins + r.losses) > 0 else 0.0)
        for r in team_results
    }
    champion_abbr = _real_champion(schedules)
    passing, rushing, receiving, defense = _real_season_stat_lines(player_stats)
    rookie_keys = _real_rookie_keys(rosters)
    awards = _real_awards(passing, rushing, receiving, defense, rookie_keys, win_pct_by_abbr)

    return SeasonRecord(
        season_number=year - FIRST_SEASON,
        team_results=team_results,
        champion_abbr=champion_abbr,
        afc_seeds=None,
        nfc_seeds=None,
        awards=awards,
        passing_leaders=sorted(passing.values(), key=lambda l: -l.yards),
        rushing_leaders=sorted(rushing.values(), key=lambda l: -l.yards),
        receiving_leaders=sorted(receiving.values(), key=lambda l: -l.yards),
        defensive_leaders=sorted(defense.values(), key=lambda l: -l.solo_tackles),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-season", type=int, default=FIRST_SEASON)
    parser.add_argument("--last-season", type=int, default=LAST_SEASON)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print a summary without writing to history.json")
    args = parser.parse_args()

    existing = history_store.get_history()
    if existing and not args.dry_run:
        print(f"data/saves/history.json already has {len(existing)} archived season(s). "
              "This script only ever appends -- if you're re-running it, clear history.json first "
              "or you'll get duplicate/out-of-order season_numbers.")
        return

    for year in range(args.first_season, args.last_season + 1):
        print(f"Importing {year}...", end=" ", flush=True)
        record = import_season(year)
        champ = record.champion_abbr or "?"
        print(f"champion={champ}, {len(record.passing_leaders)} passers, {len(record.rushing_leaders)} rushers, "
              f"{len(record.receiving_leaders)} receivers, {len(record.defensive_leaders)} defenders")
        if not args.dry_run:
            history_store.append_season_record(record)

    if args.dry_run:
        print("Dry run -- nothing written.")
    else:
        print(f"Done. {args.last_season - args.first_season + 1} real seasons archived to data/saves/history.json.")


if __name__ == "__main__":
    main()
