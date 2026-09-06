"""
Starting lineup selection.

The GDD's play-calling AI (Part 1 Sec 6.6) references specific matchups --
"LT & LG vs. opponent RDE & RDT", "WR1 vs. CB1" -- which requires knowing
which specific players are on the field, not just team-level aggregates.
There's no coach-assigned depth chart yet (that's a real future feature:
letting the user set it), so starters are chosen by highest overall_rating
per position, which is a reasonable stand-in until that exists.

11 offensive starters (11-personnel: 1 RB, 1 TE, 3 WR) and 11 defensive
starters (a 4-3-ish base: 2 DT, 2 edge, 3 LB, 2 CB, 2 S) are selected per
team and cached, since a full roster query + sort per team is wasted work
to repeat every play.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache

from sqlmodel import select

from app.core.db import get_session
from app.models.player import Player, Position


@dataclass
class OffensiveStarters:
    qb: Player
    hb: Player
    wr1: Player
    wr2: Player
    wr3: Player | None
    te: Player
    lt: Player
    lg: Player
    c: Player
    rg: Player
    rt: Player

    @property
    def receivers(self) -> list[Player]:
        return [p for p in [self.wr1, self.wr2, self.wr3, self.te] if p is not None]

    @property
    def offensive_line(self) -> list[Player]:
        return [self.lt, self.lg, self.c, self.rg, self.rt]


@dataclass
class DefensiveStarters:
    dt1: Player
    dt2: Player
    le: Player
    re: Player
    lolb: Player
    mlb: Player
    rolb: Player
    cb1: Player
    cb2: Player
    fs: Player
    ss: Player

    @property
    def defensive_line(self) -> list[Player]:
        return [self.dt1, self.dt2, self.le, self.re]

    @property
    def linebackers(self) -> list[Player]:
        return [self.lolb, self.mlb, self.rolb]

    @property
    def secondary(self) -> list[Player]:
        return [self.cb1, self.cb2, self.fs, self.ss]


def _top(players: list[Player], position: Position, n: int = 1) -> list[Player]:
    pool = sorted((p for p in players if p.position == position), key=lambda p: -p.overall_rating)
    return pool[:n]


def _load_roster(team_abbr: str) -> list[Player]:
    with get_session() as s:
        return list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))


@lru_cache(maxsize=64)
def get_offensive_starters(team_abbr: str) -> OffensiveStarters:
    roster = _load_roster(team_abbr)
    wrs = _top(roster, Position.WR, 3)
    return OffensiveStarters(
        qb=_top(roster, Position.QB, 1)[0],
        hb=_top(roster, Position.HB, 1)[0],
        wr1=wrs[0], wr2=wrs[1], wr3=wrs[2] if len(wrs) > 2 else None,
        te=_top(roster, Position.TE, 1)[0],
        lt=_top(roster, Position.LT, 1)[0],
        lg=_top(roster, Position.LG, 1)[0],
        c=_top(roster, Position.C, 1)[0],
        rg=_top(roster, Position.RG, 1)[0],
        rt=_top(roster, Position.RT, 1)[0],
    )


@lru_cache(maxsize=64)
def get_defensive_starters(team_abbr: str) -> DefensiveStarters:
    roster = _load_roster(team_abbr)
    dts = _top(roster, Position.DT, 2)
    cbs = _top(roster, Position.CB, 2)
    return DefensiveStarters(
        dt1=dts[0], dt2=dts[1],
        le=_top(roster, Position.LE, 1)[0],
        re=_top(roster, Position.RE, 1)[0],
        lolb=_top(roster, Position.LOLB, 1)[0],
        mlb=_top(roster, Position.MLB, 1)[0],
        rolb=_top(roster, Position.ROLB, 1)[0],
        cb1=cbs[0], cb2=cbs[1],
        fs=_top(roster, Position.FS, 1)[0],
        ss=_top(roster, Position.SS, 1)[0],
    )


def clear_starters_cache() -> None:
    get_offensive_starters.cache_clear()
    get_defensive_starters.cache_clear()
