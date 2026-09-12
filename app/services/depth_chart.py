"""
Starting lineup selection.

The GDD's play-calling AI (Part 1 Sec 6.6) references specific matchups --
"LT & LG vs. opponent RDE & RDT", "WR1 vs. CB1" -- which requires knowing
which specific players are on the field, not just team-level aggregates.
Starters are chosen by highest overall_rating per position by default,
overridable per (team, position) via depth_chart_overrides.py (the real
coach-settable depth chart, GET/POST /depth-chart in app/main.py) -- see
that module's docstring for the persistence format.

11 offensive starters (11-personnel: 1 RB, 1 TE, 3 WR), a kicker and punter,
and 11 defensive starters (a 4-3-ish base: 2 DT, 2 edge, 3 LB, 2 CB, 2 S) are
selected per team and cached, since a full roster query + sort per team
is wasted work to repeat every play.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache

from sqlmodel import select

from app.core.db import get_session
from app.models.player import Player, Position
from app.services import depth_chart_overrides


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
    k: Player  # not part of the 11-man personnel package -- see class docstring history; used for FG/PAT odds
    p: Player  # same as k above; used for box_score.py's Punting line (ROADMAP.md M2)
    # Real roster-depth rotation pools (app/engine/rotation.py) -- rank-
    # ordered, `hb`/`wr1..3`/`te` above stay as the nominal "starter" for
    # display/matchup purposes, but ball-carrier and target selection
    # draws from these full pools so a team's touches spread across a
    # realistic committee/corps instead of one fixed player all season.
    hb_depth: list[Player] = field(default_factory=list)
    wr_depth: list[Player] = field(default_factory=list)
    te_depth: list[Player] = field(default_factory=list)

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
    # Real roster-depth rotation (app/engine/rotation.py): real backups
    # (0-2) per rotation-eligible slot, keyed by slot name ("dt1", "dt2",
    # "le", "re", "lolb", "mlb", "rolb", "cb1", "cb2") -- an empty/
    # missing list means no real backup exists on this roster (falls
    # back to the starter alone). FS/SS deliberately excluded: real
    # safeties rotate the least of any defensive position, closest to
    # "iron man."
    backups: dict[str, list[Player]] = field(default_factory=dict)

    @property
    def defensive_line(self) -> list[Player]:
        return [self.dt1, self.dt2, self.le, self.re]

    @property
    def linebackers(self) -> list[Player]:
        return [self.lolb, self.mlb, self.rolb]

    @property
    def secondary(self) -> list[Player]:
        return [self.cb1, self.cb2, self.fs, self.ss]


def _top(players: list[Player], position: Position, n: int, team_abbr: str) -> list[Player]:
    """R1 (GDD Sec 6.10.5): a player who is currently OUT (an active
    injury with weeks_out > 0) is excluded from this position's pool, so
    selection "promotes the next slot" for free via the existing
    rating-sorted fallback -- no separate promotion logic needed.
    Backfills with OUT players (rating-sorted, via resolve_order's own
    fallback) if the healthy pool alone can't fill all `n` slots -- rare
    with real roster depth, but real (a thin position, e.g. DT needs 2;
    a bad-luck injury cluster on one team), and this engine has no
    practice-squad emergency-elevation system to reach for instead. The
    disclosed simplification is fielding an available body anyway rather
    than crashing an empty starter slot -- caught via two real
    IndexErrors on this feature's own first live full-season runs (an
    all-hurt single-starter position, then an under-filled 2-starter
    one)."""
    from app.services import injury_store

    pool = [p for p in players if p.position == position]
    out_ids = injury_store.currently_out_player_ids()
    healthy = [p for p in pool if p.player_id not in out_ids] if out_ids else pool
    if len(healthy) < n:
        healthy_ids = {p.player_id for p in healthy}
        candidates = healthy + [p for p in pool if p.player_id not in healthy_ids]
    else:
        candidates = healthy
    candidates = depth_chart_overrides.resolve_order(team_abbr, position.value, candidates)
    return candidates[:n]


def _load_roster(team_abbr: str) -> list[Player]:
    """A player currently in RTP taper (available, but weakened --
    weeks_out == 0, rtp_penalty > 0 -- R1, GDD Sec 6.10.4) has their
    attributes temporarily scaled here, per injuries.py's
    apply_rtp_penalty(). OUT-player exclusion happens in _top() instead
    of here -- see that function's own docstring for why (a per-position
    fallback needs to know "is EVERY player at just this slot out," which
    a whole-roster filter can't express)."""
    from app.engine import injuries
    from app.services import injury_store

    with get_session() as s:
        roster = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))

    rtp = injury_store.rtp_penalties()
    if rtp:
        roster = [
            injuries.apply_rtp_penalty(p, rtp[p.player_id]) if p.player_id in rtp else p
            for p in roster
        ]
    return roster


