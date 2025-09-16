from __future__ import annotations
import csv
import json
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .schemas import TeamIn, PlayerIn, DepthChartIn, POSITIONS

# Default roster sizes -> 53 players per team
DEFAULT_ROSTER_SIZES: Dict[str, int] = {
    "QB": 3, "RB": 4, "WR": 6, "TE": 3,
    "OL": 9, "DL": 8, "LB": 7, "CB": 6, "S": 4,
    "K": 1, "P": 1, "LS": 1,
}

# 32 generic team identities (no trademarked names)
DEFAULT_TEAMS: List[Tuple[str, str, str, str]] = [
    ("Arlington", "Arrows", "NFC", "East"),
    ("Birmingham", "Bulldogs", "NFC", "South"),
    ("Cedar City", "Comets", "NFC", "North"),
    ("Daytona", "Dragons", "NFC", "West"),
    ("Eugene", "Express", "AFC", "East"),
    ("Fresno", "Falcons", "AFC", "South"),
    ("Glendale", "Guardians", "AFC", "North"),
    ("Helena", "Hawks", "AFC", "West"),
    ("Irvine", "Ice", "NFC", "East"),
    ("Jackson", "Jackals", "NFC", "South"),
    ("Knox", "Knights", "NFC", "North"),
    ("Laredo", "Lightning", "NFC", "West"),
    ("Madison", "Mammoths", "AFC", "East"),
    ("Naples", "Nomads", "AFC", "South"),
    ("Ogden", "Outriders", "AFC", "North"),
    ("Plano", "Phantoms", "AFC", "West"),
    ("Quincy", "Quakes", "NFC", "East"),
    ("Reno", "Ravens", "NFC", "South"),
    ("Salem", "Sentinels", "NFC", "North"),
    ("Tulsa", "Typhoon", "NFC", "West"),
    ("Urbana", "Union", "AFC", "East"),
    ("Visalia", "Vipers", "AFC", "South"),
    ("Waco", "Wardens", "AFC", "North"),
    ("Yonkers", "Yetis", "AFC", "West"),
    ("Abilene", "Anchors", "NFC", "East"),
    ("Boise", "Bison", "NFC", "South"),
    ("Chandler", "Chargers", "NFC", "North"),
    ("Dover", "Defenders", "NFC", "West"),
    ("Erie", "Eagles", "AFC", "East"),
    ("Flagstaff", "Frontiers", "AFC", "South"),
    ("Grandview", "Grizzlies", "AFC", "North"),
    ("Henderson", "Hurricanes", "AFC", "West"),
]

FIRST_NAMES = ["John","Max","Will","Alex","Chris","Jordan","Taylor","Jamie","Sam","Pat","Casey","Riley","Logan","Drew","Carter","Avery","Micah","Lane","Rowan","Kai","Reed","Shawn","Corey","Evan","Noel","Shane","Glen","Owen","Zane","Jesse"]
LAST_NAMES  = ["Doe","Runner","Hands","Strong","Swift","Stone","Fields","Brooks","Hill","Ward","Hunt","Price","Cole","Reed","King","Knight","Moss","White","Black","Young","West","North","South","East","Powers","Miles","Page","Woods","Clark","Ford"]

# Position-specific “centers” for ratings
POS_RATING_MEANS = {
    "QB": dict(throw_power=72, throw_accuracy=70, awareness=60, speed=55, agility=55),
    "RB": dict(speed=80, agility=75, strength=60, stamina=78, awareness=50),
    "WR": dict(speed=85, agility=82, catching=78, stamina=82, awareness=55),
    "TE": dict(strength=70, catching=68, speed=62, awareness=55),
    "OL": dict(strength=85, awareness=60, stamina=80),
    "DL": dict(strength=82, tackling=78, awareness=55, stamina=78),
    "LB": dict(strength=75, tackling=80, awareness=60, speed=60),
    "CB": dict(speed=86, agility=84, awareness=58, catching=55),
    "S" : dict(speed=82, agility=78, awareness=62, tackling=70),
    "K" : dict(awareness=55, stamina=70),
    "P" : dict(awareness=55, stamina=70),
    "LS": dict(awareness=55, stamina=70),
}

def clamp(v: int) -> int:
    return max(0, min(100, v))

def rand_rating(rng: random.Random, pos: str, key: str, base: int = 50, spread: int = 25) -> int:
    center = POS_RATING_MEANS.get(pos, {}).get(key, base)
    sample = int(rng.gauss(center, spread/3))
    return clamp(sample)

def unique_jerseys_for_team(rng: random.Random, count: int) -> List[int]:
    pool = list(range(1, 100))
    rng.shuffle(pool)
    return pool[:count]

def make_team_tuple(seed_idx: int) -> TeamIn:
    loc, nick, conf, div = DEFAULT_TEAMS[seed_idx]
    return TeamIn(
        location_name=loc, nickname=nick,
        conference=conf, division=div,
        power_rating=50, cap_space=20_000_000
    )

