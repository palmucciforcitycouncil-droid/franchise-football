"""
Weather (GDD Part 1 Sec 6.9.2 / Part 2, ROADMAP.md R7): deterministic
per-game weather, generated the same way every other seeded system in
this engine is (app/engine/rng.py's stable_seed) -- the same matchup in
the same week of the same league always gets the same forecast.

STADIUM_DATA is real, public reference data (each team's actual home
stadium, its city/latitude, and whether it's Outdoor/Dome/Retractable
Roof as of the 2025 season) -- not fabricated. What's genuinely
generated, and disclosed as such: there's no real historical weather
data set behind any of this, so month-by-month temperature/precipitation
odds are this module's own simplified, latitude-and-month heuristic, not
a real meteorological model or a GDD-literal formula (Sec 6.9.2 names the
7 presets and their gameplay modifiers but not how often each should
occur).

Presets: Clear, Hot/Humid, Cold, Rain, Heavy Rain, Snow, Windy, plus the
"Dome" case (always neutral -- an indoor game has no weather at all,
whether the stadium is a true fixed dome or a retractable-roof stadium
that happened to close its roof this game).
"""
from __future__ import annotations
import random
from dataclasses import dataclass

from app.engine.rng import stable_seed

# Real 2025-season NFL stadiums: (name, city/region, latitude, roof type).
# Roof type is one of "Outdoor" / "Dome" / "Retractable" -- "Dome" covers
# both a true fixed dome (LV, DET, MIN, NO) and a fixed-roof stadium that
# is never open (LAC/LAR's shared SoFi Stadium has a translucent but
# fixed roof, not an operable one -- functionally a dome for weather
# purposes, matching how the NFL itself treats it).
STADIUM_DATA: dict[str, dict] = {
    "BUF": {"name": "Highmark Stadium", "region": "Orchard Park, NY", "latitude": 42.77, "roof": "Outdoor"},
    "MIA": {"name": "Hard Rock Stadium", "region": "Miami Gardens, FL", "latitude": 25.96, "roof": "Outdoor"},
    "NE": {"name": "Gillette Stadium", "region": "Foxborough, MA", "latitude": 42.09, "roof": "Outdoor"},
    "NYJ": {"name": "MetLife Stadium", "region": "East Rutherford, NJ", "latitude": 40.81, "roof": "Outdoor"},
    "BAL": {"name": "M&T Bank Stadium", "region": "Baltimore, MD", "latitude": 39.28, "roof": "Outdoor"},
    "CIN": {"name": "Paycor Stadium", "region": "Cincinnati, OH", "latitude": 39.10, "roof": "Outdoor"},
    "CLE": {"name": "Huntington Bank Field", "region": "Cleveland, OH", "latitude": 41.51, "roof": "Outdoor"},
    "PIT": {"name": "Acrisure Stadium", "region": "Pittsburgh, PA", "latitude": 40.45, "roof": "Outdoor"},
    "HOU": {"name": "NRG Stadium", "region": "Houston, TX", "latitude": 29.68, "roof": "Retractable"},
    "IND": {"name": "Lucas Oil Stadium", "region": "Indianapolis, IN", "latitude": 39.76, "roof": "Retractable"},
    "JAX": {"name": "EverBank Stadium", "region": "Jacksonville, FL", "latitude": 30.32, "roof": "Outdoor"},
    "TEN": {"name": "Nissan Stadium", "region": "Nashville, TN", "latitude": 36.17, "roof": "Outdoor"},
    "DEN": {"name": "Empower Field at Mile High", "region": "Denver, CO", "latitude": 39.74, "roof": "Outdoor"},
    "KC": {"name": "GEHA Field at Arrowhead Stadium", "region": "Kansas City, MO", "latitude": 39.05, "roof": "Outdoor"},
    "LV": {"name": "Allegiant Stadium", "region": "Paradise, NV", "latitude": 36.09, "roof": "Dome"},
    "LAC": {"name": "SoFi Stadium", "region": "Inglewood, CA", "latitude": 33.95, "roof": "Dome"},
    "DAL": {"name": "AT&T Stadium", "region": "Arlington, TX", "latitude": 32.75, "roof": "Retractable"},
    "NYG": {"name": "MetLife Stadium", "region": "East Rutherford, NJ", "latitude": 40.81, "roof": "Outdoor"},
    "PHI": {"name": "Lincoln Financial Field", "region": "Philadelphia, PA", "latitude": 39.90, "roof": "Outdoor"},
    "WAS": {"name": "Commanders Field", "region": "Landover, MD", "latitude": 38.91, "roof": "Outdoor"},
    "CHI": {"name": "Soldier Field", "region": "Chicago, IL", "latitude": 41.86, "roof": "Outdoor"},
    "DET": {"name": "Ford Field", "region": "Detroit, MI", "latitude": 42.34, "roof": "Dome"},
    "GB": {"name": "Lambeau Field", "region": "Green Bay, WI", "latitude": 44.50, "roof": "Outdoor"},
    "MIN": {"name": "U.S. Bank Stadium", "region": "Minneapolis, MN", "latitude": 44.97, "roof": "Dome"},
    "ATL": {"name": "Mercedes-Benz Stadium", "region": "Atlanta, GA", "latitude": 33.76, "roof": "Retractable"},
    "CAR": {"name": "Bank of America Stadium", "region": "Charlotte, NC", "latitude": 35.23, "roof": "Outdoor"},
    "NO": {"name": "Caesars Superdome", "region": "New Orleans, LA", "latitude": 29.95, "roof": "Dome"},
    "TB": {"name": "Raymond James Stadium", "region": "Tampa, FL", "latitude": 27.98, "roof": "Outdoor"},
    "ARI": {"name": "State Farm Stadium", "region": "Glendale, AZ", "latitude": 33.53, "roof": "Retractable"},
    "LAR": {"name": "SoFi Stadium", "region": "Inglewood, CA", "latitude": 33.95, "roof": "Dome"},
    "SEA": {"name": "Lumen Field", "region": "Seattle, WA", "latitude": 47.60, "roof": "Outdoor"},
    "SF": {"name": "Levi's Stadium", "region": "Santa Clara, CA", "latitude": 37.40, "roof": "Outdoor"},
}

