"""
Offseason-start headlines (Brian's ask, 2026-09-14): when the offseason
begins, the Dashboard's Headlines box leads with who won the Super Bowl
(and the score), the Super Bowl MVP, and the season's major award
winners.

Deliberately its own module rather than more templates inside
app/engine/headlines.py: that module is the weekly event-detection/
scoring pipeline, while this is a fixed, once-a-season summary built
from already-frozen results (app/services/honors_store.py) -- nothing
to detect or rank. Plain deterministic strings, same no-LLM convention.
"""
from __future__ import annotations

from app.data.teams import TEAMS_BY_ABBR

_AWARD_HEADLINES = [
    ("mvp", "{name} ({pos}, {team}) is named league MVP"),
    ("opoy", "{name} ({pos}, {team}) wins Offensive Player of the Year"),
    ("dpoy", "{name} ({team}) takes home Defensive Player of the Year"),
    ("oroy", "{name} ({pos}, {team}) is Offensive Rookie of the Year"),
    ("droy", "{name} ({team}) is Defensive Rookie of the Year"),
]


def _location(abbr: str | None) -> str:
    info = TEAMS_BY_ABBR.get(abbr or "")
    return info.location if info else (abbr or "")


def season_end_headlines(season_year: int, super_bowl: dict | None, final_awards: dict | None) -> list[str]:
    lines: list[str] = []
    if super_bowl and super_bowl.get("winner_abbr"):
        lines.append(
            f"{_location(super_bowl['winner_abbr'])} win Super Bowl {super_bowl.get('numeral', '')}, "
            f"beating {_location(super_bowl['loser_abbr'])} "
            f"{super_bowl['winner_score']}-{super_bowl['loser_score']}".replace("  ", " ")
        )
        mvp = super_bowl.get("mvp")
        if mvp:
            pos = f" ({mvp['position']})" if mvp.get("position") else ""
            line = f"{mvp['name']}{pos} named Super Bowl MVP"
            if mvp.get("stat_line"):
                line += f": {mvp['stat_line']}"
            lines.append(line)

    if final_awards:
        for key, template in _AWARD_HEADLINES:
            cands = final_awards.get(key) or []
            if not cands:
                continue
            c = cands[0]
            line = template.format(name=c["name"], pos=c.get("player_position") or c.get("position", ""), team=c["team_abbr"])
            if c.get("stat_line"):
                line += f" ({c['stat_line']})"
            lines.append(line)
        coty = final_awards.get("coty") or []
        if coty:
            lines.append(f"{coty[0]['name']} ({coty[0]['team_abbr']}, {coty[0]['record']}) is Coach of the Year")

    if not lines:
        lines.append(f"The {season_year} season is in the books.")
    return lines