def make_player(rng: random.Random, team_key: str, pos: str, jersey: int) -> PlayerIn:
    fn = rng.choice(FIRST_NAMES)
    ln = rng.choice(LAST_NAMES)
    age = rng.randint(21, 33)
    salary = rng.randint(500_000, 5_000_000)
    years = rng.randint(1, 4)

    # base ratings
    ratings = {
        "speed": rand_rating(rng, pos, "speed"),
        "strength": rand_rating(rng, pos, "strength"),
        "agility": rand_rating(rng, pos, "agility"),
        "throw_power": rand_rating(rng, pos, "throw_power"),
        "throw_accuracy": rand_rating(rng, pos, "throw_accuracy"),
        "catching": rand_rating(rng, pos, "catching"),
        "tackling": rand_rating(rng, pos, "tackling"),
        "awareness": rand_rating(rng, pos, "awareness"),
        "potential": rand_rating(rng, pos, "potential", base=60),
        "stamina": rand_rating(rng, pos, "stamina", base=70),
        "injury_proneness": clamp(100 - rand_rating(rng, pos, "stamina", base=65)),
        "morale": rng.randint(50, 80),
    }

    return PlayerIn(
        first_name=fn, last_name=ln, position=pos, jersey=jersey,
        age=age, salary=salary, contract_years=years, team_key=team_key, **ratings
    )

def make_league(seed: int, team_count: int = 32,
                roster_sizes: Dict[str, int] = None,
                free_agents: int = 0):
    """
    Deterministically generate teams, players, and depth chart entries.
    Returns (teams, players, depth_chart).
    """
    rng = random.Random(seed)
    roster_sizes = roster_sizes or DEFAULT_ROSTER_SIZES

    teams: List[TeamIn] = []
    players: List[PlayerIn] = []
    depth: List[DepthChartIn] = []

    for i in range(team_count):
        t = make_team_tuple(i % len(DEFAULT_TEAMS))
        teams.append(t)
        team_key = f"{t.location_name}|{t.nickname}"

        # generate jerseys unique per team
        total_needed = sum(roster_sizes.values())
        jerseys = unique_jerseys_for_team(rng, total_needed)
        idx = 0

        # generate by position
        for pos, count in roster_sizes.items():
            jerseys_pos = jerseys[idx: idx + count]
            idx += count
            group = [make_player(rng, team_key, pos, j) for j in jerseys_pos]
            players.extend(group)

            # depth chart: starter/backup (first two if available)
            starter = jerseys_pos[0]
            backup = jerseys_pos[1] if len(jerseys_pos) > 1 else None
            depth.append(DepthChartIn(team_key=team_key, position=pos,
                                      starter_jersey=starter, backup_jersey=backup))

    # free agents pool (team_key = "FA|FA")
    for _ in range(free_agents):
        pos = rng.choice(POSITIONS)
        jersey = rng.randint(1, 99)
        players.append(make_player(rng, "FA|FA", pos, jersey))

    return teams, players, depth

def write_csvs(out_dir: str, teams: List[TeamIn], players: List[PlayerIn], depth: List[DepthChartIn]) -> None:
    # TEAMS
    with open(f"{out_dir}/teams.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["location_name","nickname","conference","division","power_rating","cap_space"])
        for t in teams:
            w.writerow([t.location_name,t.nickname,t.conference,t.division,t.power_rating,t.cap_space])

    # PLAYERS
    with open(f"{out_dir}/players.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "first_name","last_name","position","jersey","age","salary","contract_years","team_key",
            "speed","strength","agility","throw_power","throw_accuracy","catching","tackling",
            "awareness","potential","stamina","injury_proneness","morale"
        ])
        for p in players:
            w.writerow([
                p.first_name,p.last_name,p.position,p.jersey,p.age,p.salary,p.contract_years,p.team_key,
                p.speed,p.strength,p.agility,p.throw_power,p.throw_accuracy,p.catching,p.tackling,
                p.awareness,p.potential,p.stamina,p.injury_proneness,p.morale
            ])

    # DEPTH CHART
    with open(f"{out_dir}/depth_chart.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["team_key","position","starter_jersey","backup_jersey"])
        for d in depth:
            w.writerow([d.team_key,d.position,d.starter_jersey, d.backup_jersey or ""])

def write_json(out_dir: str, teams: List[TeamIn], players: List[PlayerIn], depth: List[DepthChartIn]) -> None:
    def dump(obj): return [o.model_dump() for o in obj]
    with open(f"{out_dir}/teams.json","w",encoding="utf-8") as f:
        json.dump(dump(teams), f, indent=2)
    with open(f"{out_dir}/players.json","w",encoding="utf-8") as f:
        json.dump(dump(players), f, indent=2)
    with open(f"{out_dir}/depth_chart.json","w",encoding="utf-8") as f:
        json.dump(dump(depth), f, indent=2)
