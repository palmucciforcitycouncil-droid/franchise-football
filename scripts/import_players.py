"""
Imports the real roster data into the Player table.

Source files (local Desktop folder, not part of the repo -- see the
--source-dir flag): players.csv (2368 rows, full Madden attributes, all
32 teams) is the attribute source of truth. players_with FA.csv is used
only to determine which players should be reclassified as free agents
(team_abbr=None) -- its own attribute columns for FA players are mostly
zeroed/sentinel placeholder data (a real data quality issue in that
export), so we don't trust them; see the module-level check this script
prints for the small number of FA players who have no full-attribute
match in players.csv and had to fall back to that thin data anyway.

Usage:
    .venv/Scripts/python.exe scripts/import_players.py --source-dir "C:\\Users\\bpalm\\OneDrive\\Desktop\\Franchise Football game"
"""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import delete
from app.core.db import init_db, get_session
from app.models.player import Player, Position
from app.data.team_name_map import NICKNAME_TO_ABBR


def _int(row: dict, key: str, default: int = 0) -> int:
    raw = row.get(key, "")
    if raw is None:
        return default
    raw = str(raw).strip()
    if raw == "":
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def _slug(first: str, last: str, position: str, used: set[str]) -> str:
    base = f"{first}_{last}_{position}".lower().replace(" ", "_").replace("'", "").replace(".", "")
    slug = base
    n = 2
    while slug in used:
        slug = f"{base}_{n}"
        n += 1
    used.add(slug)
    return slug