# GDD Sec 6.9.2's 7 presets, each with the drive_sim.py outcome modifiers
# it nudges: pass_acc (added to completion %), fumble (added to fumble
# rate), fg (added to kick-make probability, FG and PAT alike -- see
# drive_sim.py's own _kicker_adjusted_prob docstring on why a PAT is
# treated as a short FG), run (a fractional bump to a run's mean yards),
# fatigue (folded into pass-rush pressure -- this engine has no separate
# per-play stamina-decay model to hook a real fatigue effect into, so a
# tiring offensive line giving up more pressure is this module's
# disclosed stand-in). cramp_risk/aggression_down are carried for
# display/documentation only -- no cramp or aggression system exists in
# this engine to wire them into.
PRESETS: dict[str, dict[str, float]] = {
    "Clear":      {"pass_acc": 0.0,   "fumble": 0.0,  "fg": 0.0,   "run": 0.0,  "fatigue": 0.0},
    "Hot/Humid":  {"pass_acc": 0.0,   "fumble": 0.0,  "fg": -0.03, "run": 0.0,  "fatigue": 0.10, "cramp_risk": 0.03},
    "Cold":       {"pass_acc": -0.05, "fumble": 0.0,  "fg": -0.05, "run": 0.0,  "fatigue": 0.0},
    "Rain":       {"pass_acc": -0.05, "fumble": 0.07, "fg": -0.05, "run": 0.0,  "fatigue": 0.0},
    "Heavy Rain": {"pass_acc": -0.12, "fumble": 0.12, "fg": -0.10, "run": 0.0,  "fatigue": 0.0, "aggression_down": 1},
    "Snow":       {"pass_acc": -0.10, "fumble": 0.05, "fg": -0.10, "run": 0.05, "fatigue": 0.0},
    "Windy":      {"pass_acc": -0.08, "fumble": 0.0,  "fg": -0.12, "run": 0.0,  "fatigue": 0.0},
}

INDOOR_TEMP_F = 72


@dataclass(frozen=True)
class Weather:
    preset: str
    temp_f: int | None       # None only for a "Dome"/roof-closed game
    wind_mph: int | None
    precip: str | None       # None | "rain" | "snow"
    is_indoors: bool
    roof_closed: bool = False  # True only for a Retractable stadium that rolled a closed roof

    def get_modifiers(self) -> dict[str, float]:
        return PRESETS.get(self.preset, PRESETS["Clear"])

    def summary(self) -> str:
        """The Scouting Panel / Box Score header's own display string --
        "Indoors" for a dome or a closed retractable roof, "Outdoors,
        45°F, rain" (temp + precip + notable wind) otherwise."""
        if self.is_indoors:
            return "Indoors"
        parts = [f"{self.temp_f}°F"]
        if self.precip:
            parts.append(self.precip)
        if self.wind_mph and self.wind_mph >= 15:
            parts.append(f"{self.wind_mph} mph wind")
        return "Outdoors, " + ", ".join(parts)


