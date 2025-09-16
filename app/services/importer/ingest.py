from __future__ import annotations

import argparse
import csv
import json
from typing import Iterable, List, Tuple, Dict, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from .schemas import TeamIn, PlayerIn, DepthChartIn
from app.models import Team, Player, DepthChart  # adjust if your paths differ
from app.models.database import create_db_and_tables, get_session


# --- Simple helper: set attribute if the model actually has it -----------------
def set_if_attr(obj, name: str, value):
    if hasattr(obj, name):
        setattr(obj, name, value)


# --- Lookups -------------------------------------------------------------------
def team_by_key(session: Session, key: Tuple[str, str]) -> Optional[Team]:
    q = select(Team).where(Team.location_name == key[0], Team.nickname == key[1])
    return session.scalar(q)


def player_by_team_jersey(session: Session, team_id: Optional[int], jersey: int) -> Optional[Player]:
    if not team_id:
        return None
    q = select(Player).where(Player.team_id == team_id, Player.jersey == jersey)
    return session.scalar(q)


def team_jersey_set(session: Session, team_id: int) -> Set[int]:
    rows = session.execute(
        select(Player.jersey).where(Player.team_id == team_id)
    ).all()
    return {r[0] for r in rows}


# --- Import core ---------------------------------------------------------------
def import_roster(
    session: Session,
    *,
    teams: Iterable[TeamIn],
    players: Iterable[PlayerIn],
    depth_chart: Iterable[DepthChartIn],
    upsert: bool = True
) -> Dict[str, int]:
    """
    Import the league roster in three phases: TEAMS -> PLAYERS -> DEPTH CHART.

    Key fix for your error:
      We now call session.flush() *after* inserting/updating players and *before*
      resolving the depth chart. This guarantees that SELECTs used to find starter/
      backup players will see the new rows in the database.
    """
    created = updated = skipped = 0
    key_to_team_id: Dict[Tuple[str, str], int] = {}

    try:
        # -------------------- TEAMS --------------------
        for t in teams:
            key = (t.location_name.strip(), t.nickname.strip())
            existing = team_by_key(session, key)
            if existing:
                key_to_team_id[key] = existing.id
                if upsert:
                    set_if_attr(existing, "conference", t.conference)
                    set_if_attr(existing, "division", t.division)
                    set_if_attr(existing, "power_rating", t.power_rating)
                    set_if_attr(existing, "cap_space", t.cap_space)
                    updated += 1
                else:
                    skipped += 1
            else:
                new_t = Team(location_name=key[0], nickname=key[1])
                set_if_attr(new_t, "conference", t.conference)
                set_if_attr(new_t, "division", t.division)
                set_if_attr(new_t, "power_rating", t.power_rating)
                set_if_attr(new_t, "cap_space", t.cap_space)
                session.add(new_t)
                # Flush so id is available immediately for players
                session.flush()
                key_to_team_id[key] = new_t.id
                created += 1

        # -------------------- PLAYERS -------------------
        for p in players:
            if p.age < 18:
                raise ValueError(f"Player {p.first_name} {p.last_name} age {p.age} < 18")

            ratings = [
                p.speed, p.strength, p.agility, p.throw_power, p.throw_accuracy,
                p.catching, p.tackling, p.awareness, p.potential, p.stamina,
                p.injury_proneness, p.morale
            ]
            if any(r < 0 or r > 100 for r in ratings):
                raise ValueError(f"Player {p.first_name} {p.last_name} has rating out of 0..100")

            # team_key like "Arlington|Arrows" or "FA|FA"
            loc, nick = [s.strip() for s in p.team_key.split("|", 1)]
            team_id = key_to_team_id.get((loc, nick))

            # Non-FA players must map to a known team
            if (loc, nick) != ("FA", "FA") and not team_id:
                raise ValueError(f"Unknown team_key for player {p.first_name} {p.last_name}: '{p.team_key}' "
                                 f"(make sure teams.csv was loaded and matches exactly)")

            existing = player_by_team_jersey(session, team_id, p.jersey) if team_id else None
            if existing:
                if upsert:
                    for name, value in [
                        ("first_name", p.first_name), ("last_name", p.last_name),
                        ("position", p.position), ("age", p.age),
                        ("salary", p.salary), ("contract_years", p.contract_years),
                        ("speed", p.speed), ("strength", p.strength), ("agility", p.agility),
                        ("throw_power", p.throw_power), ("throw_accuracy", p.throw_accuracy),
                        ("catching", p.catching), ("tacking", p.tackling),  # typo-safe set_if_attr
                        ("tackling", p.tackling),
                        ("awareness", p.awareness), ("potential", p.potential),
                        ("stamina", p.stamina), ("injury_proneness", p.injury_proneness),
                        ("morale", p.morale),
                    ]:
                        set_if_attr(existing, name, value)
                    updated += 1
                else:
                    skipped += 1
            else:
                new_p = Player(
                    first_name=p.first_name,
                    last_name=p.last_name,
                    position=p.position,
                    jersey=p.jersey,
                    age=p.age
                )
                if team_id:
                    set_if_attr(new_p, "team_id", team_id)
                for name, value in [
                    ("salary", p.salary), ("contract_years", p.contract_years),
                    ("speed", p.speed), ("strength", p.strength), ("agility", p.agility),
                    ("throw_power", p.throw_power), ("throw_accuracy", p.throw_accuracy),
                    ("catching", p.catching), ("tackling", p.tackling),
                    ("awareness", p.awareness), ("potential", p.potential),
                    ("stamina", p.stamina), ("injury_proneness", p.injury_proneness),
                    ("morale", p.morale),
                ]:
                    set_if_attr(new_p, name, value)
                session.add(new_p)
                created += 1

        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # IMPORTANT: make sure newly added players are visible to SELECTs
        session.flush()
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        # -------------------- DEPTH CHART ----------------
        for d in depth_chart:
            loc, nick = [s.strip() for s in d.team_key.split("|", 1)]
            team_id = key_to_team_id.get((loc, nick))
            if not team_id:
                raise ValueError(f"Unknown team_key in depth chart: '{d.team_key}'. "
                                 f"Check teams.csv and depth_chart.csv for exact matching.")

            jerseys_on_team = sorted(team_jersey_set(session, team_id))
            # Starter
            starter = session.scalar(select(Player).where(
                Player.team_id == team_id, Player.jersey == d.starter_jersey
            ))
            if not starter:
                msg = (
                    f"Depth chart starter jersey {d.starter_jersey} not found on team {d.team_key} "
                    f"for position {d.position}. "
                    f"Available jerseys on that team: {jerseys_on_team[:60]}"
                )
                raise ValueError(msg)

            # Backup (optional)
            backup = None
            if d.backup_jersey not in (None, ""):
                backup = session.scalar(select(Player).where(
                    Player.team_id == team_id, Player.jersey == d.backup_jersey
                ))
                if not backup:
                    msg = (
                        f"Depth chart backup jersey {d.backup_jersey} not found on team {d.team_key} "
                        f"for position {d.position}. "
                        f"Available jerseys on that team: {jerseys_on_team[:60]}"
                    )
                    raise ValueError(msg)

            existing = session.scalar(select(DepthChart).where(
                DepthChart.team_id == team_id, DepthChart.position == d.position
            ))
            if existing:
                if upsert:
                    set_if_attr(existing, "starter_player_id", starter.id)
                    set_if_attr(existing, "backup_player_id", backup.id if backup else None)
                    updated += 1
                else:
                    skipped += 1
            else:
                dc = DepthChart(team_id=team_id, position=d.position)
                set_if_attr(dc, "starter_player_id", starter.id)
                set_if_attr(dc, "backup_player_id", backup.id if backup else None)
                session.add(dc)
                created += 1

        session.commit()
        return {"created": created, "updated": updated, "skipped": skipped}
    except Exception:
        session.rollback()
        raise