def build_player(row: dict, team_abbr: str | None, used_ids: set[str]) -> Player | None:
    full_name = row.get("Full Name", "").strip()
    if not full_name:
        return None
    parts = full_name.split(" ", 1)
    first, last = (parts[0], parts[1]) if len(parts) > 1 else (parts[0], "")

    pos_raw = row.get("Position", "").strip()
    try:
        position = Position(pos_raw)
    except ValueError:
        print(f"  skipping {full_name}: unknown position {pos_raw!r}")
        return None

    player_id = _slug(first, last, pos_raw, used_ids)

    return Player(
        player_id=player_id,
        first_name=first,
        last_name=last,
        position=position,
        team_abbr=team_abbr,
        jersey_number=_int(row, "Jersey Number"),
        age=_int(row, "Age"),
        height_inches=_int(row, "Height"),
        weight_lbs=_int(row, "Weight"),
        college=row.get("College", "").strip(),
        years_pro=_int(row, "Years Pro"),
        overall_rating=_int(row, "Overall Rating"),
        potential=_int(row, "Potential"),
        morale=_int(row, "Morale"),
        salary=_int(row, "Total Salary "),
        signing_bonus=_int(row, "Signing Bonus "),
        speed=_int(row, "Speed"),
        acceleration=_int(row, "Acceleration"),
        strength=_int(row, "Strength"),
        agility=_int(row, "Agility"),
        jumping=_int(row, "Jumping"),
        stamina=_int(row, "Stamina"),
        toughness=_int(row, "Toughness"),
        durability=_int(row, "Injury"),
        throw_power=_int(row, "Throw Power"),
        throw_accuracy_short=_int(row, "Throw Accuracy Short"),
        throw_accuracy_mid=_int(row, "Throw Accuracy Mid"),
        throw_accuracy_deep=_int(row, "Throw Accuracy Deep"),
        play_action=_int(row, "Play Action"),
        throw_on_the_run=_int(row, "Throw On The Run"),
        throw_under_pressure=_int(row, "Throw Under Pressure"),
        break_sack=_int(row, "Break Sack"),
        catching=_int(row, "Catching"),
        spectacular_catch=_int(row, "Spectacular Catch"),
        catch_in_traffic=_int(row, "Catch In Traffic"),
        short_route_running=_int(row, "Short Route Running"),
        medium_route_running=_int(row, "Medium Route Running"),
        deep_route_running=_int(row, "Deep Route Running"),
        release=_int(row, "Release"),
        carrying=_int(row, "Carrying"),
        trucking=_int(row, "Trucking"),
        change_of_direction=_int(row, "Change Of Direction"),
        ball_carrier_vision=_int(row, "Ball Carrier Vision"),
        stiff_arm=_int(row, "Stiff Arm"),
        spin_move=_int(row, "Spin Move"),
        juke_move=_int(row, "Juke Move"),
        break_tackle=_int(row, "Break Tackle"),
        run_block=_int(row, "Run Block"),
        pass_block=_int(row, "Pass Block"),
        run_block_power=_int(row, "Run Block Power"),
        run_block_finesse=_int(row, "Run Block Finesse"),
        pass_block_power=_int(row, "Pass Block Power"),
        pass_block_finesse=_int(row, "Pass Block Finesse"),
        lead_block=_int(row, "Lead Block"),
        impact_blocking=_int(row, "Impact Blocking"),
        tackle=_int(row, "Tackle"),
        hit_power=_int(row, "Hit Power"),
        block_shedding=_int(row, "Block Shedding"),
        pursuit=_int(row, "Pursuit"),
        play_recognition=_int(row, "Play Recognition"),
        man_coverage=_int(row, "Man Coverage"),
        zone_coverage=_int(row, "Zone Coverage"),
        press=_int(row, "Press"),
        power_moves=_int(row, "Power Moves"),
        finesse_moves=_int(row, "Finesse Moves"),
        kick_power=_int(row, "Kick Power"),
        kick_accuracy=_int(row, "Kick Accuracy"),
        kick_return=_int(row, "Kick Return"),
        awareness=_int(row, "Awareness"),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, help="Folder containing players.csv and players_with FA.csv")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    full_path = source_dir / "players.csv"
    fa_path = source_dir / "players_with FA.csv"

    with open(full_path, encoding="utf-8-sig") as f:
        full_rows = list(csv.DictReader(f))
    with open(fa_path, encoding="utf-8-sig") as f:
        fa_rows = list(csv.DictReader(f))

    def norm(name: str) -> str:
        # "Jr." vs "Jr", "Mckinney" vs "McKinney" -- the two source files
        # don't agree on punctuation/capitalization for every player, so
        # matching has to tolerate that rather than treat them as different people.
        return name.strip().rstrip(".").lower()

    fa_rows_only = [r for r in fa_rows if r.get("Team", "").strip() == "FA"]
    fa_names = {r["Full Name"].strip() for r in fa_rows_only}
    fa_norm_names = {norm(n) for n in fa_names}
    full_by_name = {r["Full Name"].strip(): r for r in full_rows}
    full_by_norm_name = {norm(r["Full Name"]): r for r in full_rows}

    print(f"players.csv: {len(full_rows)} rows")
    print(f"free agents flagged in players_with FA.csv: {len(fa_names)}")

    missing_full_data = fa_norm_names - set(full_by_norm_name.keys())
    if missing_full_data:
        print(f"WARNING: {len(missing_full_data)} free agents have no full-attribute row in players.csv (even after name normalization), using thin FA data:")
        for name in missing_full_data:
            print(f"  - {name}")

    fa_thin_by_name = {r["Full Name"].strip(): r for r in fa_rows_only}

    used_ids: set[str] = set()
    players: list[Player] = []
    skipped_unmapped_team = 0

    for row in full_rows:
        name = row.get("Full Name", "").strip()
        if norm(name) in fa_norm_names:
            continue  # handled separately below with team_abbr=None
        nickname = row.get("Team", "").strip()
        abbr = NICKNAME_TO_ABBR.get(nickname)
        if abbr is None:
            skipped_unmapped_team += 1
            continue
        p = build_player(row, abbr, used_ids)
        if p:
            players.append(p)

    for name in fa_names:
        source_row = full_by_norm_name.get(norm(name)) or fa_thin_by_name[name]
        p = build_player(source_row, None, used_ids)
        if p:
            players.append(p)

    print(f"skipped (unmapped team nickname): {skipped_unmapped_team}")
    print(f"total players built: {len(players)}")

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
