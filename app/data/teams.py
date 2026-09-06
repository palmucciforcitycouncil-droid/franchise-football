"""
The 32 team locations, matching the GDD's "location-only" team identity
(no licensed nicknames/logos -- see Part 1 Sec 10.4).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TeamInfo:
    abbr: str
    location: str
    conference: str  # "AFC" | "NFC"
    division: str    # "East" | "North" | "South" | "West"


TEAMS: list[TeamInfo] = [
    TeamInfo("BUF", "Buffalo", "AFC", "East"),
    TeamInfo("MIA", "Miami", "AFC", "East"),
    TeamInfo("NE", "New England", "AFC", "East"),
    TeamInfo("NYJ", "New York", "AFC", "East"),
    TeamInfo("BAL", "Baltimore", "AFC", "North"),
    TeamInfo("CIN", "Cincinnati", "AFC", "North"),
    TeamInfo("CLE", "Cleveland", "AFC", "North"),
    TeamInfo("PIT", "Pittsburgh", "AFC", "North"),
    TeamInfo("HOU", "Houston", "AFC", "South"),
    TeamInfo("IND", "Indianapolis", "AFC", "South"),
    TeamInfo("JAX", "Jacksonville", "AFC", "South"),
    TeamInfo("TEN", "Tennessee", "AFC", "South"),
    TeamInfo("DEN", "Denver", "AFC", "West"),
    TeamInfo("KC", "Kansas City", "AFC", "West"),
    TeamInfo("LV", "Las Vegas", "AFC", "West"),
    TeamInfo("LAC", "Los Angeles", "AFC", "West"),
    TeamInfo("DAL", "Dallas", "NFC", "East"),
    TeamInfo("NYG", "New York", "NFC", "East"),
    TeamInfo("PHI", "Philadelphia", "NFC", "East"),
    TeamInfo("WAS", "Washington", "NFC", "East"),
    TeamInfo("CHI", "Chicago", "NFC", "North"),
    TeamInfo("DET", "Detroit", "NFC", "North"),
    TeamInfo("GB", "Green Bay", "NFC", "North"),
    TeamInfo("MIN", "Minnesota", "NFC", "North"),
    TeamInfo("ATL", "Atlanta", "NFC", "South"),
    TeamInfo("CAR", "Carolina", "NFC", "South"),
    TeamInfo("NO", "New Orleans", "NFC", "South"),
    TeamInfo("TB", "Tampa Bay", "NFC", "South"),
    TeamInfo("ARI", "Arizona", "NFC", "West"),
    TeamInfo("LAR", "Los Angeles", "NFC", "West"),
    TeamInfo("SEA", "Seattle", "NFC", "West"),
    TeamInfo("SF", "San Francisco", "NFC", "West"),
]

TEAMS_BY_ABBR: dict[str, TeamInfo] = {t.abbr: t for t in TEAMS}