def _indoor_weather(roof_closed: bool = False) -> Weather:
    return Weather(preset="Clear", temp_f=INDOOR_TEMP_F, wind_mph=0, precip=None,
                   is_indoors=True, roof_closed=roof_closed)


# Real NFL season calendar (Week 1 ~ early September, Week 18 ~ early
# January) mapped onto real calendar months -- deliberately coarse (a
# 4-5 week bucket per month) rather than exact per-week dates, since
# only the MONTH is actually used below (temperature/precip trend).
_MONTH_FOR_WEEK: dict[int, int] = {
    **{w: 9 for w in range(1, 5)},
    **{w: 10 for w in range(5, 9)},
    **{w: 11 for w in range(9, 14)},
    **{w: 12 for w in range(14, 18)},
    18: 1,
}


def _month_for_week(week: int) -> int:
    return _MONTH_FOR_WEEK.get(week, 9 if week < 1 else 1)


# This module's own disclosed heuristic (no GDD formula, no real
# historical weather data set) for how cold a given month/latitude
# combination trends -- later months and higher (more northern)
# latitudes trend colder, with real per-game noise on top.
_MONTH_COLD_OFFSET: dict[int, float] = {9: 0.0, 10: -8.0, 11: -16.0, 12: -22.0, 1: -26.0}


def _base_temp_f(month: int, latitude: float, rng: random.Random) -> int:
    base = 78.0 + _MONTH_COLD_OFFSET.get(month, 0.0) - (latitude - 30.0) * 0.9
    return int(round(base + rng.gauss(0.0, 8.0)))


def _select_preset(temp_f: int, rng: random.Random) -> tuple[str, float, str | None, int]:
    """Returns (preset, precip_roll, precip_kind, wind_mph). precip_roll
    is also what a Retractable stadium's roof decision (_should_roof_close)
    reacts to -- a low roll means this game rolled real precipitation,
    regardless of which preset it ultimately became."""
    precip_roll = rng.random()
    wind_mph = int(rng.uniform(20, 35)) if rng.random() < 0.10 else int(rng.uniform(0, 12))

    if temp_f <= 34:
        if precip_roll < 0.25:
            return "Snow", precip_roll, "snow", wind_mph
        return "Cold", precip_roll, None, wind_mph
    if temp_f >= 85:
        return "Hot/Humid", precip_roll, None, wind_mph
    if precip_roll < 0.12:
        return "Heavy Rain", precip_roll, "rain", wind_mph
    if precip_roll < 0.30:
        return "Rain", precip_roll, "rain", wind_mph
    if wind_mph >= 20:
        return "Windy", precip_roll, None, wind_mph
    return "Clear", precip_roll, None, wind_mph


def _should_roof_close(precip_roll: float, rng: random.Random) -> bool:
    """GDD Sec 6.9.2: "50% chance roof closed if precipitation
    probability > 40%". precip_roll is this game's own roll from
    _select_preset -- a LOW roll is what produced Rain/Heavy Rain/Snow
    there, so "precipitation probability" is read as 1 - precip_roll
    (how far into that game's precipitation-favoring range the roll
    landed)."""
    precip_probability = 1.0 - precip_roll
    if precip_probability > 0.4:
        return rng.random() < 0.5
    return False


def generate_weather(league_seed: int, season_number: int, week: int, home_team_abbr: str) -> Weather:
    """Deterministic weather for one game, keyed off the same real
    inputs every other per-week seeded system in this engine uses
    (league_seed, season_number, week) plus the home team, since weather
    is a property of the home team's stadium/climate, not either
    roster."""
    stadium = STADIUM_DATA[home_team_abbr]
    seed = stable_seed(league_seed, season_number, week, home_team_abbr, "weather")
    rng = random.Random(seed)

    if stadium["roof"] == "Dome":
        return _indoor_weather()

    month = _month_for_week(week)
    temp_f = _base_temp_f(month, stadium["latitude"], rng)
    preset, precip_roll, precip, wind_mph = _select_preset(temp_f, rng)

    if stadium["roof"] == "Retractable" and _should_roof_close(precip_roll, rng):
        return _indoor_weather(roof_closed=True)

    return Weather(preset=preset, temp_f=temp_f, wind_mph=wind_mph, precip=precip, is_indoors=False)
