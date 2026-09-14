"""
Imports the real roster + real-world salary data into the Player table.

Source file: data/raw/rosters/madden26_salary_master.xlsx (2035 player rows,
full Madden 26 attributes for all 32 teams, plus real-world salary data
merged in on 2026-09-13 from Over The Cap's contracts table, targeted web
research for ~80 notable players OTC didn't have on file, and -- for
everyone else -- a per-position log-linear model of real salary vs. Madden
Overall rating, fit from the ~1,528 players with a real OTC contract). See
that workbook's "Salary Match Status" and "Research Note" columns for which
of those three a given player's numbers came from.

This REPLACES the previous players.csv/players_with FA.csv-based import
(2368 players, Madden's own in-game fictional contract economy for
salary/signing_bonus -- e.g. it had Josh Allen at $182M "Total Salary",
Joe Burrow at $2.5M -- not real NFL numbers). Those two CSVs are left in
the repo for reference/rollback but are no longer read by this script.
Because this source has a different (smaller) roster than the old CSVs --
2035 vs. 2368 players -- player_ids for anyone not in the new sheet
disappear on this import; anyone whose name+position is unchanged between
the two sources gets the SAME player_id back (see _slug()), so only the
~330 players absent from the new roster actually orphan old references
(injuries, depth chart overrides, saved gameplans, historical box scores
keyed by player_id). Accepted tradeoff, made explicitly aware mid-Season-25
playoffs -- see the conversation this shipped in.

Salary field mapping (Player has no separate Contract table -- see
app/engine/contracts.py's module docstring):
    salary            = real annual salary (APY)
    guaranteed_money  = real total guaranteed money at signing (added by
                         this same import; see app/models/player.py)
    signing_bonus     = 0 for every re-imported player -- the source data
                         doesn't break bonus money out separately from the
                         rest of what's guaranteed, so there's nothing real
                         to put here without double-counting guaranteed_money
    contract_years_remaining = still the pre-existing synthetic 1-5
                         placeholder (deterministically seeded per
                         player_id) -- the source data has real contract
                         *length*, but not real years *remaining*, which
                         depends on when each deal was signed relative to
                         now; not something this import can derive.

Free agency: ~42 players the web research pass confirmed are currently
retired, released and unsigned, or off a real contract that's since
expired get team_abbr=None here (see _is_real_free_agent()) even though
Madden's own roster still has them on a team -- reality wins over the
game export for this one field.

potential/morale: the salary-master sheet is a ratings-only Madden export
and (unlike the old players.csv) carries no Potential/Morale columns.
Both are required, non-nullable fields on Player, so this import
synthesizes them the same way contract_years_remaining is synthesized --
deterministically seeded per player_id, disclosed as synthetic here rather
than silently defaulted:
    potential: overall_rating + an age-based ceiling bump (younger players
        get more room to grow, older players get less/negative), clamped
        to [40, 99]
    morale: a flat deterministic 60-90 range (no real signal to base this
        on at all)

Usage:
    .venv/Scripts/python.exe scripts/import_players.py
    .venv/Scripts/python.exe scripts/import_players.py --source path\\to\\other.xlsx
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook
from sqlmodel import delete
from app.core.db import init_db, get_session
from app.models.player import Player, Position
from app.engine.rng import RNG, stable_seed

DEFAULT_SOURCE = Path(__file__).resolve().parent.parent / "data" / "raw" / "rosters" / "madden26_salary_master.xlsx"

# Madden 26's Position ID -> this project's Position enum. LS (long
# snapper) has no equivalent here (Position enum has no LS) and is
# skipped, same as an unmapped position always has been in this importer.
POSITION_ID_MAP: dict[str, str] = {
    "QB": "QB", "HB": "HB", "FB": "FB", "WR": "WR", "TE": "TE",
    "LT": "T", "LG": "G", "C": "C", "RG": "G", "RT": "T",
    "LEDG": "EDGE", "REDG": "EDGE", "DT": "DT",
    "WILL": "LB", "MIKE": "LB", "SAM": "LB",
    "CB": "CB", "FS": "S", "SS": "S", "K": "K", "P": "P",
}

TEAM_FULL_NAME_TO_ABBR: dict[str, str] = {
    "Buffalo Bills": "BUF", "Miami Dolphins": "MIA", "New England Patriots": "NE", "New York Jets": "NYJ",
    "Baltimore Ravens": "BAL", "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Pittsburgh Steelers": "PIT",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX", "Tennessee Titans": "TEN",
    "Denver Broncos": "DEN", "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "NY Jets": "NYJ",
    "Dallas Cowboys": "DAL", "New York Giants": "NYG", "NY Giants": "NYG",
    "Philadelphia Eagles": "PHI", "Washington Commanders": "WAS",
    "Chicago Bears": "CHI", "Detroit Lions": "DET", "Green Bay Packers": "GB", "Minnesota Vikings": "MIN",
    "Atlanta Falcons": "ATL", "Carolina Panthers": "CAR", "New Orleans Saints": "NO", "Tampa Bay Buccaneers": "TB",
    "Arizona Cardinals": "ARI", "Los Angeles Rams": "LAR", "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA",
}


def _slug(first: str, last: str, position: str, used: set[str]) -> str:
    base = f"{first}_{last}_{position}".lower().replace(" ", "_").replace("'", "").replace(".", "")
    slug = base
    n = 2
    while slug in used:
        slug = f"{base}_{n}"
        n += 1
    used.add(slug)
    return slug


def _int(row: dict, key: str, default: int = 0) -> int:
    raw = row.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(round(float(raw)))
    except (ValueError, TypeError):
        return default


def _synth_potential(player_id: str, overall: int, age: int) -> int:
    ceiling_bump = max(0, 27 - age) - max(0, age - 30)
    noise = RNG.with_seed(stable_seed(player_id, "potential")).r().randint(-3, 3)
    return max(40, min(99, overall + ceiling_bump + noise))


def _synth_morale(player_id: str) -> int:
    return RNG.with_seed(stable_seed(player_id, "morale")).r().randint(60, 90)


def _is_real_free_agent(row: dict) -> bool:
    """True if this player is confirmed (via the 2026-09-13 web research
    pass, not Madden's own roster) to have no real current NFL team --
    retired, released and unsigned, or a real contract we found that has
    since expired. Overrides Madden's own team_abbr for these ~42 players
    (Madden's roster and reality disagree here) rather than leaving them
    on a real NFL team they're not actually on."""
    otc_team = str(row.get("OTC Team") or "").lower()
    status = str(row.get("Salary Match Status") or "")
    return (
        "free agent" in otc_team or "retired" in otc_team or "no team" in otc_team
        or status.startswith("Estimated - verified")
    )


def build_player(row: dict, used_ids: set[str]) -> Player | None:
    first = str(row.get("First Name") or "").strip()
    last = str(row.get("Last Name") or "").strip()
    if not first and not last:
        return None

    pos_id_raw = str(row.get("Position ID") or "").strip()
    pos_code = POSITION_ID_MAP.get(pos_id_raw)
    if pos_code is None:
        return None  # unmapped position (e.g. LS) -- caller counts these
    position = Position(pos_code)

    team_full = str(row.get("Team") or "").strip()
    team_abbr = TEAM_FULL_NAME_TO_ABBR.get(team_full)
    if team_abbr is None:
        return None  # caller counts these
    if _is_real_free_agent(row):
        team_abbr = None

    player_id = _slug(first, last, pos_id_raw, used_ids)
    overall = _int(row, "Overall")
    age = _int(row, "Age", default=25)

    apy = _int(row, "Annual Salary (APY)")
    guaranteed = _int(row, "Total Guaranteed")

    return Player(
        player_id=player_id,
        first_name=first,
        last_name=last,
        position=position,
        team_abbr=team_abbr,
        jersey_number=_int(row, "Jersey Number"),
        age=age,
        height_inches=_int(row, "Height"),
        weight_lbs=_int(row, "Weight"),
        college=str(row.get("College") or "").strip(),
        years_pro=_int(row, "Years Pro"),
        overall_rating=overall,
        potential=_synth_potential(player_id, overall, age),
        morale=_synth_morale(player_id),
        salary=apy,
        guaranteed_money=guaranteed,
        signing_bonus=0,
        contract_years_remaining=RNG.with_seed(stable_seed(player_id, "contract_years_remaining")).r().randint(1, 5),
        speed=_int(row, "SPEED"),
        acceleration=_int(row, "ACCELERATION"),
        strength=_int(row, "STRENGTH"),
        agility=_int(row, "AGILITY"),
        jumping=_int(row, "JUMPING"),
        stamina=_int(row, "STAMINA"),
        toughness=_int(row, "TOUGHNESS"),
        durability=_int(row, "INJURY"),
        throw_power=_int(row, "THROWPOWER"),
        throw_accuracy_short=_int(row, "THROWACCURACYSHORT"),
        throw_accuracy_mid=_int(row, "THROWACCURACYMID"),
        throw_accuracy_deep=_int(row, "THROWACCURACYDEEP"),
        play_action=_int(row, "PLAYACTION"),
        throw_on_the_run=_int(row, "THROWONTHERUN"),
        throw_under_pressure=_int(row, "THROWUNDERPRESSURE"),
        break_sack=_int(row, "BREAKSACK"),
        catching=_int(row, "CATCHING"),
        spectacular_catch=_int(row, "SPECTACULARCATCH"),
        catch_in_traffic=_int(row, "CATCHINTRAFFIC"),
        short_route_running=_int(row, "SHORTROUTERUNNING"),
        medium_route_running=_int(row, "MEDIUMROUTERUNNING"),
        deep_route_running=_int(row, "DEEPROUTERUNNING"),
        release=_int(row, "RELEASE"),
        carrying=_int(row, "CARRYING"),
        trucking=_int(row, "TRUCKING"),
        change_of_direction=_int(row, "CHANGEOFDIRECTION"),
        ball_carrier_vision=_int(row, "BCVISION"),
        stiff_arm=_int(row, "STIFFARM"),
        spin_move=_int(row, "SPINMOVE"),
        juke_move=_int(row, "JUKEMOVE"),
        break_tackle=_int(row, "BREAKTACKLE"),
        run_block=_int(row, "RUNBLOCK"),
        pass_block=_int(row, "PASSBLOCK"),
        run_block_power=_int(row, "RUNBLOCKPOWER"),
        run_block_finesse=_int(row, "RUNBLOCKFINESSE"),
        pass_block_power=_int(row, "PASSBLOCKPOWER"),
        pass_block_finesse=_int(row, "PASSBLOCKFINESSE"),
        lead_block=_int(row, "LEADBLOCK"),
        impact_blocking=_int(row, "IMPACTBLOCKING"),
        tackle=_int(row, "TACKLE"),
        hit_power=_int(row, "HITPOWER"),
        block_shedding=_int(row, "BLOCKSHEDDING"),
        pursuit=_int(row, "PURSUIT"),
        play_recognition=_int(row, "PLAYRECOGNITION"),
        man_coverage=_int(row, "MANCOVERAGE"),
        zone_coverage=_int(row, "ZONECOVERAGE"),
        press=_int(row, "PRESS"),
        power_moves=_int(row, "POWERMOVES"),
        finesse_moves=_int(row, "FINESSEMOVES"),
        kick_power=_int(row, "KICKPOWER"),
        kick_accuracy=_int(row, "KICKACCURACY"),
        kick_return=_int(row, "KICKRETURN"),
        awareness=_int(row, "AWARENESS"),
    )


LB_GROUP: tuple[str, ...] = ()  # LOLB/MLB/ROLB unified into LB (2026-09-14) -- no relabel needed


def _fix_zero_position_gaps(players: list[Player]) -> None:
    """This importer's source has a real, disclosed data-quality issue:
    it labels off-ball linebackers with Madden's specific WILL/MIKE/SAM
    sub-roles (mapped here to LOLB/MLB/ROLB), and a real chunk of teams'
    exports simply have zero players carrying the "SAM" (ROLB) label --
    likely this fictional league's nickel-heavy defenses genuinely not
    rostering a traditional SAM backer, same real-world trend as today's
    NFL. app/services/depth_chart.py's get_defensive_starters() has no
    None-safe fallback for an empty position (see app/engine/free_agency.py's
    MIN_ROSTER_COUNTS comment) and crashes with IndexError the moment a
    game involving that team is simulated -- a live bug found testing this
    same import, not a hypothetical.

    Since there are zero ROLB free agents in this same import to draw from
    (fill_roster_gaps()'s normal fix, run automatically every offseason,
    would find nothing to sign), this instead re-labels one team's own
    surplus LOLB/MLB player as its ROLB -- the lowest-overall one on
    whichever of those two positions the team has more than the required
    minimum of, so the team doesn't lose real depth at a position it
    actually has enough of. Every gap team in this source has that
    surplus (never take from a position already at its 1-player minimum).
    Mutates `players` in place. Any OTHER MIN_ROSTER_COUNTS gap (there
    are none from this source as of 2026-09-13 outside the ROLB case,
    confirmed by this same run's own printed warnings) is left for
    fill_roster_gaps()'s free-agency signing path to handle at the next
    offseason rollover, same as any in-season roster attrition."""
    from collections import Counter
    from app.engine.free_agency import MIN_ROSTER_COUNTS

    by_team: dict[str, list[Player]] = {}
    free_agents: list[Player] = []
    for p in players:
        if p.team_abbr:
            by_team.setdefault(p.team_abbr, []).append(p)
        else:
            free_agents.append(p)

    for team_abbr, roster in by_team.items():
        counts = Counter(p.position.value for p in roster)
        for position, minimum in MIN_ROSTER_COUNTS.items():
            if counts.get(position.value, 0) >= minimum:
                continue
            if position.value in LB_GROUP:
                donor_pos = max(
                    (pos for pos in LB_GROUP if pos != position.value),
                    key=lambda pos: counts.get(pos, 0),
                )
                donor_pool = [p for p in roster if p.position.value == donor_pos]
                if len(donor_pool) > MIN_ROSTER_COUNTS[Position(donor_pos)]:
                    weakest = min(donor_pool, key=lambda p: p.overall_rating)
                    print(f"  {team_abbr}: relabeling {weakest.full_name} ({donor_pos} -> {position.value}) -- source had zero {position.value}")
                    weakest.position = position
                    counts[donor_pos] -= 1
                    counts[position.value] = counts.get(position.value, 0) + 1
                    continue
            # No same-position-group donor (or not an LB-group position at
            # all, e.g. P) -- same fix free_agency.fill_roster_gaps() would
            # apply automatically at the next offseason rollover, just run
            # now so this roster is never crash-prone even before its
            # first rollover.
            fa_candidates = [fa for fa in free_agents if fa.position.value == position.value]
            if fa_candidates:
                best = max(fa_candidates, key=lambda p: p.overall_rating)
                print(f"  {team_abbr}: signing free agent {best.full_name} ({position.value}) -- source had zero {position.value}")
                best.team_abbr = team_abbr
                free_agents.remove(best)
                counts[position.value] = counts.get(position.value, 0) + 1
                continue
            print(f"  WARNING: {team_abbr} still short at {position.value} (has {counts.get(position.value, 0)}, needs {minimum}) -- no donor or free agent available, left for fill_roster_gaps() at next rollover")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE),
                         help="Path to the salary-master workbook (default: data/raw/rosters/madden26_salary_master.xlsx)")
    args = parser.parse_args()

    wb = load_workbook(args.source, data_only=True)
    ws = wb.active
    headers = [c.value for c in ws[1]]

    used_ids: set[str] = set()
    players: list[Player] = []
    skipped_position = 0
    skipped_team = 0
    real_free_agents = 0

    for excel_row in ws.iter_rows(min_row=2, values_only=True):
        row = dict(zip(headers, excel_row))
        pos_id_raw = str(row.get("Position ID") or "").strip()
        team_full = str(row.get("Team") or "").strip()
        if pos_id_raw not in POSITION_ID_MAP:
            skipped_position += 1
            continue
        if team_full not in TEAM_FULL_NAME_TO_ABBR:
            skipped_team += 1
            continue
        if _is_real_free_agent(row):
            real_free_agents += 1
        p = build_player(row, used_ids)
        if p:
            players.append(p)

    print(f"source rows: {ws.max_row - 1}")
    print(f"skipped (unmapped position, e.g. LS): {skipped_position}")
    print(f"skipped (unmapped team): {skipped_team}")
    print(f"real-world free agents/retired (team_abbr overridden to None): {real_free_agents}")
    print(f"total players built: {len(players)}")

    print("checking every team meets MIN_ROSTER_COUNTS (depth_chart.py's hard requirements)...")
    _fix_zero_position_gaps(players)

    init_db()
    with get_session() as session:
        session.exec(delete(Player))
        session.commit()
        for p in players:
            session.add(p)
        session.commit()

    print("Import complete.")


if __name__ == "__main__":
    main()