@lru_cache(maxsize=64)
def get_offensive_starters(team_abbr: str) -> OffensiveStarters:
    roster = _load_roster(team_abbr)
    wrs = _top(roster, Position.WR, 5, team_abbr)
    hbs = _top(roster, Position.HB, 3, team_abbr)
    tes = _top(roster, Position.TE, 2, team_abbr)
    return OffensiveStarters(
        qb=_top(roster, Position.QB, 1, team_abbr)[0],
        hb=hbs[0],
        wr1=wrs[0], wr2=wrs[1], wr3=wrs[2] if len(wrs) > 2 else None,
        te=tes[0],
        lt=_top(roster, Position.LT, 1, team_abbr)[0],
        lg=_top(roster, Position.LG, 1, team_abbr)[0],
        c=_top(roster, Position.C, 1, team_abbr)[0],
        rg=_top(roster, Position.RG, 1, team_abbr)[0],
        rt=_top(roster, Position.RT, 1, team_abbr)[0],
        k=_top(roster, Position.K, 1, team_abbr)[0],
        p=_top(roster, Position.P, 1, team_abbr)[0],
        hb_depth=hbs, wr_depth=wrs, te_depth=tes,
    )


def _slot_backups(roster: list[Player], team_abbr: str) -> dict[str, list[Player]]:
    """Real backups (up to 2 each) per rotation-eligible defensive slot
    -- see DefensiveStarters.backups' own docstring for why FS/SS are
    excluded. dt1/dt2 and cb1/cb2 share one position pool each (both
    starters are the same Position value), so their backups are drawn
    from the same pool split in depth order (3rd/4th-best DT backs up
    dt1/dt2 respectively, 5th/6th back them up further, etc.) -- a
    disclosed simplification, not positionally exact."""
    dts = _top(roster, Position.DT, 6, team_abbr)
    cbs = _top(roster, Position.CB, 6, team_abbr)
    les = _top(roster, Position.LE, 3, team_abbr)
    res = _top(roster, Position.RE, 3, team_abbr)
    lolbs = _top(roster, Position.LOLB, 3, team_abbr)
    mlbs = _top(roster, Position.MLB, 3, team_abbr)
    rolbs = _top(roster, Position.ROLB, 3, team_abbr)
    return {
        "dt1": dts[2::2][:2],   # 3rd, 5th-best DT
        "dt2": dts[3::2][:2],   # 4th, 6th-best DT
        "le": les[1:],
        "re": res[1:],
        "lolb": lolbs[1:],
        "mlb": mlbs[1:],
        "rolb": rolbs[1:],
        "cb1": cbs[2::2][:2],
        "cb2": cbs[3::2][:2],
    }


@lru_cache(maxsize=64)
def get_defensive_starters(team_abbr: str) -> DefensiveStarters:
    roster = _load_roster(team_abbr)
    dts = _top(roster, Position.DT, 2, team_abbr)
    cbs = _top(roster, Position.CB, 2, team_abbr)
    return DefensiveStarters(
        dt1=dts[0], dt2=dts[1],
        le=_top(roster, Position.LE, 1, team_abbr)[0],
        re=_top(roster, Position.RE, 1, team_abbr)[0],
        lolb=_top(roster, Position.LOLB, 1, team_abbr)[0],
        mlb=_top(roster, Position.MLB, 1, team_abbr)[0],
        rolb=_top(roster, Position.ROLB, 1, team_abbr)[0],
        cb1=cbs[0], cb2=cbs[1],
        fs=_top(roster, Position.FS, 1, team_abbr)[0],
        ss=_top(roster, Position.SS, 1, team_abbr)[0],
        backups=_slot_backups(roster, team_abbr),
    )


def clear_starters_cache() -> None:
    get_offensive_starters.cache_clear()
    get_defensive_starters.cache_clear()
    # R1: starters now depend on injury_store's cache too (_top() reads
    # it every call), and every existing test fixture that resets DB_PATH
    # already calls this function -- coupling the two here means those
    # fixtures correctly clear injury_store's cache too without needing
    # to know that module exists. Import kept local: depth_chart.py is a
    # dependency of injury_store's own _load_roster()-adjacent code, so a
    # module-level import here would risk a circular import.
    from app.services import injury_store
    injury_store.clear_cache()