# --- CSV loaders ---------------------------------------------------------------
def _load_csv_team(path: str) -> List[TeamIn]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append(TeamIn(**{
                "location_name": row["location_name"].strip(),
                "nickname": row["nickname"].strip(),
                "conference": row["conference"].strip(),
                "division": row["division"].strip(),
                "power_rating": int(row["power_rating"]),
                "cap_space": int(row["cap_space"]),
            }))
    return out


def _load_csv_players(path: str) -> List[PlayerIn]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            payload = {k: row[k] for k in row}
            # Normalize fields
            payload["team_key"] = payload["team_key"].strip()
            for k in ["jersey", "age", "salary", "contract_years", "speed", "strength", "agility",
                      "throw_power", "throw_accuracy", "catching", "tackling", "awareness",
                      "potential", "stamina", "injury_proneness", "morale"]:
                payload[k] = int(str(payload[k]).strip())
            payload["first_name"] = payload["first_name"].strip()
            payload["last_name"] = payload["last_name"].strip()
            payload["position"] = payload["position"].strip()
            out.append(PlayerIn(**payload))
    return out


def _load_csv_depth(path: str) -> List[DepthChartIn]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            team_key = row["team_key"].strip()
            position = row["position"].strip()
            starter_raw = str(row["starter_jersey"]).strip()
            backup_raw = str(row.get("backup_jersey", "")).strip()

            starter = int(starter_raw)
            backup_int = int(backup_raw) if backup_raw != "" else None

            out.append(DepthChartIn(
                team_key=team_key,
                position=position,
                starter_jersey=starter,
                backup_jersey=backup_int
            ))
    return out


def _load_json(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- CLI entrypoints -----------------------------------------------------------
def cli_import_from_dir(path: str) -> Dict[str, int]:
    """
    Import from a directory that contains teams.csv, players.csv, depth_chart.csv.
    """
    teams = _load_csv_team(f"{path}/teams.csv")
    players = _load_csv_players(f"{path}/players.csv")
    depth = _load_csv_depth(f"{path}/depth_chart.csv")

    create_db_and_tables()
    with get_session() as session:
        return import_roster(session, teams=teams, players=players, depth_chart=depth, upsert=True)


def main():
    parser = argparse.ArgumentParser(
        description="Import roster from a directory containing teams.csv, players.csv, depth_chart.csv."
    )
    parser.add_argument("--from", dest="from_path", required=True,
                        help="Directory with teams.csv, players.csv, depth_chart.csv")
    args = parser.parse_args()
    res = cli_import_from_dir(args.from_path)
    print(f"Import summary: {res}")


if __name__ == "__main__":
    main()
