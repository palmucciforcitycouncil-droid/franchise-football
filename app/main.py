from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

from dotenv import load_dotenv
load_dotenv()

from markupsafe import Markup, escape
from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_league_seed
from app.data.teams import TEAMS, TEAMS_BY_ABBR, TeamInfo
from app.engine.placeholder_ratings import ratings_for
from app.engine.position_groups import POSITION_TO_GROUP, QUOTA_GROUPS
from app.engine import roster_strength, contracts
from app.engine.rng import RNG, stable_seed
from app.engine.game_sim import simulate_game, TeamSim
from app.engine.game_state import quarter_scores
from app.engine.box_score import build_box_score
from app.engine.defensive_box_score import build_defensive_box_score
from app.engine.season_stats import aggregate_season_stats, aggregate_season_defensive_stats
from app.engine import season_stats
from app.engine import score_fidelity, awards
from app.engine.playoffs import bubble_teams, build_wild_card_round, final_division_standings, seed_conference
from app.engine.scouting import find_next_opponent, build_scouting_report
from app.engine.gameplan import (
    Gameplan, OFFENSIVE_AGGRESSIVENESS, DEFENSIVE_AGGRESSIVENESS,
    COVERAGE_SCHEMES, BLITZ_STRATEGIES, RZ_OFFENSE_STYLES, RZ_DEFENSE_STYLES,
)
from app.engine.progression import PROGRESSED_ATTRIBUTES
from app.services import (
    season_state, depth_chart_overrides, gameplan_store, history_store, power_rank_history,
    coach_store, coach_records, injury_store,
)
from app.services.depth_chart import clear_starters_cache
from app.core.db import get_session
from app.models.player import Player, Position
from app.models.coach import Coach, CoachRole, ROLE_TITLES
from sqlmodel import select

app = FastAPI(title="Franchise Football")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"teams": TEAMS})


FREE_AGENTS_TEAM = TeamInfo(abbr="FA", location="Free Agents", conference="", division="")

# How many players at each position actually start, per depth_chart.py's
# OffensiveStarters/DefensiveStarters (wr1/wr2/wr3, dt1/dt2, cb1/cb2) --
# every other position starts exactly one. Used to highlight the right
# NUMBER of starters on /roster and /depth-chart, not just the top player
# at every position regardless of how many the engine actually plays.
STARTER_COUNTS: dict[Position, int] = {Position.WR: 3, Position.DT: 2, Position.CB: 2}

# Position roster minimums for Team Quota badges (M4: Figma RosterPage.tsx)
_ROSTER_POSITION_MINIMUMS: dict[str, int] = {
    "QB": 2, "RB": 3, "WR": 5, "TE": 2, "C": 1, "G": 2, "T": 2,
    "DE": 2, "DT": 1, "LB": 6, "CB": 4, "S": 4, "K": 1, "P": 1,
}

# M11 correction: Team Quota pills need a GENERIC group per player --
# `_ROSTER_POSITION_MINIMUMS` above was always keyed by these generic
# labels, but the original M4 build counted players by their RAW
# Position enum value (QB/HB/FB/WR/TE/LT/LG/C/RG/RT/LE/RE/DT/LOLB/MLB/
# ROLB/CB/FS/SS/K/P -- Madden's granular scheme, see player.py's own
# docstring for why it's kept that granular). Since the minimums dict
# has no "HB"/"LT"/"LOLB"/etc keys, 6 of 14 pills (RB/G/T/DE/LB/S) never
# matched anything and silently never rendered -- a real, previously-
# unnoticed bug, not a stale-doc issue like M9's. This mapping is what
# was actually missing. Now shared with app/engine/roster_strength.py
# via app/engine/position_groups.py rather than defined here alone.
_QUOTA_GROUP_FOR_POSITION = POSITION_TO_GROUP

# Free Agents box's OFF/DEF split (offense skill/line groups vs. defensive
# front/secondary groups). K/P don't cleanly belong to either side of the
# ball -- grouped under OFF here rather than inventing a third bucket the
# UI doesn't offer, same "don't add a filter option nothing asked for"
# discipline as everywhere else on this page.
FA_OFFENSE_GROUPS = {"QB", "RB", "WR", "TE", "C", "G", "T", "K", "P"}
FA_DEFENSE_GROUPS = {"DE", "DT", "LB", "CB", "S"}

# The real Figma source uses a SECOND, coarser 10-group breakdown for the
# Filter panel's position checkboxes and the Top Free Agents pager
# (FilterPanel.tsx's own `positions` list collapses OL/DL/ST further than
# the Team Quota pills' 14-group split does). Deliberately NOT reproduced
# as a second grouping here: a quota pill and a filter checkbox sharing
# one `position` query param but two different label spaces (e.g. a "G"
# pill setting `position=G`, which the 10-group filter would never match)
# is a real bug, not a faithfulness nice-to-have -- so both widgets share
# QUOTA_GROUPS/_QUOTA_GROUP_FOR_POSITION instead. Finer-grained than
# Figma's filter panel, not a regression.

MAX_ROSTER_SIZE = 53  # the real NFL active-roster limit (RosterTable.tsx's
                       # own hardcoded constant) -- not fabricated per-team
                       # data, just an unenforced real-world number this
                       # engine doesn't cap rosters against yet.

# Column ids sortable via the Roster table's header links (RosterTable.tsx's
# own `handleSort` keys), GET-param + full-page-reload like Stats' M3
# precedent -- not client JS state.
ROSTER_SORT_KEYS = (
    "num", "name", "pos", "age", "ovr", "pot", "spd", "str", "agi",
    "tpw", "tac", "cth", "tck", "awr", "sta", "inj", "mor", "ctr", "yrs", "dep",
)

# Same id/label pairs as roster.html's own inline main-table header list,
# centralized here (R11, GDD Sec 11) so the new Find Player "Sort by"
# dropdown can reuse ROSTER_SORT_KEYS' labels without a second hand-typed
# copy -- the main table's own header stays as its existing inline list
# (not worth the risk of touching already-working, already-tested markup
# just to DRY up one string list).
ROSTER_SORT_COLUMN_LABELS = (
    ("num", "#"), ("name", "Player"), ("pos", "Pos"), ("age", "Age"), ("ovr", "OVR"), ("pot", "POT"),
    ("spd", "SPD"), ("str", "STR"), ("agi", "AGI"), ("tpw", "TPW"), ("tac", "TAC"), ("cth", "CTH"),
    ("tck", "TCK"), ("awr", "AWR"), ("sta", "STA"), ("inj", "INJ"), ("mor", "MOR"), ("ctr", "Contract"),
    ("yrs", "Yrs"), ("dep", "Depth"),
)


def _int_or_none(raw: str | None) -> int | None:
    """Blank <input type="number"> fields submit as "" (a real, empty
    query-param value), not an omitted param -- FastAPI's `int | None`
    coercion rejects that outright, so range-filter params come in as
    plain strings and get converted here instead."""
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _roster_avg_throw_accuracy(p: Player) -> int:
    """RosterTable.tsx's TAC column -- not a single modeled attribute on
    Player, but a real, disclosed average of the three throw-accuracy
    splits the model already has (short/mid/deep), not a fabricated one."""
    return round((p.throw_accuracy_short + p.throw_accuracy_mid + p.throw_accuracy_deep) / 3)


def _roster_injury_risk(p: Player) -> int:
    """RosterTable.tsx's INJ column, read the opposite direction from our
    real `durability` field per Player's own module docstring formula
    (`proneness = 99 - durability`) -- the same real data, not a second
    modeled attribute."""
    return 99 - p.durability


def _roster_sort_value(p: Player, key: str, depth_slot: dict[str, str]):
    return {
        "num": p.jersey_number, "name": p.full_name.lower(), "pos": p.position.value,
        "age": p.age, "ovr": p.overall_rating, "pot": p.potential, "spd": p.speed,
        "str": p.strength, "agi": p.agility, "tpw": p.throw_power,
        "tac": _roster_avg_throw_accuracy(p), "cth": p.catching, "tck": p.tackle,
        "awr": p.awareness, "sta": p.stamina, "inj": _roster_injury_risk(p),
        "mor": p.morale, "ctr": p.salary, "yrs": p.years_pro,
        "dep": depth_slot.get(p.player_id, ""),
    }.get(key, p.overall_rating)


def _depth_chart_groups_for_team(team_abbr: str, players_on_team: list[Player]) -> list[dict]:
    """Same per-position resolved-order grouping `roster_view`/
    `depth_chart_view` already build for the DEP column and the embedded
    depth-chart widget, factored out so R11's cross-team Find Player
    "dep" sort (below) can call it for whichever OTHER teams a search
    result happens to belong to, without duplicating this logic a third
    time."""
    by_position = defaultdict(list)
    for p in players_on_team:
        by_position[p.position].append(p)
    return [
        {
            "position": pos.value,
            "players": depth_chart_overrides.resolve_order(team_abbr, pos.value, players_at_pos),
            "starter_count": STARTER_COUNTS.get(pos, 1),
        }
        for pos, players_at_pos in sorted(by_position.items(), key=lambda kv: list(Position).index(kv[0]))
    ]


def _slot_labels_from_groups(groups: list[dict]) -> dict[str, str]:
    """{player_id: "QB1"/"QB2"/...} from an already-resolved depth-chart
    groups list (`_depth_chart_groups_for_team`'s return value)."""
    labels: dict[str, str] = {}
    for group in groups:
        for i, p in enumerate(group["players"], start=1):
            labels[p.player_id] = f"{group['position']}{i}"
    return labels


def _depth_slot_across_teams(team_abbrs: set[str]) -> dict[str, str]:
    """R11 (GDD Sec 11): Find Player's results can span every team in the
    league, unlike the main Roster table's single-team DEP column -- this
    computes the real depth-slot label for each team a result actually
    belongs to (each team's OWN full roster, not just the matched search
    results, since depth rank is relative to the whole position group),
    merged into one dict. Only called when "dep" is the actual chosen
    sort column (see roster_view below) -- most searches never need this
    extra per-team DB round-trip."""
    labels: dict[str, str] = {}
    with get_session() as s:
        for abbr in team_abbrs:
            team_players = list(s.exec(select(Player).where(Player.team_abbr == abbr)))
            labels.update(_slot_labels_from_groups(_depth_chart_groups_for_team(abbr, team_players)))
    return labels


def _fa_stat_line_summary(row: dict) -> str:
    """Condensed current-season stat line for the Free Agents box's SOON
    rows (rostered players actually playing games) -- same "only show
    nonzero TD" shorthand convention as `_format_leader_stat_line`, but
    built from `_stats_page_aggregates()`'s season-aggregate row shape
    (a plain dict) rather than a per-game box-score dataclass, and picks
    its stat block by position group instead of a fixed category."""
    pos = row["player_pos"]
    if pos == "QB" and row["pass_att"]:
        parts = [f"{row['pass_cmp']}-{row['pass_att']}", f"{row['pass_yds']} Yds"]
        if row["pass_td"]:
            parts.append(f"{row['pass_td']} TD")
        return ", ".join(parts)
    if pos in ("HB", "FB") and row["rush_att"]:
        parts = [f"{row['rush_att']} Car", f"{row['rush_yds']} Yds"]
        if row["rush_td"]:
            parts.append(f"{row['rush_td']} TD")
        return ", ".join(parts)
    if pos in ("WR", "TE") and row["targets"]:
        parts = [f"{row['receptions']} Rec", f"{row['rec_yds']} Yds"]
        if row["rec_td"]:
            parts.append(f"{row['rec_td']} TD")
        return ", ".join(parts)
    if row["solo_tackles"] or row["sacks"] or row["def_int"]:
        parts = [f"{row['solo_tackles']} Tkl"]
        if row["sacks"]:
            parts.append(f"{row['sacks']} Sck")
        if row["def_int"]:
            parts.append(f"{row['def_int']} Int")
        return ", ".join(parts)
    return ""


@app.get("/roster", response_class=HTMLResponse)
def roster_view(
    request: Request,
    team_abbr: str | None = None,
    view: str = "attributes",
    position: list[str] = Query(default=[]),
    min_ovr: str | None = None, max_ovr: str | None = None,
    min_spd: str | None = None, max_spd: str | None = None,
    min_cth: str | None = None, max_cth: str | None = None,
    min_tck: str | None = None, max_tck: str | None = None,
    rookie: bool = False,
    sort: str | None = None, dir: str = "asc",
    fa_pos: str = "All", fa_status: str = "ALL",
    find_q: str = "", find_pos: str = "all", find_team: str = "all",
    find_min_ovr: str | None = None, find_max_ovr: str | None = None,
    find_min_spd: str | None = None, find_max_spd: str | None = None,
    find_min_cth: str | None = None, find_max_cth: str | None = None,
    find_min_tck: str | None = None, find_max_tck: str | None = None,
    find_rookie: bool = False,
    find_sort: str = "ovr", find_dir: str = "desc",
):
    """Real player data (2,365 players across 32 teams, plus 71 free
    agents) has existed since the roster import but was only ever
    consumed internally by the engine -- this is the first page that
    actually shows it. No team selected yet -> just the picker.
    `team_abbr=FA` is a pseudo-team (Player.team_abbr is None for a free
    agent) rather than a real TEAMS entry -- FREE_AGENTS_TEAM stands in
    so the template's `team.location`/`team.abbr` access works the same
    way for both. `starters` marks the top N highest-overall_rating
    players at each position (STARTER_COUNTS -- 3 for WR, 2 for DT/CB,
    1 otherwise, matching how many depth_chart.py's OffensiveStarters/
    DefensiveStarters actually start at each position) -- always empty
    for free agents, since "starter" isn't a meaningful concept for
    players with no team.

    M11 correction (real source: RosterPage.tsx/RosterTable.tsx/
    FilterPanel.tsx, not M4's simplified build): real Filter panel
    (position groups, OVR/SPD/CTH/TCK ranges, Rookie toggle -- Injured/
    Trade-block toggles stayed omitted, no in-season health or trade
    system exists), clickable Team Quota pills (+ a real ALL/53 pill,
    fixing the quota-count bug described above `_QUOTA_GROUP_FOR_POSITION`),
    sortable/sticky-column table with the 8 real attribute columns M4
    never added (TPW/TAC/CTH/TCK/INJ/MOR/Contract/Depth -- Health/Trade
    columns stay omitted, same disclosed no-real-data reasoning), a
    whole-row click to open the Player Card, and the two of Figma's three
    quick-access boxes with real underlying data (Top Free Agents, Find
    Player -- Trade Block is skipped, no trade system exists, see the
    GM Desk audit note in ROADMAP.md §2b)."""
    # Range-filter inputs render as plain <input type="number"> with no
    # value; a blank one submits as "" (not omitted), which FastAPI can't
    # coerce to `int | None` -- parse as str and treat "" as unset here.
    min_ovr = _int_or_none(min_ovr); max_ovr = _int_or_none(max_ovr)
    min_spd = _int_or_none(min_spd); max_spd = _int_or_none(max_spd)
    min_cth = _int_or_none(min_cth); max_cth = _int_or_none(max_cth)
    min_tck = _int_or_none(min_tck); max_tck = _int_or_none(max_tck)
    find_min_ovr = _int_or_none(find_min_ovr); find_max_ovr = _int_or_none(find_max_ovr)
    find_min_spd = _int_or_none(find_min_spd); find_max_spd = _int_or_none(find_max_spd)
    find_min_cth = _int_or_none(find_min_cth); find_max_cth = _int_or_none(find_max_cth)
    find_min_tck = _int_or_none(find_min_tck); find_max_tck = _int_or_none(find_max_tck)

    if view not in ("attributes", "stats"):
        view = "attributes"
    if team_abbr is None:
        # GDD Sec 10.1: default screen state resolves to the user's team
        # without a picker interaction, once one has been chosen.
        team_abbr = season_state.get_season().user_team_abbr
    if team_abbr is None:
        return templates.TemplateResponse(request, "roster.html", {"teams": TEAMS, "team": None, "players": None, "view": view})
    if team_abbr != "FA" and team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")

    with get_session() as s:
        if team_abbr == "FA":
            players = list(s.exec(select(Player).where(Player.team_abbr == None)))  # noqa: E711 (SQLAlchemy needs `== None`, not `is None`)
        else:
            players = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))

    position_rank = {pos: i for i, pos in enumerate(Position)}
    players.sort(key=lambda p: (position_rank[p.position], -p.overall_rating))

    starters: set[str] = set()
    if team_abbr != "FA":
        seen_counts: dict[Position, int] = {}
        for p in players:
            count_so_far = seen_counts.get(p.position, 0)
            if count_so_far < STARTER_COUNTS.get(p.position, 1):
                starters.add(p.player_id)
            seen_counts[p.position] = count_so_far + 1

    # Team Quota badges: counted by the fixed generic grouping (see
    # _QUOTA_GROUP_FOR_POSITION's docstring for the bug this replaces).
    total_roster_count = len(players)
    position_quotas = {
        grp: {"current": sum(1 for p in players if _QUOTA_GROUP_FOR_POSITION[p.position] == grp),
              "min": _ROSTER_POSITION_MINIMUMS.get(grp, 1)}
        for grp in QUOTA_GROUPS
    }

    # Depth chart groups (reusing depth_chart_view's logic)
    depth_chart_groups = _depth_chart_groups_for_team(team_abbr, players) if team_abbr != "FA" else []

    # Depth slot label per player ("QB1", "QB2", ...) -- RosterTable.tsx's
    # DEP column, real (each group's already-resolved starter order),
    # not fabricated. Empty for free agents (no depth chart concept).
    depth_slot: dict[str, str] = _slot_labels_from_groups(depth_chart_groups)

    # Real Filter panel (FilterPanel.tsx): position groups (QUOTA_GROUPS --
    # see that constant's own comment for why this reuses the quota
    # grouping instead of Figma's separate 10-group filter list), attribute
    # ranges, Rookie (age <= 23, Figma's own definition). Applied to the
    # TABLE ROWS only -- position_quotas/total_roster_count above stay
    # computed off the full roster, same as RosterTable.tsx's own
    # `totalRosterCount = players.length` (the unfiltered prop), not the
    # filtered `sortedPlayers`.
    filtered_players = players
    if position:
        wanted = set(position)
        filtered_players = [p for p in filtered_players if _QUOTA_GROUP_FOR_POSITION[p.position] in wanted]
    if min_ovr is not None:
        filtered_players = [p for p in filtered_players if p.overall_rating >= min_ovr]
    if max_ovr is not None:
        filtered_players = [p for p in filtered_players if p.overall_rating <= max_ovr]
    if min_spd is not None:
        filtered_players = [p for p in filtered_players if p.speed >= min_spd]
    if max_spd is not None:
        filtered_players = [p for p in filtered_players if p.speed <= max_spd]
    if min_cth is not None:
        filtered_players = [p for p in filtered_players if p.catching >= min_cth]
    if max_cth is not None:
        filtered_players = [p for p in filtered_players if p.catching <= max_cth]
    if min_tck is not None:
        filtered_players = [p for p in filtered_players if p.tackle >= min_tck]
    if max_tck is not None:
        filtered_players = [p for p in filtered_players if p.tackle <= max_tck]
    if rookie:
        filtered_players = [p for p in filtered_players if p.age <= 23]

    active_filters = []
    if position:
        active_filters.append("Position: " + ", ".join(position))
    if min_ovr is not None or max_ovr is not None:
        active_filters.append(f"OVR {min_ovr if min_ovr is not None else 0}-{max_ovr if max_ovr is not None else 99}")
    if min_spd is not None or max_spd is not None:
        active_filters.append(f"SPD {min_spd if min_spd is not None else 0}-{max_spd if max_spd is not None else 99}")
    if min_cth is not None or max_cth is not None:
        active_filters.append(f"CTH {min_cth if min_cth is not None else 0}-{max_cth if max_cth is not None else 99}")
    if min_tck is not None or max_tck is not None:
        active_filters.append(f"TCK {min_tck if min_tck is not None else 0}-{max_tck if max_tck is not None else 99}")
    if rookie:
        active_filters.append("Rookie (age <= 23)")
    generated_query = " AND ".join(active_filters) if active_filters else None

    # Sortable columns (GET-param + full-page-reload, Stats' M3 precedent).
    effective_sort = sort if sort in ROSTER_SORT_KEYS else None
    direction = dir if dir in ("asc", "desc") else "asc"
    if effective_sort:
        rows = sorted(filtered_players, key=lambda p: _roster_sort_value(p, effective_sort, depth_slot), reverse=(direction == "desc"))
    else:
        rows = filtered_players

    def roster_query(overrides: dict) -> str:
        base: dict = {
            "team_abbr": team_abbr, "view": view, "position": position,
            "min_ovr": min_ovr, "max_ovr": max_ovr, "min_spd": min_spd, "max_spd": max_spd,
            "min_cth": min_cth, "max_cth": max_cth, "min_tck": min_tck, "max_tck": max_tck,
            "rookie": "1" if rookie else None,
        }
        base.update(overrides)
        params = []
        for key, val in base.items():
            if key == "position":
                params.extend(("position", v) for v in val)
            elif val not in (None, "", False):
                params.append((key, val))
        return "/roster?" + urlencode(params)

    sort_links = {}
    for cid in ROSTER_SORT_KEYS:
        next_dir = "desc" if (effective_sort == cid and direction == "asc") else "asc"
        sort_links[cid] = roster_query({"sort": cid, "dir": next_dir})

    quota_pill_links = {}
    for grp in QUOTA_GROUPS:
        new_position = [] if position == [grp] else [grp]
        quota_pill_links[grp] = roster_query({"position": new_position})
    all_pill_link = roster_query({"position": []})
    clear_filters_link = roster_query({
        "position": [], "min_ovr": None, "max_ovr": None, "min_spd": None, "max_spd": None,
        "min_cth": None, "max_cth": None, "min_tck": None, "max_tck": None, "rookie": None,
    })

    # Compute stats data if needed
    stats_data = None
    if view == "stats":
        season = season_state.get_season()
        player_rows, _ = _stats_page_aggregates(season)
        # Filter to this team only
        stats_data = {(r["player_name"], r["player_pos"]): r for r in player_rows if r["player_team"] == team_abbr}

    # Top Free Agents (TopFreeAgentsBox.tsx). fa_status:
    #   ALL/OFF/DEF -- real free agents (no OVR floor or top-N cap anymore,
    #     per Brian's ask -- the box scrolls instead), stat line always
    #     blank (a free agent hasn't played a game this season, by
    #     definition -- there's nothing to show).
    #   SOON -- NOT free agents at all: rostered players league-wide whose
    #     contract_years_remaining <= 1, i.e. who a GM should worry about
    #     re-signing. This is the only reading of "soon to be a free agent"
    #     that isn't degenerate on a box that already only lists free
    #     agents (see ROADMAP.md R11's own note on this). These players
    #     ARE playing, so their real current-season stat line is shown.
    if fa_pos not in QUOTA_GROUPS and fa_pos != "All":
        fa_pos = "All"
    if fa_status not in ("ALL", "OFF", "DEF", "SOON"):
        fa_status = "ALL"
    with get_session() as s:
        if fa_status == "SOON":
            fa_rows = list(s.exec(select(Player).where(Player.team_abbr != None, Player.contract_years_remaining <= 1)))  # noqa: E711
        else:
            fa_rows = list(s.exec(select(Player).where(Player.team_abbr == None)))  # noqa: E711
    if fa_pos != "All":
        fa_rows = [p for p in fa_rows if _QUOTA_GROUP_FOR_POSITION[p.position] == fa_pos]
    if fa_status == "OFF":
        fa_rows = [p for p in fa_rows if _QUOTA_GROUP_FOR_POSITION[p.position] in FA_OFFENSE_GROUPS]
    elif fa_status == "DEF":
        fa_rows = [p for p in fa_rows if _QUOTA_GROUP_FOR_POSITION[p.position] in FA_DEFENSE_GROUPS]
    top_free_agents = sorted(fa_rows, key=lambda p: -p.overall_rating)
    fa_stat_line: dict[str, str] = {}
    if fa_status == "SOON" and top_free_agents:
        season = season_state.get_season()
        player_rows, _ = _stats_page_aggregates(season)
        stats_by_key = {(r["player_name"], r["player_pos"]): r for r in player_rows}
        for p in top_free_agents:
            row = stats_by_key.get((p.full_name, p.position.value))
            if row:
                fa_stat_line[p.player_id] = _fa_stat_line_summary(row)
    fa_pos_options = ["All"] + QUOTA_GROUPS

    # Find Player (FindPlayerBox.tsx): real league-wide name/position/team
    # search -- unlike Figma's own mock version, results reuse this
    # project's existing Player Card modal (player_link()) instead of a
    # second, separate detail dialog. Attribute-range/Rookie filters mirror
    # the Roster page's own Filter panel exactly (same fields, same
    # semantics) via distinct find_* param names so the two forms living on
    # the same /roster URL never clobber each other's query params.
    find_results = []
    find_active = bool(
        find_q or find_pos != "all" or find_team != "all" or find_rookie
        or find_min_ovr is not None or find_max_ovr is not None
        or find_min_spd is not None or find_max_spd is not None
        or find_min_cth is not None or find_max_cth is not None
        or find_min_tck is not None or find_max_tck is not None
    )
    if find_active:
        with get_session() as s:
            find_results = list(s.exec(select(Player)))
        if find_q:
            ql = find_q.lower()
            find_results = [p for p in find_results if ql in p.full_name.lower()]
        if find_pos != "all":
            find_results = [p for p in find_results if p.position.value == find_pos]
        if find_team != "all":
            find_results = [p for p in find_results if p.team_abbr == find_team]
        if find_min_ovr is not None:
            find_results = [p for p in find_results if p.overall_rating >= find_min_ovr]
        if find_max_ovr is not None:
            find_results = [p for p in find_results if p.overall_rating <= find_max_ovr]
        if find_min_spd is not None:
            find_results = [p for p in find_results if p.speed >= find_min_spd]
        if find_max_spd is not None:
            find_results = [p for p in find_results if p.speed <= find_max_spd]
        if find_min_cth is not None:
            find_results = [p for p in find_results if p.catching >= find_min_cth]
        if find_max_cth is not None:
            find_results = [p for p in find_results if p.catching <= find_max_cth]
        if find_min_tck is not None:
            find_results = [p for p in find_results if p.tackle >= find_min_tck]
        if find_max_tck is not None:
            find_results = [p for p in find_results if p.tackle <= find_max_tck]
        if find_rookie:
            find_results = [p for p in find_results if p.age <= 23]

        # R11 (GDD Sec 11, "Roster - Find Player & Free Agents"): sortable
        # by any ROSTER_SORT_KEYS column, same GET-param + full-page-reload
        # convention as the main Roster table's own sort links -- not a
        # second, client-side mechanism. "dep" needs each result's OWN
        # team's depth chart (not the currently-browsed team's), computed
        # lazily via _depth_slot_across_teams only when actually asked for.
        effective_find_sort = find_sort if find_sort in ROSTER_SORT_KEYS else "ovr"
        find_direction = find_dir if find_dir in ("asc", "desc") else "desc"
        find_depth_slot: dict[str, str] = {}
        if effective_find_sort == "dep":
            find_depth_slot = _depth_slot_across_teams({p.team_abbr for p in find_results if p.team_abbr})
        find_results.sort(
            key=lambda p: _roster_sort_value(p, effective_find_sort, find_depth_slot),
            reverse=(find_direction == "desc"),
        )
        find_results = find_results[:25]
    else:
        effective_find_sort = find_sort if find_sort in ROSTER_SORT_KEYS else "ovr"
        find_direction = find_dir if find_dir in ("asc", "desc") else "desc"

    team = FREE_AGENTS_TEAM if team_abbr == "FA" else TEAMS_BY_ABBR[team_abbr]
    return templates.TemplateResponse(
        request,
        "roster.html",
        {
            "teams": TEAMS, "team": team, "players": rows, "starters": starters,
            "view": view, "position_quotas": position_quotas, "depth_chart_groups": depth_chart_groups,
            "stats_data": stats_data, "depth_slot": depth_slot,
            "total_roster_count": total_roster_count, "max_roster_size": MAX_ROSTER_SIZE,
            "quota_pill_links": quota_pill_links, "all_pill_link": all_pill_link,
            "position_filter": position, "sort_links": sort_links, "sort": effective_sort, "dir": direction,
            "filter_groups": QUOTA_GROUPS,
            "min_ovr": min_ovr, "max_ovr": max_ovr, "min_spd": min_spd, "max_spd": max_spd,
            "min_cth": min_cth, "max_cth": max_cth, "min_tck": min_tck, "max_tck": max_tck,
            "rookie": rookie, "generated_query": generated_query, "clear_filters_link": clear_filters_link,
            "avg_throw_accuracy": _roster_avg_throw_accuracy, "injury_risk": _roster_injury_risk,
            "top_free_agents": top_free_agents, "fa_pos": fa_pos, "fa_status": fa_status,
            "fa_pos_options": fa_pos_options, "fa_stat_line": fa_stat_line,
            "find_q": find_q, "find_pos": find_pos, "find_team": find_team, "find_results": find_results,
            "find_active": find_active,
            "find_min_ovr": find_min_ovr, "find_max_ovr": find_max_ovr,
            "find_min_spd": find_min_spd, "find_max_spd": find_max_spd,
            "find_min_cth": find_min_cth, "find_max_cth": find_max_cth,
            "find_min_tck": find_min_tck, "find_max_tck": find_max_tck, "find_rookie": find_rookie,
            "find_sort": effective_find_sort, "find_dir": find_direction,
            "find_sort_columns": ROSTER_SORT_COLUMN_LABELS,
            "all_positions": list(Position),
        },
    )


def _roster_by_position(team_abbr: str) -> dict[Position, list[Player]]:
    with get_session() as s:
        players = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
    by_position: dict[Position, list[Player]] = {}
    for p in players:
        by_position.setdefault(p.position, []).append(p)
    return by_position


@app.get("/depth-chart")
def depth_chart_view(team_abbr: str | None = None):
    """Sec13: the standalone Depth Chart page is retired -- its full
    functionality (per-position tables, move buttons, auto-fill) now
    lives in the Roster page's own embedded widget (see
    `_depth_chart_widget.html`, included from roster.html) rather than a
    separate screen. This route stays only so an old bookmark/link to
    /depth-chart redirects instead of 404ing."""
    if team_abbr is None:
        team_abbr = season_state.get_season().user_team_abbr
    url = f"/roster?team_abbr={team_abbr}" if team_abbr else "/roster"
    return RedirectResponse(url=url, status_code=303)


@app.post("/depth-chart/{team_abbr}/{position_value}/move")
def depth_chart_move(team_abbr: str, position_value: str, player_id: str = Form(...), direction: str = Form(...)):
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")
    try:
        position = Position(position_value)
    except ValueError:
        raise HTTPException(404, "No such position")

    players = _roster_by_position(team_abbr).get(position, [])
    current_order = [p.player_id for p in depth_chart_overrides.resolve_order(team_abbr, position_value, players)]
    depth_chart_overrides.move_player(team_abbr, position_value, current_order, player_id, direction)
    clear_starters_cache()  # the override just changed -- don't serve a stale cached starter

    return RedirectResponse(url=f"/roster?team_abbr={team_abbr}", status_code=303)


@app.post("/depth-chart/{team_abbr}/auto-fill")
def depth_chart_auto_fill(team_abbr: str, respect_fatigue: bool = Form(False), lock_starters: bool = Form(False)):
    """M15 correction (real source: AutoFillModal.tsx) -- see
    depth_chart_overrides.auto_fill()'s own docstring for exactly which
    2 of the source's 4 toggles are offered and why the other 2 aren't
    (both need data this engine's Player model doesn't have). `respect_fatigue`
    is still the real form field name/behavior -- Sec11 only renamed its
    user-facing label to "Consider Stamina", not this param."""
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")

    by_position = _roster_by_position(team_abbr)
    depth_chart_overrides.auto_fill(team_abbr, by_position, STARTER_COUNTS, respect_fatigue=respect_fatigue, lock_starters=lock_starters)
    clear_starters_cache()

    return RedirectResponse(url=f"/roster?team_abbr={team_abbr}", status_code=303)


def _defensive_stat_leaders(season, top_n: int = 15):
    """Sorted by solo tackles (the closest single-number analog to
    "yards" for a defensive leaderboard) -- see
    app/engine/defensive_box_score.py for what's real here, including
    Defensive TD (GDD Sec 6.7.2, ROADMAP.md M1)."""
    defense = aggregate_season_defensive_stats(season)
    return sorted(defense.values(), key=lambda l: -l.solo_tackles)[:top_n]


def _team_schedule_for(season, team_abbr: str) -> list[dict]:
    """One row per week this team plays (byes just don't appear), each
    with the opponent and W/L/score once that week's game has been
    simulated -- the real per-team view the Figma source's TeamSchedule
    component shows, as opposed to the league-wide "latest results"
    the pre-M9 dashboard had. Built from season.schedule, the same data
    every other schedule view (e.g. /season) already reads."""
    rows = []
    for week_num, week in enumerate(season.schedule, start=1):
        game = next((g for g in week if team_abbr in (g.home_abbr, g.away_abbr)), None)
        if game is None:
            continue
        is_home = game.home_abbr == team_abbr
        opponent_abbr = game.away_abbr if is_home else game.home_abbr
        result = None
        if game.result is not None:
            user_score = game.result.home_score if is_home else game.result.away_score
            opp_score = game.result.away_score if is_home else game.result.home_score
            # Compared by literal score, not game.result.winner: that field
            # always resolves an equal score to "home" (game_sim.py's
            # `"home" if h >= a else "away"`, a tie-break convention for
            # standings, not a real tie state), so trusting it here would
            # mis-color a genuinely tied score green/red instead of grey.
            won = user_score > opp_score
            tied = user_score == opp_score
            result = {"won": won, "tied": tied, "user_score": user_score, "opp_score": opp_score}
        rows.append({"week": week_num, "opponent_abbr": opponent_abbr, "is_home": is_home, "result": result})
    return rows


def _game_leaders(box) -> dict[str, object | None]:
    """One full stat line (the PassingLine/RushingLine/ReceivingLine
    itself, not just a name+yards tuple) per real offensive category for
    a SINGLE game's box score -- ROADMAP.md Sec2c item 3's condensed
    "Game Leaders" mini-leaderboard, not a season aggregate (that's Top
    Performers' job). None (not a fabricated 0) when a team recorded
    nothing in a category, e.g. a team with zero completed passes.
    Returning the whole line (not just yards) lets the dashboard render
    a real box-score stat line, e.g. "23-33, 178 Yds, 1 TD, 3 Ints"."""
    return {
        "passing": max(box.passing, key=lambda p: p.yards, default=None),
        "rushing": max(box.rushing, key=lambda r: r.yards, default=None),
        "receiving": max(box.receiving, key=lambda r: r.yards, default=None),
    }


def _format_leader_stat_line(cat: str, line) -> str:
    """Condensed single-line stat summary for the Game Leaders widget,
    matching real box-score shorthand (e.g. "23-33, 178 Yds, 1 TD, 3
    Ints") -- TD/INT are only appended when nonzero so a leader with
    neither doesn't show a stray "0 TD"."""
    if cat == "passing":
        parts = [f"{line.completions}-{line.attempts}", f"{line.yards} Yds"]
        if line.touchdowns:
            parts.append(f"{line.touchdowns} TD")
        if line.interceptions:
            parts.append(f"{line.interceptions} Ints")
    elif cat == "rushing":
        parts = [f"{line.carries} Car", f"{line.yards} Yds"]
        if line.touchdowns:
            parts.append(f"{line.touchdowns} TD")
    else:  # receiving
        parts = [f"{line.receptions} Rec", f"{line.yards} Yds"]
        if line.touchdowns:
            parts.append(f"{line.touchdowns} TD")
    return ", ".join(parts)


def _last_played_game_for(season, team_abbr: str) -> dict | None:
    """The most recently completed game involving this team specifically
    (not just the most recent league-wide week, which may have been a
    bye for this team) -- feeds the Dashboard's Box Score widget
    (ROADMAP.md M9, redesigned Sec2c item 3), reusing the exact same
    build_box_score/build_defensive_box_score calls result.html already
    makes for any other game. Also builds the OPPONENT's box score (M9
    only ever needed the user's own team's) so the redesigned box's
    scoreboard summary and Game Leaders mini-leaderboard can show both
    teams, not just the user's."""
    for week_num in range(season.current_week - 1, 0, -1):
        game = next(
            (g for g in season.schedule[week_num - 1]
             if team_abbr in (g.home_abbr, g.away_abbr) and g.result is not None),
            None,
        )
        if game is None:
            continue
        is_home = game.home_abbr == team_abbr
        opponent_abbr = game.away_abbr if is_home else game.home_abbr
        user_score = game.result.home_score if is_home else game.result.away_score
        opp_score = game.result.away_score if is_home else game.result.home_score
        box = build_box_score(game.result.plays, team_abbr)
        opponent_box = build_box_score(game.result.plays, opponent_abbr)
        return {
            "week": week_num,
            "opponent_abbr": opponent_abbr,
            "is_home": is_home,
            "home_abbr": game.home_abbr,
            "away_abbr": game.away_abbr,
            "home_score": user_score if is_home else opp_score,
            "away_score": opp_score if is_home else user_score,
            "won": (game.result.winner == "home") == is_home,
            "user_score": user_score,
            "opp_score": opp_score,
            "box": box,
            "defense": build_defensive_box_score(game.result.plays, team_abbr),
            "user_leaders": _game_leaders(box),
            "opponent_leaders": _game_leaders(opponent_box),
            "plays": game.result.plays,
            "quarters": quarter_scores(game.result.events),
        }
    return None


def _notable_players_for(team_abbr: str, min_ovr: int = 85) -> list[dict]:
    """Scouting Panel Overview tab: any real roster player above min_ovr,
    not a fixed QB/RB/WR1-style slot table -- Brian's own instruction
    (ROADMAP.md Sec2d item 3), and more robust than a forced slot layout
    (a team with no elite LB just shows fewer rows instead of a blank
    one). Real query against the roster DB, same field roster.html's own
    OVR badge already uses (Player.overall_rating)."""
    with get_session() as s:
        players = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
    notable = sorted((p for p in players if p.overall_rating >= min_ovr), key=lambda p: -p.overall_rating)
    return [{"name": p.full_name, "position": p.position.value, "ovr": p.overall_rating} for p in notable]


def _money(amount: int) -> str:
    return "${:,}".format(amount)


def _coach_card_json(coach: Coach) -> str:
    """The Coach Card modal's data blob (GDD Sec 7.5 "Player & Coach
    Cards", Sec 7.9.4's Career Summary / Season History), rendered into
    a data-coach-card attribute exactly the way _player_card_json and
    the Team Card's blob already are.

    Every number here is real in one of two senses, and the card says
    which: the name/title/team/salary come straight from the real 2026
    staff seed, while the ratings and tendencies are deterministically
    generated (Coach.is_generated_profile) and carry an on-card
    disclosure saying so -- see app/models/coach.py's module docstring."""
    role = CoachRole(coach.role)
    history_rows = []
    for row in coach_records.season_history(coach.coach_id):
        bits = [f"{row.wins}-{row.losses}"]
        if row.conference_title != "NONE":
            bits.append(f"{row.conference_title} champion")
        if row.super_bowl_result == "WIN":
            bits.append("Super Bowl win")
        elif row.super_bowl_result == "LOSS":
            bits.append("Super Bowl loss")
        elif row.made_playoffs:
            bits.append("made playoffs")
        history_rows.append({
            "season": row.season, "team": row.team_abbr or "--",
            "role": row.role.value, "summary": ", ".join(bits),
        })

    titles_by_role = []
    for r, label in (("hc", "HC"), ("oc", "OC"), ("dc", "DC"), ("st", "ST"), ("ac", "AC")):
        afc = getattr(coach, f"{r}_afc_championships")
        nfc = getattr(coach, f"{r}_nfc_championships")
        sb = getattr(coach, f"{r}_super_bowl_wins")
        if afc or nfc or sb:
            titles_by_role.append([label, f"{afc} AFC, {nfc} NFC, {sb} SB"])

    generated_note = (
        "Ratings and tendencies are deterministically generated from this league's "
        "seed, not real data -- the real 2026 staff seed supplies only name, title "
        "and salary. Reputation is the one generated value with a real anchor: this "
        "coach's salary percentile within their own role tier."
    ) if coach.is_generated_profile else ""

    return json.dumps({
        "coach_id": coach.coach_id,
        "name": coach.full_name,
        "initials": (coach.first_name[:1] + coach.last_name[:1]).upper(),
        "title": coach.title,
        "role": role.value,
        "specialty": coach.specialty,
        "team_abbr": coach.team_abbr,
        "age": coach.age,
        "experience_years": coach.experience_years,
        "reputation": coach.reputation,
        "overall": coach.overall,
        "offensive_profile": coach.offensive_profile,
        "defensive_profile": coach.defensive_profile,
        "job_security": f"{coach.job_security_score:.0f}",
        "salary": _money(coach.salary_aav),
        "contract_years": coach.contract_years,
        "career_record": f"{coach.career_wins}-{coach.career_losses}",
        "seasons_coached": coach.seasons_coached,
        "playoff_wins": coach.playoff_wins,
        "conference_titles": coach.conference_titles,
        "super_bowl_wins": coach.super_bowl_wins,
        "coach_awards": coach.coach_awards,
        "titles_by_role": titles_by_role,
        "season_history": history_rows,
        "rating_groups": [
            {"heading": "Performance & Management (Sec 7.7.2.3)", "rows": [
                ["Player Dev (Off)", coach.player_dev_offense],
                ["Player Dev (Def)", coach.player_dev_defense],
                ["Discipline", coach.discipline],
                ["Motivation / Chemistry", coach.motivation_chemistry],
                ["Red Zone Offense", coach.red_zone_offense],
                ["Red Zone Defense", coach.red_zone_defense],
            ]},
            {"heading": "Strategic Tendencies (Sec 7.7.2.2)", "rows": [
                ["Pass Tendency", coach.run_pass_tendency],
                ["Offensive Aggression", coach.offensive_aggression],
                ["Pace", coach.pace],
                ["Red Zone Pass Lean", coach.red_zone_offense_bias],
                ["Two-Point Tendency", coach.two_point_tendency],
                ["Blitz Rate", coach.blitz_rate],
                ["Coverage Mix (zone-heavy)", coach.coverage_mix],
                ["Short-Yardage D Aggression", coach.fourth_down_defense],
                ["Red Zone D Lean", coach.red_zone_defense_bias],
                ["Special Teams Focus", coach.special_teams_focus],
            ]},
        ],
        "contract_note": (
            "Salary is real (2026 staff seed). Contract length is a disclosed "
            "placeholder until R4a builds real negotiated terms -- the same state "
            "player contracts are in."
        ),
        "generated_note": generated_note,
    })


def _head_coach_summary(team_abbr: str) -> dict | None:
    """The Scouting Panel's Head Coach row (ROADMAP.md Sec2d item 3),
    now backed by the real Coach entity rather than the
    "Coach Name"/None placeholder this function replaced. Returns None
    when the database has no coaches at all, which is what the template
    branches on to fall back to its pre-coach text."""
    coach = coach_store.head_coach(team_abbr)
    if coach is None:
        return None
    return {
        "name": coach.full_name,
        "record": f"{coach.career_wins}-{coach.career_losses}" if coach.seasons_coached else None,
        "overall": coach.overall,
        "card": _coach_card_json(coach),
    }


def _placeholder_coach() -> dict:
    """Pre-Coach-entity fallback, kept for the one case it still covers:
    a database that predates scripts/import_coaches.py and therefore has
    no Coach rows at all. Every caller checks coach_store.has_coaches()
    (or _head_coach_summary()'s None return) first and prefers the real
    coach; this is the honest "we have nothing" answer, not a default.

    ROADMAP.md Sec2d item 3's original note: Brian's
    explicit decision was a disclosed placeholder now rather than either
    fabricating a real-looking name/record or silently omitting the
    section: the front end renders the literal name "Coach Name" (not a
    real coach), and this is the ONE place that string comes from, so
    R3 only has to replace this function's body with a real query later,
    not hunt for a hardcoded template string."""
    return {"name": "Coach Name", "record": None}


def _all_division_standings(season, user_conference: str | None = None, user_division: str | None = None) -> dict[str, dict[str, list]]:
    """Every conference's every division, sorted the same way the
    Dashboard's original (user-division-only) Standings box already
    sorted (win_pct desc, point_diff desc, location as a stable
    tiebreak) -- ROADMAP.md Sec2d-B item 9's AFC/NFC-tab-only redesign
    needs all 8 real groups, not just the user's own, stacked together
    under one conference tab. Reuses _grouped_teams() (already real,
    already used by /playoffs) instead of re-deriving conference/
    division membership.

    user_conference/user_division (when given) put the user's own
    division first in its conference's dict -- since dict iteration
    order is what the Standings box now renders top-to-bottom (no more
    East/North/South/West sub-tabs), this is what keeps the user's own
    division pinned to the top instead of wherever it falls
    alphabetically."""
    grouped: dict[str, dict[str, list]] = {}
    for conf, divisions in _grouped_teams().items():
        division_standings = {
            division: sorted(
                (season.records[t.abbr] for t in teams),
                key=lambda r: (-r.win_pct, -r.point_diff, r.location),
            )
            for division, teams in divisions.items()
        }
        if conf == user_conference and user_division in division_standings:
            division_standings = {
                user_division: division_standings.pop(user_division),
                **division_standings,
            }
        grouped[conf] = division_standings
    return grouped


def _power_rankings_with_deltas(season) -> list[dict]:
    """Ranked by power_rating descending -- the same order
    simulate_current_week() itself uses when it writes each week's
    snapshot (app/services/power_rank_history.py) -- with a real
    week-over-week rank delta read from that snapshot store
    (ROADMAP.md Sec2d-B item 10) instead of Figma's own fabricated demo
    deltas. delta is None (not a fabricated 0/dash) whenever there's no
    prior-week snapshot yet: the season's first tracked week, or an old
    save that predates this store."""
    ordered = sorted(season.records.values(), key=lambda r: -r.power_rating)
    week_just_played = season.current_week - 1
    prior_ranks = (
        power_rank_history.get_ranks(season.season_number, week_just_played - 1)
        if week_just_played > 0 else None
    )
    rows = []
    for idx, r in enumerate(ordered, start=1):
        delta = prior_ranks[r.abbr] - idx if prior_ranks and r.abbr in prior_ranks else None
        rows.append({"rank": idx, "record": r, "delta": delta})
    return rows


# A2 (docs/handoff_prestige_and_coach_impact.md): the FBGM-style
# position-rank sheet's sortable columns -- same GET-param + full-page-
# reload convention as ROSTER_SORT_KEYS, not a second mechanism.
POSITION_RANK_SORT_KEYS = ("team", "conf", "div", "rating", "age") + tuple(QUOTA_GROUPS) + ("coach",)


def _rank_by(values: dict[str, float]) -> dict[str, int]:
    """1 = highest value. Same shape as coach_progression.py's own
    _rank_map, kept local since that one ranks real statistical
    categories that FEED coach progression, not a display rank."""
    ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=True)
    return {abbr: i for i, (abbr, _) in enumerate(ordered, start=1)}


def _position_rank_sheet() -> list[dict]:
    """A1's app/engine/roster_strength.py has three intended consumers;
    this is the first of them. Computed live on every page load rather
    than from a stored week-0 snapshot -- see roster_strength.py's own
    module docstring: nothing in this engine mutates a Player's
    overall_rating or a Coach's overall mid-season, so a live read and a
    frozen week-0 snapshot are numerically IDENTICAL for the entire
    season today. Revisit once progression/injury/trades can change
    either value mid-season -- at that point this needs the real
    week-0-snapshot story A1 deliberately deferred."""
    strengths = roster_strength.compute_all([t.abbr for t in TEAMS])

    with get_session() as s:
        all_players = list(s.exec(select(Player)))
    ages_by_team: dict[str, list[int]] = defaultdict(list)
    for p in all_players:
        if p.team_abbr:
            ages_by_team[p.team_abbr].append(p.age)
    avg_age = {abbr: sum(ages) / len(ages) for abbr, ages in ages_by_team.items()}

    group_ranks = {
        group: _rank_by({abbr: r.group_ratings.get(group, 0.0) for abbr, r in strengths.items()})
        for group in QUOTA_GROUPS
    }
    # A vacant head coach (never happens at league seed -- see
    # coach_store.py's own docstring -- but this degrades rather than
    # crashing if it ever does) ranks last, not fabricated into the
    # middle of the pack.
    coach_rank = _rank_by({
        abbr: (r.coach_overall if r.coach_overall is not None else -1.0)
        for abbr, r in strengths.items()
    })

    rows = []
    for team in TEAMS:
        r = strengths[team.abbr]
        rows.append({
            "team": team,
            "rating": r.team_rating,
            "age": avg_age.get(team.abbr, 0.0),
            "coach_overall": r.coach_overall,
            "coach_rank": coach_rank[team.abbr],
            "group_ranks": {g: group_ranks[g][team.abbr] for g in QUOTA_GROUPS},
        })
    return rows


def _position_rank_sort_value(row: dict, key: str):
    if key == "team":
        return row["team"].location.lower()
    if key == "conf":
        return row["team"].conference
    if key == "div":
        return row["team"].division
    if key == "rating":
        return row["rating"]
    if key == "age":
        return row["age"]
    if key == "coach":
        return row["coach_rank"]
    return row["group_ranks"].get(key, 999)


# ROADMAP.md Sec2d-B item 11: Dashboard Top Performers category dropdown.
# Every id is a real field _stats_page_aggregates() already computes (same
# per-player season rows backing the Stats page's Player tab) -- labels
# match LeagueTopPerformers.tsx's own category wording rather than
# PLAYER_STAT_LABELS' slightly different phrasing (e.g. "Tackles" not
# "Solo Tackles"), since this dropdown is specifically replicating that
# source. "Tackles" -> solo_tackles is the same closest-real-analog choice
# _defensive_stat_leaders() already makes for a defensive leaderboard.
TOP_PERFORMERS_CATEGORIES: list[tuple[str, str]] = [
    ("qb_rating", "QB Rating"),
    ("pass_yds", "Passing Yards"),
    ("pass_td", "Passing TDs"),
    ("rush_yds", "Rushing Yards"),
    ("rush_td", "Rushing TDs"),
    ("rec_yds", "Receiving Yards"),
    ("rec_td", "Receiving TDs"),
    ("sacks", "Sacks"),
    ("solo_tackles", "Tackles"),
    ("def_int", "Interceptions"),
]


def _top_performer_leaders(player_rows: list[dict], stat_id: str, top_n: int = 10) -> list[dict]:
    """Ranks the real per-player season rows _stats_page_aggregates()
    already computes by one stat id, descending -- a straight reuse, not
    new computation, per ROADMAP.md Sec2d-B item 11's own instruction to
    check for an existing source before assuming anything's missing.
    A None stat value (an empty sample -- e.g. a non-kicker has no
    qb_rating) sorts last rather than crashing or being coerced to a
    fabricated 0. Each row gains its real conference (for the
    AFC/NFC/All client-side filter) looked up from the same TEAMS_BY_ABBR
    every other conference/division grouping on this page already uses."""
    ranked = sorted(player_rows, key=lambda r: (r[stat_id] is None, -(r[stat_id] or 0)))[:top_n]
    return [
        {**row, "conference": TEAMS_BY_ABBR[row["player_team"]].conference}
        for row in ranked
        if row["player_team"] in TEAMS_BY_ABBR
    ]


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request, pr_sort: str | None = None, pr_dir: str = "asc"):
    """League-at-a-glance landing page, pulling from pieces that already
    exist rather than introducing new state. Doesn't replace `/`, which
    stays the single-game simulator -- the GDD lists Dashboard and
    "Simulate a Game" as distinct screens.

    GDD Sec 10.1: Dashboard is the default landing page and always
    resolves to the user's team -- if no team has been chosen yet for
    this franchise, redirect to the one-time team-selection screen
    rather than rendering a teamless dashboard.

    ROADMAP.md M9: the real Figma layout (docs/figma-export/src/app/
    DASHBOARD_DOCUMENTATION.md) is a 3-column grid of 8 widgets --
    Division Standings, Team Schedule, Scouting Panel, League Power
    Rankings, League Top Performers, Box Score, Team Top Performers,
    Play-by-Play. All 8 are real data already produced elsewhere in
    the engine (standings/schedule/scouting/box-score machinery); this
    route just queries/filters it per-widget instead of the single
    league-wide top-10 + latest-week-results shape the pre-M9 version
    used, and dashboard.html arranges the result into that grid."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        return RedirectResponse(url="/team-select", status_code=303)

    user_abbr = season.user_team_abbr
    user_info = TEAMS_BY_ABBR[user_abbr]
    gameplan = gameplan_store.get_gameplan(user_abbr)

    next_opponent = find_next_opponent(season, user_abbr)
    scouting = None
    if next_opponent is not None:
        opponent_abbr, team_is_home = next_opponent
        scouting = build_scouting_report(season, opponent_abbr)
        scouting["opponent_team"] = TEAMS_BY_ABBR[opponent_abbr]
        scouting["is_home_game"] = team_is_home
        scouting["notable_players"] = _notable_players_for(opponent_abbr)
        # ROADMAP.md R3: the real Coach entity, replacing Sec2d item 3's
        # disclosed "Coach Name" placeholder. Falls back to that
        # placeholder only if this database has no coaches at all.
        scouting["coach"] = _head_coach_summary(opponent_abbr) or _placeholder_coach()

    all_standings = _all_division_standings(season, user_info.conference, user_info.division)
    power_rankings = _power_rankings_with_deltas(season)
    team_schedule = _team_schedule_for(season, user_abbr)
    last_game = _last_played_game_for(season, user_abbr)

    # A2 (docs/handoff_prestige_and_coach_impact.md): the position-rank
    # sheet, sortable via the same GET-param + full-page-reload pattern
    # as the Roster page (ROSTER_SORT_KEYS/_roster_sort_value()).
    effective_pr_sort = pr_sort if pr_sort in POSITION_RANK_SORT_KEYS else None
    pr_direction = pr_dir if pr_dir in ("asc", "desc") else "asc"
    position_rank_rows = _position_rank_sheet()
    if effective_pr_sort:
        position_rank_rows = sorted(
            position_rank_rows,
            key=lambda row: _position_rank_sort_value(row, effective_pr_sort),
            reverse=(pr_direction == "desc"),
        )
    else:
        position_rank_rows = sorted(position_rank_rows, key=lambda row: -row["rating"])

    def pr_query(overrides: dict) -> str:
        base = {"pr_sort": pr_sort, "pr_dir": pr_dir}
        base.update(overrides)
        return "/dashboard?" + urlencode([(k, v) for k, v in base.items() if v not in (None, "")])

    position_rank_sort_links = {}
    for cid in POSITION_RANK_SORT_KEYS:
        next_dir = "desc" if (effective_pr_sort == cid and pr_direction == "asc") else "asc"
        position_rank_sort_links[cid] = pr_query({"pr_sort": cid, "pr_dir": next_dir})

    player_rows, _team_rows = _stats_page_aggregates(season)
    top_performers_by_stat = {
        stat_id: _top_performer_leaders(player_rows, stat_id)
        for stat_id, _label in TOP_PERFORMERS_CATEGORIES
    }

    # ROADMAP.md Sec2c item 2: new Row 3 Awards Race box, real data via
    # awards.py's season_awards() -- gated on Week 4 completion (see
    # STANDINGS_BASED_FEATURES_MIN_WEEK's own docstring), same gate the
    # Stats page's own Awards Race section now uses too.
    awards_race = awards.season_awards(season) if season.current_week >= STANDINGS_BASED_FEATURES_MIN_WEEK else None

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "season": season,
            "user_info": user_info,
            "gameplan": gameplan,
            "scouting": scouting,
            "offensive_aggressiveness_options": OFFENSIVE_AGGRESSIVENESS,
            "defensive_aggressiveness_options": DEFENSIVE_AGGRESSIVENESS,
            "coverage_options": COVERAGE_SCHEMES,
            "blitz_options": BLITZ_STRATEGIES,
            "rz_offense_options": RZ_OFFENSE_STYLES,
            "rz_defense_options": RZ_DEFENSE_STYLES,
            "all_standings": all_standings,
            "power_rankings": power_rankings,
            "team_schedule": team_schedule,
            "last_game": last_game,
            "top_performers_categories": TOP_PERFORMERS_CATEGORIES,
            "top_performers_by_stat": top_performers_by_stat,
            "awards_race": awards_race,
            "position_rank_rows": position_rank_rows,
            "position_rank_groups": QUOTA_GROUPS,
            "position_rank_sort_links": position_rank_sort_links,
            "pr_sort": effective_pr_sort,
            "pr_dir": pr_direction,
        },
    )


@app.post("/gameplan")
def gameplan_submit(
    offensive_aggressiveness: str = Form(...),
    defensive_aggressiveness: str = Form(...),
    coverage: str = Form(...),
    blitz: str = Form(...),
    rz_offense: str = Form(...),
    rz_defense: str = Form(...),
):
    """GDD Sec 10.4.1's Weekly Gameplan: always sets the CURRENT user's
    team (there's no team_abbr in the form -- the panel only ever
    appears on the user's own Dashboard/Staff screens, matching Sec
    10.1's "gameplan settings" being exclusive to the user's team).
    404s if no team has been chosen yet rather than silently no-op'ing."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        raise HTTPException(404, "No team chosen yet")

    for value, options, field in [
        (offensive_aggressiveness, OFFENSIVE_AGGRESSIVENESS, "offensive_aggressiveness"),
        (defensive_aggressiveness, DEFENSIVE_AGGRESSIVENESS, "defensive_aggressiveness"),
        (coverage, COVERAGE_SCHEMES, "coverage"),
        (blitz, BLITZ_STRATEGIES, "blitz"),
        (rz_offense, RZ_OFFENSE_STYLES, "rz_offense"),
        (rz_defense, RZ_DEFENSE_STYLES, "rz_defense"),
    ]:
        if value not in options:
            raise HTTPException(422, f"Invalid {field}: {value!r}")

    gameplan_store.set_gameplan(season.user_team_abbr, Gameplan(
        offensive_aggressiveness=offensive_aggressiveness,
        defensive_aggressiveness=defensive_aggressiveness,
        coverage=coverage,
        blitz=blitz,
        rz_offense=rz_offense,
        rz_defense=rz_defense,
    ))
    return RedirectResponse(url="/dashboard", status_code=303)


# Stats page redesign (GDD Sec 10.4, ROADMAP.md M3). Real source:
# docs/figma-export/src/app/components/StatsPage.tsx +
# stats/StatColumnChooser.tsx -- Team/Player/Coach tabs, sortable
# columns, a customizable-column chooser. Translated from the Figma
# source's React client-state implementation into this project's
# existing GET-query-param + full-page-reload pattern (see /playoffs's
# ?view=, and the "no htmx/framework" architecture note in HANDOFF.md)
# rather than introducing a new client-side JS subsystem. The catalog
# below is a deliberately TRIMMED version of the Figma source's ~150-stat
# hierarchy (docs/figma-export/src/app/lib/statHierarchy.ts) -- only
# stats this engine actually attributes to a real player/team
# (season_stats.py, defensive_box_score.py, TeamRecord) are offered;
# advanced metrics with no real underlying data here (air yards,
# pressures, contested catches, snap counts, coach records, ...) are
# omitted rather than fabricated, same discipline as the Player Card's
# Stats tab (and its Contract tab, M8 -- real salary/signing bonus, no
# fabricated cap/years-remaining data).
PLAYER_STAT_CATEGORIES: list[dict] = [
    {"label": "Identity & Participation", "stats": [
        {"id": "player_name", "label": "Player Name"},
        {"id": "player_pos", "label": "Position"},
        {"id": "player_team", "label": "Team"},
        {"id": "player_num", "label": "Jersey #"},
        {"id": "player_age", "label": "Age"},
        {"id": "player_exp", "label": "Years Pro"},
        {"id": "games_played", "label": "Games Played"},
    ]},
    {"label": "Passing", "stats": [
        {"id": "pass_att", "label": "Pass Attempts"},
        {"id": "pass_cmp", "label": "Completions"},
        {"id": "pass_cmp_pct", "label": "Completion %"},
        {"id": "pass_yds", "label": "Passing Yards"},
        {"id": "pass_yds_per_att", "label": "Yards per Attempt"},
        {"id": "pass_td", "label": "Passing TDs"},
        {"id": "pass_int", "label": "Interceptions Thrown"},
        {"id": "sacks_taken", "label": "Sacks Taken"},
        {"id": "qb_rating", "label": "Passer Rating"},
    ]},
    {"label": "Rushing", "stats": [
        {"id": "rush_att", "label": "Rush Attempts"},
        {"id": "rush_yds", "label": "Rushing Yards"},
        {"id": "yds_per_rush", "label": "Yards per Rush"},
        {"id": "rush_td", "label": "Rushing TDs"},
        {"id": "fumbles_lost", "label": "Fumbles Lost"},
    ]},
    {"label": "Receiving", "stats": [
        {"id": "targets", "label": "Targets"},
        {"id": "receptions", "label": "Receptions"},
        {"id": "catch_pct", "label": "Catch %"},
        {"id": "rec_yds", "label": "Receiving Yards"},
        {"id": "rec_td", "label": "Receiving TDs"},
    ]},
    {"label": "Defense", "stats": [
        {"id": "solo_tackles", "label": "Solo Tackles"},
        {"id": "tackles_for_loss", "label": "Tackles for Loss"},
        {"id": "sacks", "label": "Sacks"},
        {"id": "def_int", "label": "Interceptions"},
        {"id": "passes_defended", "label": "Passes Defended"},
        {"id": "forced_fumbles", "label": "Forced Fumbles"},
        {"id": "fumble_recoveries", "label": "Fumble Recoveries"},
        {"id": "defensive_tds", "label": "Defensive TDs"},
    ]},
    {"label": "Kicking", "stats": [
        {"id": "fg_att", "label": "FG Attempts"},
        {"id": "fg_made", "label": "FG Made"},
        {"id": "fg_pct", "label": "FG %"},
        {"id": "fg_lt30", "label": "FG <30 yds"},
        {"id": "fg_30_39", "label": "FG 30-39 yds"},
        {"id": "fg_40_49", "label": "FG 40-49 yds"},
        {"id": "fg_50_plus", "label": "FG 50+ yds"},
        {"id": "xp_att", "label": "XP Attempts"},
        {"id": "xp_made", "label": "XP Made"},
        {"id": "xp_pct", "label": "XP %"},
    ]},
    {"label": "Punting", "stats": [
        {"id": "punts", "label": "Punts"},
        {"id": "punt_net_yds", "label": "Punt Yards (Net)"},
        {"id": "punt_net_avg", "label": "Net Punt Average"},
        {"id": "punts_inside_20", "label": "Punts Inside 20"},
    ]},
]
PLAYER_DEFAULT_COLUMNS = ["player_name", "player_pos", "player_team", "player_age", "games_played"]
PLAYER_STAT_LABELS = {s["id"]: s["label"] for cat in PLAYER_STAT_CATEGORIES for s in cat["stats"]}
PLAYER_PRESETS: dict[str, list[str]] = {
    "default": PLAYER_DEFAULT_COLUMNS,
    "qb": ["player_name", "player_pos", "player_team", "games_played", "pass_att", "pass_cmp", "pass_cmp_pct", "pass_yds", "pass_yds_per_att", "pass_td", "pass_int", "qb_rating"],
    "rushing": ["player_name", "player_pos", "player_team", "games_played", "rush_att", "rush_yds", "yds_per_rush", "rush_td", "fumbles_lost"],
    "receiving": ["player_name", "player_pos", "player_team", "games_played", "targets", "receptions", "catch_pct", "rec_yds", "rec_td"],
    "defense": ["player_name", "player_pos", "player_team", "games_played", "solo_tackles", "tackles_for_loss", "sacks", "def_int", "passes_defended", "forced_fumbles", "fumble_recoveries", "defensive_tds"],
    "kicking": ["player_name", "player_team", "games_played", "fg_made", "fg_att", "fg_pct", "xp_made", "xp_att", "xp_pct"],
    "punting": ["player_name", "player_team", "games_played", "punts", "punt_net_yds", "punt_net_avg", "punts_inside_20"],
    "all": list(PLAYER_STAT_LABELS),
}

TEAM_STAT_CATEGORIES: list[dict] = [
    {"label": "Identity & Record", "stats": [
        {"id": "team_name", "label": "Team Name"},
        {"id": "conference", "label": "Conference"},
        {"id": "division", "label": "Division"},
        {"id": "wins", "label": "Wins"},
        {"id": "losses", "label": "Losses"},
        {"id": "win_pct", "label": "Win %"},
        {"id": "points_for", "label": "Points For"},
        {"id": "points_against", "label": "Points Against"},
        {"id": "point_diff", "label": "Point Differential"},
        {"id": "power_rating", "label": "Power Rating"},
    ]},
    {"label": "Offense", "stats": [
        {"id": "off_plays", "label": "Offensive Plays"},
        {"id": "off_yds", "label": "Total Yards"},
        {"id": "team_pass_att", "label": "Pass Attempts"},
        {"id": "team_pass_cmp", "label": "Completions"},
        {"id": "team_pass_yds", "label": "Passing Yards"},
        {"id": "team_pass_td", "label": "Passing TDs"},
        {"id": "team_pass_int", "label": "Interceptions Thrown"},
        {"id": "team_rush_att", "label": "Rush Attempts"},
        {"id": "team_rush_yds", "label": "Rushing Yards"},
        {"id": "team_rush_td", "label": "Rushing TDs"},
    ]},
    {"label": "Defense", "stats": [
        {"id": "def_yds_allowed", "label": "Total Yards Allowed"},
        {"id": "team_pass_yds_allowed", "label": "Passing Yards Allowed"},
        {"id": "team_rush_yds_allowed", "label": "Rushing Yards Allowed"},
        {"id": "team_sacks", "label": "Sacks"},
        {"id": "team_int_def", "label": "Interceptions"},
        {"id": "team_fumble_recoveries", "label": "Fumble Recoveries"},
        {"id": "def_turnovers_forced", "label": "Turnovers Forced"},
    ]},
    {"label": "Special Teams", "stats": [
        {"id": "team_fg_pct", "label": "FG %"},
        {"id": "team_punt_net_avg", "label": "Net Punt Average"},
    ]},
]
TEAM_DEFAULT_COLUMNS = ["team_name", "conference", "division", "wins", "losses", "win_pct"]
TEAM_STAT_LABELS = {s["id"]: s["label"] for cat in TEAM_STAT_CATEGORIES for s in cat["stats"]}
TEAM_PRESETS: dict[str, list[str]] = {
    "default": TEAM_DEFAULT_COLUMNS,
    "record": ["team_name", "wins", "losses", "win_pct", "points_for", "points_against", "point_diff", "power_rating"],
    "offense": ["team_name", "wins", "losses", "points_for", "off_yds", "team_pass_yds", "team_rush_yds"],
    "defense": ["team_name", "wins", "losses", "points_against", "def_yds_allowed", "team_sacks", "def_turnovers_forced"],
    "special-teams": ["team_name", "team_fg_pct", "team_punt_net_avg"],
    "all": list(TEAM_STAT_LABELS),
}

STATS_PERCENT_COLUMNS = {"pass_cmp_pct", "catch_pct", "win_pct", "fg_pct", "xp_pct", "team_fg_pct"}
CONFERENCES = ["AFC", "NFC"]
DIVISIONS = ["East", "North", "South", "West"]

# Brian's own explicit ask: Awards Race (Dashboard + Stats page) and the
# Playoffs page's real in-season "current playoff picture" preview both
# wait until Week 4 is complete before showing real content -- a
# 1-3-game sample makes both genuinely misleading (a single 300-yard
# passer "leading" MVP with nobody else having played yet, or a 1-0 team
# looking like a division "winner"). Week 5 is the first week these can
# show real content (i.e. AFTER week 4 completes) -- current_week is the
# NEXT week to simulate, so current_week > 4 means at least 4 weeks are
# already in the books.
STANDINGS_BASED_FEATURES_MIN_WEEK = 5


_STATS_PAGE_AGGREGATES_CACHE: dict[tuple, tuple[list[dict], list[dict]]] = {}


def _clear_stats_page_aggregates_cache() -> None:
    _STATS_PAGE_AGGREGATES_CACHE.clear()


def _stats_page_aggregates(season) -> tuple[list[dict], list[dict]]:
    """Same lru_cache-plus-explicit-clear precedent as
    season_stats.cached_current_season_aggregates (which this function's
    OWN body still doesn't use -- it rebuilds every game's box score a
    second time for kicking/punting/games-played/team-offense-defense
    totals, a genuinely separate pass). Needed once the Team Card (Sec3)
    started calling this once per team on pages with many team_link()s
    (Standings/Power Rankings render 32 rows) -- uncached, that reproduced
    the exact class of bug ROADMAP.md's Sec2d-B item 11 fix already
    covers for the player-card chain (measured 12s+ dashboard loads before
    this cache; see season_stats.cached_current_season_aggregates's own
    docstring for the original incident). Cleared from the same 3
    season_state.py call sites that already clear season_stats's own
    cache (simulate_current_week/reset_season/start_new_season)."""
    key = (season.league_seed, season.season_number, season.current_week)
    if key not in _STATS_PAGE_AGGREGATES_CACHE:
        _STATS_PAGE_AGGREGATES_CACHE.clear()
        _STATS_PAGE_AGGREGATES_CACHE[key] = _stats_page_aggregates_uncached(season)
    return _STATS_PAGE_AGGREGATES_CACHE[key]


def _stats_page_aggregates_uncached(season) -> tuple[list[dict], list[dict]]:
    """Builds the real per-player and per-team rows the Stats page's
    Player/Team tabs display. Reuses the same aggregate_season_stats /
    aggregate_season_defensive_stats helpers the old fixed leaderboards
    and awards.py already share (no reimplemented stat math), plus one
    extra pass over the season's played games for two things those
    helpers don't track: per-player games-played (a player counts as
    having played a game if they were credited with any offensive or
    defensive stat in it) and per-team offense/defense totals (summed
    from the same box_score.py/defensive_box_score.py lines, with
    "yards allowed" read off the OPPONENT's offensive box for that
    game). Identity fields (position/jersey/age/years pro) are joined
    in from the live Player rows by (team_abbr, full_name) -- the same
    lookup key app.main._player_link_or_name already uses -- and left
    as "-"/None if no live match exists (shouldn't happen for a
    currently-simulated season, but a real name/team mismatch should
    show as unknown, not fabricate a player)."""
    passing, rushing, receiving = aggregate_season_stats(season)
    defense = aggregate_season_defensive_stats(season)

    games_played: dict[tuple[str, str], int] = defaultdict(int)
    team_off: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    team_def: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # M13: Kicking/Punting season totals -- box_score.py's KickingLine/
    # PuntingLine (real, per-game, built by M2) were never rolled up into
    # a season aggregate anywhere before this. Kept local to this
    # function (not a new season_stats.py aggregator) since nothing else
    # -- awards.py included -- needs a Kicking/Punting season view yet.
    kicking: dict[tuple[str, str], dict] = {}
    punting: dict[tuple[str, str], dict] = {}
    team_st: dict[str, dict] = defaultdict(lambda: {"fg_made": 0, "fg_att": 0, "punts": 0, "punt_net_yds": 0})

    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            boxes = {abbr: build_box_score(g.result.plays, abbr) for abbr in (g.home_abbr, g.away_abbr)}
            def_boxes = {abbr: build_defensive_box_score(g.result.plays, abbr) for abbr in (g.home_abbr, g.away_abbr)}

            for abbr in (g.home_abbr, g.away_abbr):
                for k in boxes[abbr].kicking:
                    row = kicking.setdefault((abbr, k.name), {
                        "fg_made": 0, "fg_att": 0, "xp_made": 0, "xp_att": 0,
                        "fg_lt30": [0, 0], "fg_30_39": [0, 0], "fg_40_49": [0, 0], "fg_50_plus": [0, 0],
                    })
                    row["fg_made"] += k.fg_made
                    row["fg_att"] += k.fg_attempted
                    row["xp_made"] += k.xp_made
                    row["xp_att"] += k.xp_attempted
                    for bucket, bucket_key in (("<30", "fg_lt30"), ("30-39", "fg_30_39"), ("40-49", "fg_40_49"), ("50+", "fg_50_plus")):
                        made, att = k.fg_by_bucket[bucket]
                        row[bucket_key][0] += made
                        row[bucket_key][1] += att
                    team_st[abbr]["fg_made"] += k.fg_made
                    team_st[abbr]["fg_att"] += k.fg_attempted
                for pu in boxes[abbr].punting:
                    row = punting.setdefault((abbr, pu.name), {"punts": 0, "net_yards": 0, "inside_20": 0})
                    row["punts"] += pu.punts
                    row["net_yards"] += pu.net_yards
                    row["inside_20"] += pu.inside_20
                    team_st[abbr]["punts"] += pu.punts
                    team_st[abbr]["punt_net_yds"] += pu.net_yards
                box = boxes[abbr]
                participants = {p.name for p in box.passing} | {r.name for r in box.rushing} | {rc.name for rc in box.receiving} | {d.name for d in def_boxes[abbr]}
                for name in participants:
                    games_played[(abbr, name)] += 1

                off = team_off[abbr]
                for p in box.passing:
                    off["pass_att"] += p.attempts
                    off["pass_cmp"] += p.completions
                    off["pass_yds"] += p.yards
                    off["pass_td"] += p.touchdowns
                    off["pass_int"] += p.interceptions
                for r in box.rushing:
                    off["rush_att"] += r.carries
                    off["rush_yds"] += r.yards
                    off["rush_td"] += r.touchdowns

                d = team_def[abbr]
                for dl in def_boxes[abbr]:
                    d["sacks"] += dl.sacks
                    d["int"] += dl.interceptions
                    d["fumble_rec"] += dl.fumble_recoveries

            home_pass_yds = sum(p.yards for p in boxes[g.home_abbr].passing)
            home_rush_yds = sum(r.yards for r in boxes[g.home_abbr].rushing)
            away_pass_yds = sum(p.yards for p in boxes[g.away_abbr].passing)
            away_rush_yds = sum(r.yards for r in boxes[g.away_abbr].rushing)
            team_def[g.home_abbr]["pass_yds_allowed"] += away_pass_yds
            team_def[g.home_abbr]["rush_yds_allowed"] += away_rush_yds
            team_def[g.away_abbr]["pass_yds_allowed"] += home_pass_yds
            team_def[g.away_abbr]["rush_yds_allowed"] += home_rush_yds

    with get_session() as s:
        live_players = list(s.exec(select(Player)))
    player_by_key = {(p.team_abbr, p.full_name): p for p in live_players if p.team_abbr}

    all_keys = set(passing) | set(rushing) | set(receiving) | set(defense) | set(kicking) | set(punting)
    player_rows = []
    for abbr, name in all_keys:
        p = player_by_key.get((abbr, name))
        pas = passing.get((abbr, name))
        rus = rushing.get((abbr, name))
        rec = receiving.get((abbr, name))
        dfn = defense.get((abbr, name))
        kck = kicking.get((abbr, name))
        pnt = punting.get((abbr, name))
        player_rows.append({
            "player_name": name,
            "player_pos": p.position.value if p else "-",
            "player_team": abbr,
            "player_num": p.jersey_number if p else None,
            "player_age": p.age if p else None,
            "player_exp": p.years_pro if p else None,
            "games_played": games_played.get((abbr, name), 0),
            "pass_att": pas.attempts if pas else 0,
            "pass_cmp": pas.completions if pas else 0,
            "pass_yds": pas.yards if pas else 0,
            "pass_td": pas.touchdowns if pas else 0,
            "pass_int": pas.interceptions if pas else 0,
            "pass_cmp_pct": round(pas.completions / pas.attempts * 100, 1) if pas and pas.attempts else None,
            "pass_yds_per_att": round(pas.yards / pas.attempts, 1) if pas and pas.attempts else None,
            "sacks_taken": pas.sacks_taken if pas else 0,
            "qb_rating": _passer_rating(pas.attempts, pas.completions, pas.yards, pas.touchdowns, pas.interceptions) if pas else None,
            "rush_att": rus.carries if rus else 0,
            "rush_yds": rus.yards if rus else 0,
            "rush_td": rus.touchdowns if rus else 0,
            "yds_per_rush": round(rus.yards / rus.carries, 1) if rus and rus.carries else None,
            "fumbles_lost": rus.fumbles_lost if rus else 0,
            "targets": rec.targets if rec else 0,
            "receptions": rec.receptions if rec else 0,
            "rec_yds": rec.yards if rec else 0,
            "rec_td": rec.touchdowns if rec else 0,
            "catch_pct": round(rec.receptions / rec.targets * 100, 1) if rec and rec.targets else None,
            "solo_tackles": dfn.solo_tackles if dfn else 0,
            "tackles_for_loss": dfn.tackles_for_loss if dfn else 0,
            "sacks": dfn.sacks if dfn else 0,
            "def_int": dfn.interceptions if dfn else 0,
            "passes_defended": dfn.passes_defended if dfn else 0,
            "forced_fumbles": dfn.forced_fumbles if dfn else 0,
            "fumble_recoveries": dfn.fumble_recoveries if dfn else 0,
            "defensive_tds": dfn.defensive_touchdowns if dfn else 0,
            "fg_att": kck["fg_att"] if kck else 0,
            "fg_made": kck["fg_made"] if kck else 0,
            "fg_pct": round(kck["fg_made"] / kck["fg_att"] * 100, 1) if kck and kck["fg_att"] else None,
            "fg_lt30": f"{kck['fg_lt30'][0]}/{kck['fg_lt30'][1]}" if kck else "-",
            "fg_30_39": f"{kck['fg_30_39'][0]}/{kck['fg_30_39'][1]}" if kck else "-",
            "fg_40_49": f"{kck['fg_40_49'][0]}/{kck['fg_40_49'][1]}" if kck else "-",
            "fg_50_plus": f"{kck['fg_50_plus'][0]}/{kck['fg_50_plus'][1]}" if kck else "-",
            "xp_att": kck["xp_att"] if kck else 0,
            "xp_made": kck["xp_made"] if kck else 0,
            "xp_pct": round(kck["xp_made"] / kck["xp_att"] * 100, 1) if kck and kck["xp_att"] else None,
            "punts": pnt["punts"] if pnt else 0,
            "punt_net_yds": pnt["net_yards"] if pnt else 0,
            "punt_net_avg": round(pnt["net_yards"] / pnt["punts"], 1) if pnt and pnt["punts"] else None,
            "punts_inside_20": pnt["inside_20"] if pnt else 0,
        })

    team_rows = []
    for t in TEAMS:
        rec = season.records[t.abbr]
        off = team_off.get(t.abbr, {})
        d = team_def.get(t.abbr, {})
        team_rows.append({
            "team_name": t.location,
            "team_abbr": t.abbr,
            "conference": t.conference,
            "division": t.division,
            "wins": rec.wins,
            "losses": rec.losses,
            "win_pct": round(rec.win_pct * 100, 1),
            "points_for": rec.points_for,
            "points_against": rec.points_against,
            "point_diff": rec.point_diff,
            "power_rating": round(rec.power_rating, 1),
            "off_plays": off.get("pass_att", 0) + off.get("rush_att", 0),
            "off_yds": off.get("pass_yds", 0) + off.get("rush_yds", 0),
            "team_pass_att": off.get("pass_att", 0),
            "team_pass_cmp": off.get("pass_cmp", 0),
            "team_pass_yds": off.get("pass_yds", 0),
            "team_pass_td": off.get("pass_td", 0),
            "team_pass_int": off.get("pass_int", 0),
            "team_rush_att": off.get("rush_att", 0),
            "team_rush_yds": off.get("rush_yds", 0),
            "team_rush_td": off.get("rush_td", 0),
            "def_yds_allowed": d.get("pass_yds_allowed", 0) + d.get("rush_yds_allowed", 0),
            "team_pass_yds_allowed": d.get("pass_yds_allowed", 0),
            "team_rush_yds_allowed": d.get("rush_yds_allowed", 0),
            "team_sacks": d.get("sacks", 0),
            "team_int_def": d.get("int", 0),
            "team_fumble_recoveries": d.get("fumble_rec", 0),
            "def_turnovers_forced": d.get("int", 0) + d.get("fumble_rec", 0),
            "team_fg_pct": round(team_st[t.abbr]["fg_made"] / team_st[t.abbr]["fg_att"] * 100, 1) if team_st[t.abbr]["fg_att"] else None,
            "team_punt_net_avg": round(team_st[t.abbr]["punt_net_yds"] / team_st[t.abbr]["punts"], 1) if team_st[t.abbr]["punts"] else None,
        })

    return player_rows, team_rows


def _passer_rating(att: int, cmp: int, yds: int, td: int, ints: int) -> float | None:
    """The real, standard NFL passer rating formula (not a fabricated or
    simplified stand-in) -- computed from stats this engine already
    tracks in full (att/cmp/yds/td/int), same as StatColumnChooser.tsx's
    `qb_rating` column."""
    if not att:
        return None
    a = max(0.0, min(2.375, ((cmp / att) - 0.3) * 5))
    b = max(0.0, min(2.375, ((yds / att) - 3) * 0.25))
    c = max(0.0, min(2.375, (td / att) * 20))
    d = max(0.0, min(2.375, 2.375 - (ints / att) * 25))
    return round((a + b + c + d) / 6 * 100, 1)


def _sort_stat_rows(rows: list[dict], key: str, direction: str) -> list[dict]:
    """Nulls always sort last, independent of direction -- matches the
    Figma source's own sort comparator (StatsPage.tsx's handleSort)."""
    have = [r for r in rows if r.get(key) is not None]
    missing = [r for r in rows if r.get(key) is None]
    have.sort(key=lambda r: r[key], reverse=(direction == "desc"))
    return have + missing


@app.get("/stats", response_class=HTMLResponse)
def stats_view(
    request: Request,
    tab: str = "player",
    sort: str | None = None,
    dir: str = "desc",
    team: str = "all",
    pos: str = "all",
    conference: str = "all",
    division: str = "all",
    q: str = "",
    cols: list[str] = Query(default=[]),
    preset: str | None = None,
):
    if tab not in ("player", "team", "coach"):
        tab = "player"

    season = season_state.get_season()
    games_played = sum(1 for week in season.schedule for g in week if g.result is not None)
    awards_race = awards.season_awards(season) if season.current_week >= STANDINGS_BASED_FEATURES_MIN_WEEK else None

    ctx = {
        "season": season, "games_played": games_played, "awards_race": awards_race, "tab": tab,
        "teams": TEAMS, "positions": list(Position), "conferences": CONFERENCES, "divisions": DIVISIONS,
        "team_filter": team, "pos_filter": pos, "conference_filter": conference, "division_filter": division,
        "q": q, "sort": sort,
    }

    if tab == "coach":
        # M13 left this tab as "Coming Soon" because no Coach entity
        # existed. It does now (ROADMAP.md R3), so this is a real
        # leaderboard of every head coach -- sortable on the same
        # GET-param + full-reload convention the Player/Team tabs use.
        ctx["dir"] = dir if dir in ("asc", "desc") else "desc"
        ctx["coach_rows"] = _coach_stat_rows(season, sort or "win_pct", ctx["dir"], q)
        ctx["coach_sort_columns"] = COACH_STAT_COLUMNS
        ctx["has_coaches"] = coach_store.has_coaches()
        return templates.TemplateResponse(request, "stats.html", ctx)

    if games_played == 0:
        ctx["dir"] = dir if dir in ("asc", "desc") else "desc"
        return templates.TemplateResponse(request, "stats.html", ctx)

    player_rows, team_rows = _stats_page_aggregates(season)

    if tab == "player":
        categories, presets, default_cols, labels = PLAYER_STAT_CATEGORIES, PLAYER_PRESETS, PLAYER_DEFAULT_COLUMNS, PLAYER_STAT_LABELS
        rows = player_rows
        if team != "all":
            rows = [r for r in rows if r["player_team"] == team]
        if pos != "all":
            rows = [r for r in rows if r["player_pos"] == pos]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in r["player_name"].lower() or ql in r["player_team"].lower()]
        default_sort, default_dir = "player_name", "asc"
    else:
        categories, presets, default_cols, labels = TEAM_STAT_CATEGORIES, TEAM_PRESETS, TEAM_DEFAULT_COLUMNS, TEAM_STAT_LABELS
        rows = team_rows
        if conference != "all":
            rows = [r for r in rows if r["conference"] == conference]
        if division != "all":
            rows = [r for r in rows if r["division"] == division]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in r["team_name"].lower() or ql in r["team_abbr"].lower()]
        default_sort, default_dir = "wins", "desc"

    valid_ids = set(labels)
    if preset and preset in presets:
        columns = presets[preset]
    else:
        submitted = [c for c in cols if c in valid_ids]
        columns = submitted if submitted else default_cols

    # A raw `sort` param only ever arrives from a header-sort link, which
    # always sends `dir` alongside it -- so an explicit sort honors the
    # requested direction, while the very first (no `sort` yet) load uses
    # a sensible per-tab default (alphabetical for names, best-record-
    # first for team standings) rather than always defaulting to "desc",
    # which read as Z-to-A on an untouched Player tab.
    if sort in valid_ids:
        effective_sort = sort
        direction = dir if dir in ("asc", "desc") else "desc"
    else:
        effective_sort = default_sort
        direction = default_dir
    ctx["dir"] = direction
    rows = _sort_stat_rows(rows, effective_sort, direction)
    display_rows = []
    for r in rows:
        dr = dict(r)
        for pct_col in STATS_PERCENT_COLUMNS:
            if pct_col in dr and dr[pct_col] is not None:
                dr[pct_col] = f"{dr[pct_col]}%"
        display_rows.append(dr)

    def stats_query(overrides: dict) -> str:
        base: dict = {"tab": tab, "cols": columns}
        if tab == "player":
            base["team"], base["pos"] = team, pos
        else:
            base["conference"], base["division"] = conference, division
        if q:
            base["q"] = q
        base.update(overrides)
        params = []
        for key, val in base.items():
            if key == "cols":
                params.extend(("cols", c) for c in val)
            elif val not in (None, ""):
                params.append((key, val))
        return "/stats?" + urlencode(params)

    sort_links = {}
    for cid in columns:
        next_dir = "asc" if (sort == cid and direction == "desc") else "desc"
        sort_links[cid] = stats_query({"sort": cid, "dir": next_dir})

    preset_links = {pid: stats_query({"cols": plist, "sort": None, "dir": None}) for pid, plist in presets.items()}
    reset_link = stats_query({"cols": default_cols, "sort": None, "dir": None})

    ctx.update({
        "categories": categories,
        "labels": labels,
        "column_ids": columns,
        "columns": [{"id": cid, "label": labels[cid]} for cid in columns],
        "rows": display_rows,
        "sort_links": sort_links,
        "preset_links": preset_links,
        "reset_link": reset_link,
        "row_count": len(rows),
    })
    return templates.TemplateResponse(request, "stats.html", ctx)


@app.get("/season", response_class=HTMLResponse)
def season_view(request: Request):
    season = season_state.get_season()
    return templates.TemplateResponse(
        request,
        "season.html",
        {
            "season": season,
            "standings": season.standings(),
            "n_weeks": season_state.N_WEEKS,
            "target_ppg": score_fidelity.TARGET_PPG_PER_TEAM,
        },
    )


@app.get("/season/week/{week_num}/game/{home_abbr}/{away_abbr}", response_class=HTMLResponse)
def season_game_view(request: Request, week_num: int, home_abbr: str, away_abbr: str):
    """Reuses result.html (the single-game simulator's play-by-play +
    box score view) for an already-simulated season game -- season_state
    already retains each game's full GameResult (plays, per-team totals,
    see save_service.py's round-trip), it just had no route/link to view
    one. 404s on an unplayed or nonexistent week/matchup rather than
    rendering an empty page, since there's nothing to show yet."""
    season = season_state.get_season()
    if not (1 <= week_num <= season_state.N_WEEKS):
        raise HTTPException(404, "No such week")

    game = next(
        (g for g in season.schedule[week_num - 1] if g.home_abbr == home_abbr and g.away_abbr == away_abbr),
        None,
    )
    if game is None or game.result is None:
        raise HTTPException(404, "That game hasn't been played yet")

    home_info = TEAMS_BY_ABBR[home_abbr]
    away_info = TEAMS_BY_ABBR[away_abbr]
    home = TeamSim(name=home_info.location, abbr=home_info.abbr, ratings=None)
    away = TeamSim(name=away_info.location, abbr=away_info.abbr, ratings=None)

    result = game.result
    home_box = build_box_score(result.plays, home_info.abbr)
    away_box = build_box_score(result.plays, away_info.abbr)
    home_defense = build_defensive_box_score(result.plays, home_info.abbr)
    away_defense = build_defensive_box_score(result.plays, away_info.abbr)
    game_seed = stable_seed(season.league_seed, week_num, home_abbr, away_abbr)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "home": home,
            "away": away,
            "result": result,
            "quarters": quarter_scores(result.events),
            "league_seed": season.league_seed,
            "game_seed": game_seed,
            "home_box": home_box,
            "away_box": away_box,
            "home_defense": home_defense,
            "away_defense": away_defense,
            "back_url": "/season",
            "back_label": "Back to season",
        },
    )


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', 22 -> '22nd', etc. -- the
    11-13 exception is why this can't be a simple `n % 10` lookup."""
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _header_context() -> dict:
    """GDD Sec 10.3: a persistent header (team badge, name, record/
    division/power-rank, a Sim Week control) visible on EVERY screen,
    not just Dashboard -- registered as a Jinja2 global (see
    `templates.env.globals` below) and called directly from
    base.html, rather than threading the same few values through every
    single route's own context dict for data that's always the same
    shape. Returns user_team=None before a team's been chosen (team-
    select, or a route hit before any franchise setup) -- base.html
    falls back to the plain title in that case."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        return {"user_team": None}
    team = TEAMS_BY_ABBR[season.user_team_abbr]
    record = season.records[season.user_team_abbr]
    rank = next((i for i, r in enumerate(season.standings(), start=1) if r.abbr == team.abbr), None)
    return {
        "user_team": team,
        "user_record": record,
        "user_rank_ordinal": _ordinal(rank) if rank is not None else None,
    }


templates.env.globals["header_context"] = _header_context


# GDD Sec 10.3 / Sec 7.5: player names open a Player Card Modal, everywhere
# a player name appears (Roster, Dashboard leaders, Scouting, box scores,
# Playoffs, Stats leaderboards, ...). Confirmed against the real Figma
# component (PlayerDrawer.tsx) -- same dark-panel/gold-OVR-badge layout,
# same Overview/Ratings/Stats/Contract tab set. Implemented WITHOUT a
# server round-trip per click: the trigger element (see the player_link
# Jinja macro, app/templates/macros.html) carries this player's full data
# as one JSON blob in a data-card attribute, and a single shared <dialog>
# + a small vanilla-JS click handler in base.html reads it and renders
# the card client-side -- consistent with "no per-player pre-rendering,
# no framework, no extra network request" (base.html's own <dialog> is
# the ONE thing on the page, not one hidden card per player).
ATTRIBUTE_LABELS: dict[str, str] = {
    "speed": "Speed", "acceleration": "Acceleration", "strength": "Strength", "agility": "Agility",
    "jumping": "Jumping", "stamina": "Stamina", "toughness": "Toughness", "durability": "Durability (Injury)",
    "throw_power": "Throw Power", "throw_accuracy_short": "Throw Accuracy (Short)",
    "throw_accuracy_mid": "Throw Accuracy (Mid)", "throw_accuracy_deep": "Throw Accuracy (Deep)",
    "play_action": "Play Action", "throw_on_the_run": "Throw on the Run",
    "throw_under_pressure": "Throw Under Pressure", "break_sack": "Break Sack",
    "catching": "Catching", "spectacular_catch": "Spectacular Catch", "catch_in_traffic": "Catch in Traffic",
    "short_route_running": "Short Routes", "medium_route_running": "Medium Routes",
    "deep_route_running": "Deep Routes", "release": "Release",
    "carrying": "Ball Carrying", "trucking": "Trucking", "change_of_direction": "Change of Direction",
    "ball_carrier_vision": "Vision", "stiff_arm": "Stiff Arm", "spin_move": "Spin Move",
    "juke_move": "Juke Move", "break_tackle": "Break Tackle",
    "run_block": "Run Block", "pass_block": "Pass Block", "run_block_power": "Run Block Power",
    "run_block_finesse": "Run Block Finesse", "pass_block_power": "Pass Block Power",
    "pass_block_finesse": "Pass Block Finesse", "lead_block": "Lead Block", "impact_blocking": "Impact Blocking",
    "tackle": "Tackle", "hit_power": "Hit Power", "block_shedding": "Block Shedding",
    "pursuit": "Pursuit", "play_recognition": "Play Recognition", "man_coverage": "Man Coverage",
    "zone_coverage": "Zone Coverage", "press": "Press", "power_moves": "Power Moves", "finesse_moves": "Finesse Moves",
    "kick_power": "Kick Power", "kick_accuracy": "Kick Accuracy", "kick_return": "Kick Return",
    "awareness": "Awareness",
}


def _passing_row(label: str, completions: int, attempts: int, yards: int, touchdowns: int, interceptions: int, sacks_taken: int) -> dict:
    return {
        "season_label": label, "completions": completions, "attempts": attempts,
        "pct": round(completions / attempts * 100, 1) if attempts else None,
        "yards": yards, "ypa": round(yards / attempts, 1) if attempts else None,
        "touchdowns": touchdowns, "interceptions": interceptions, "sacks_taken": sacks_taken,
        "rating": _passer_rating(attempts, completions, yards, touchdowns, interceptions),
    }


def _rushing_row(label: str, carries: int, yards: int, touchdowns: int, fumbles_lost: int) -> dict:
    return {
        "season_label": label, "carries": carries, "yards": yards,
        "avg": round(yards / carries, 1) if carries else None,
        "touchdowns": touchdowns, "fumbles_lost": fumbles_lost,
    }


def _receiving_row(label: str, receptions: int, targets: int, yards: int, touchdowns: int) -> dict:
    return {
        "season_label": label, "receptions": receptions, "targets": targets, "yards": yards,
        "avg": round(yards / receptions, 1) if receptions else None, "touchdowns": touchdowns,
    }


def _defense_row(label: str, solo_tackles: int, tackles_for_loss: int, sacks: int, interceptions: int,
                  passes_defended: int, forced_fumbles: int, fumble_recoveries: int, defensive_touchdowns: int) -> dict:
    return {
        "season_label": label, "solo_tackles": solo_tackles, "tackles_for_loss": tackles_for_loss,
        "sacks": sacks, "interceptions": interceptions, "passes_defended": passes_defended,
        "forced_fumbles": forced_fumbles, "fumble_recoveries": fumble_recoveries,
        "defensive_touchdowns": defensive_touchdowns,
    }


def _season_by_season_stats_for(p: Player) -> dict | None:
    """Player Card Stats tab, redesigned per Brian's own request into a
    real Madden-style year-by-year table instead of one combined career
    total: one row per season (current in-progress season first, then
    every archived season most-recent-first, via
    history_store.season_by_season_stats()), with a Career summary row
    (history_store.career_stats(), unchanged, still real/cumulative)
    appended last. No Team column -- every row would show the same
    abbr today anyway, since no trade system exists yet (Player.team_abbr
    is stable for a player's whole tenure); add one if/when R4c (Trades)
    ever makes it a real per-season fact instead of a constant.
    Games Played/Started aren't included either -- SeasonRecord's
    archived leader lines don't carry that, only the CURRENT season's
    live aggregation does (see _stats_page_aggregates's own games_played
    dict), so it isn't available for past seasons without a real
    archival-schema change this chunk didn't scope."""
    if not p.team_abbr:
        return None

    season = season_state.get_season()
    cur_passing, cur_rushing, cur_receiving, cur_defense = season_stats.cached_current_season_aggregates(season)
    key = (p.team_abbr, p.full_name)
    cur_label = f"Season {season.season_number + 1} (in progress)"

    archived = history_store.season_by_season_stats(p.team_abbr, p.full_name)
    passing_rows = [_passing_row(f"Season {r['season_number'] + 1}", r["completions"], r["attempts"], r["yards"], r["touchdowns"], r["interceptions"], r.get("sacks_taken", 0)) for r in archived["passing"]]
    rushing_rows = [_rushing_row(f"Season {r['season_number'] + 1}", r["carries"], r["yards"], r["touchdowns"], r.get("fumbles_lost", 0)) for r in archived["rushing"]]
    receiving_rows = [_receiving_row(f"Season {r['season_number'] + 1}", r["receptions"], r["targets"], r["yards"], r["touchdowns"]) for r in archived["receiving"]]
    defense_rows = [_defense_row(f"Season {r['season_number'] + 1}", r["solo_tackles"], r["tackles_for_loss"], r["sacks"], r["interceptions"], r["passes_defended"], r["forced_fumbles"], r["fumble_recoveries"], r["defensive_touchdowns"]) for r in archived["defense"]]

    if key in cur_passing:
        l = cur_passing[key]
        passing_rows.insert(0, _passing_row(cur_label, l.completions, l.attempts, l.yards, l.touchdowns, l.interceptions, l.sacks_taken))
    if key in cur_rushing:
        l = cur_rushing[key]
        rushing_rows.insert(0, _rushing_row(cur_label, l.carries, l.yards, l.touchdowns, l.fumbles_lost))
    if key in cur_receiving:
        l = cur_receiving[key]
        receiving_rows.insert(0, _receiving_row(cur_label, l.receptions, l.targets, l.yards, l.touchdowns))
    if key in cur_defense:
        l = cur_defense[key]
        defense_rows.insert(0, _defense_row(cur_label, l.solo_tackles, l.tackles_for_loss, l.sacks, l.interceptions, l.passes_defended, l.forced_fumbles, l.fumble_recoveries, l.defensive_touchdowns))

    career_passing, career_rushing, career_receiving, career_defense = history_store.career_stats()
    if key in career_passing:
        l = career_passing[key]
        passing_rows.append(_passing_row(f"Career ({l.seasons} seasons)", l.completions, l.attempts, l.yards, l.touchdowns, l.interceptions, l.sacks_taken))
    if key in career_rushing:
        l = career_rushing[key]
        rushing_rows.append(_rushing_row(f"Career ({l.seasons} seasons)", l.carries, l.yards, l.touchdowns, l.fumbles_lost))
    if key in career_receiving:
        l = career_receiving[key]
        receiving_rows.append(_receiving_row(f"Career ({l.seasons} seasons)", l.receptions, l.targets, l.yards, l.touchdowns))
    if key in career_defense:
        l = career_defense[key]
        defense_rows.append(_defense_row(f"Career ({l.seasons} seasons)", l.solo_tackles, l.tackles_for_loss, l.sacks, l.interceptions, l.passes_defended, l.forced_fumbles, l.fumble_recoveries, l.defensive_touchdowns))

    lines = {}
    if passing_rows:
        lines["passing"] = passing_rows
    if rushing_rows:
        lines["rushing"] = rushing_rows
    if receiving_rows:
        lines["receiving"] = receiving_rows
    if defense_rows:
        lines["defense"] = defense_rows
    return lines or None


def _injury_summary_for(p: Player) -> dict | None:
    """R1 (GDD Sec 3.8/6.10): the Player Card's real injury status, None
    when healthy -- never a fabricated "Healthy" badge for a database
    that predates this chunk (injury_store degrades to empty gracefully,
    same contract coach_store already established)."""
    injury = injury_store.injury_for_player(p.player_id)
    if injury is None:
        return None
    return {
        "status": "OUT" if injury.is_out else "Questionable (returning)",
        "type": injury.injury_type.value.title(),
        "severity": injury.severity.value.title(),
        "weeks_out": injury.weeks_out,
        "ir": injury.placed_on_ir,
    }


def _player_card_json(p: Player) -> str:
    attrs = {ATTRIBUTE_LABELS.get(a, a): getattr(p, a) for a in PROGRESSED_ATTRIBUTES if a != "overall_rating"}
    return json.dumps({
        "name": p.full_name, "num": p.jersey_number, "pos": p.position.value,
        "age": p.age, "ovr": p.overall_rating, "pot": p.potential,
        "team": p.team_abbr or "FA", "morale": p.morale, "stamina": p.stamina,
        "attrs": attrs, "career": _season_by_season_stats_for(p),
        "salary": p.salary, "signing_bonus": p.signing_bonus,
        "contract_years_remaining": p.contract_years_remaining,
        "injury": _injury_summary_for(p),
    })


templates.env.filters["player_card_json"] = _player_card_json
templates.env.filters["player_injury_status"] = _injury_summary_for
templates.env.filters["money"] = _money


# Stat-line dataclasses (PassingLine, SeasonDefensiveLine, HOFCandidate, ...)
# only ever carry a plain `name` string, not a real Player row -- some of
# them (real-NFL-seeded history, retired players) have NO live Player row
# to find at all. This looks one up by (name, team_abbr) and falls back to
# plain escaped text when there's no live match, rather than fabricating a
# card. Brian's own instruction was "every player name... (except maybe
# HOF)" -- HOF is skipped entirely (see history.html's Hall of Fame tab) since its whole point is
# retired/historical players, most with no live row; this handles the
# other pages (dashboard/stats/history leaders, box scores) where the
# named player is usually still on a live roster but isn't guaranteed to be.
def _player_link_or_name(name: str, team_abbr: str | None) -> Markup:
    if team_abbr:
        with get_session() as s:
            candidates = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
        for p in candidates:
            if p.full_name == name:
                card_json = escape(_player_card_json(p))
                return Markup(f"<button type=\"button\" class=\"player-link\" data-card='{card_json}'>{escape(name)}</button>")
    return escape(name)


templates.env.globals["player_link_or_name"] = _player_link_or_name
templates.env.globals["format_leader_stat_line"] = _format_leader_stat_line


# Team Card (Sec3): forks the Player Card's exact pattern (a JSON blob
# embedded server-side in a data-* attribute, opened client-side by a
# dedicated dialog -- no network fetch) rather than inventing a new UI
# mechanism. Team leaders reuse the same per-player season rows the
# dashboard's Top Performers box already computes (_stats_page_aggregates),
# filtered to this team and ranked one stat at a time via the existing
# _top_performer_leaders() helper -- a straight reuse, not new aggregation.
# "Coaches" reuses the same disclosed _placeholder_coach() the Scouting
# Panel already shows (no real Coach entity exists yet, ROADMAP.md R3).
TEAM_CARD_LEADER_CATEGORIES = [
    ("pass_yds", "Passing Yards"), ("rush_yds", "Rushing Yards"),
    ("rec_yds", "Receiving Yards"), ("sacks", "Sacks"), ("solo_tackles", "Tackles"),
]


def _team_card_json(team_abbr: str) -> str:
    team = TEAMS_BY_ABBR.get(team_abbr)
    if team is None:
        return json.dumps({"abbr": team_abbr, "name": team_abbr, "record": None, "schedule": [], "leaders": [], "coach": None, "roster": []})

    season = season_state.get_season()
    record = season.records.get(team_abbr)
    schedule = []
    for row in _team_schedule_for(season, team_abbr):
        opp = TEAMS_BY_ABBR.get(row["opponent_abbr"])
        schedule.append({**row, "opponent_name": opp.location if opp else row["opponent_abbr"]})

    player_rows, _ = _stats_page_aggregates(season)
    team_rows = [r for r in player_rows if r["player_team"] == team_abbr]
    leaders = []
    for stat_id, label in TEAM_CARD_LEADER_CATEGORIES:
        top = _top_performer_leaders(team_rows, stat_id, top_n=1)
        if top and top[0].get(stat_id):
            leaders.append({"label": label, "name": top[0]["player_name"], "pos": top[0]["player_pos"], "value": top[0][stat_id]})

    with get_session() as s:
        roster_players = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
    roster_players.sort(key=lambda p: -p.overall_rating)

    return json.dumps({
        "abbr": team_abbr, "name": team.location,
        "record": {
            "wins": record.wins, "losses": record.losses,
            "pf": record.points_for, "pa": record.points_against,
            "power": round(record.power_rating),
        } if record else None,
        "schedule": schedule,
        "leaders": leaders,
        "coach": _head_coach_summary(team_abbr) or _placeholder_coach(),
        "roster": [{"name": p.full_name, "pos": p.position.value, "ovr": p.overall_rating} for p in roster_players],
    })


def _team_link(abbr: str | None, label: str | None = None) -> Markup:
    if not abbr or abbr not in TEAMS_BY_ABBR:
        return escape(label or abbr or "")
    card_json = escape(_team_card_json(abbr))
    return Markup(f"<button type=\"button\" class=\"team-link\" data-team-card='{card_json}'>{escape(label or abbr)}</button>")


templates.env.globals["team_link"] = _team_link


def _grouped_teams() -> dict[str, dict[str, list[TeamInfo]]]:
    grouped: dict[str, dict[str, list[TeamInfo]]] = {}
    for t in TEAMS:
        grouped.setdefault(t.conference, {}).setdefault(t.division, []).append(t)
    return grouped


ROUND_LABELS = {"WC": "Wild Card", "DIV": "Divisional", "CONF": "Conference Championship", "SB": "Super Bowl"}


def _hof_new_inductee_keys(full_history: list, full_inductee_keys: set[tuple[str, str]]) -> set[tuple[str, str]]:
    """Which of `full_inductee_keys` (the CURRENT Hall of Fame class,
    already computed by the caller) weren't there as of the PREVIOUS
    archived season -- i.e. genuinely inducted this cycle, matching GDD
    Sec 10.4.8's "Class of [current year] Inductees" highlight section.
    history_store.hall_of_fame() only ever answers "who qualifies right
    now" (it recomputes from career_stats() fresh every call, no stored
    induction-year field) -- so this re-runs it against history with
    the most recent season dropped, via a throwaway temp file (the only
    way to feed it a truncated history without changing its path-only
    signature, which a concurrent M6 session was actively editing for
    its own real reasons -- lru_cache-ing career_stats() -- while this
    chunk was built), and diffs the two candidate sets."""
    if len(full_history) < 2:
        return set()
    prior_dicts = [history_store._record_to_dict(r) for r in full_history[:-1]]
    with tempfile.TemporaryDirectory() as d:
        temp_path = Path(d) / "prior_history.json"
        history_store._save(prior_dicts, temp_path)
        prior_inductees = history_store.hall_of_fame(path=temp_path)
    prior_keys = {(c.team_abbr, c.name) for c in prior_inductees}
    return full_inductee_keys - prior_keys


def _hof_all_years_active(full_history: list) -> dict[str, str]:
    """(team_abbr|name) -> a human-facing "Season X" or "Season X-Y"
    span, derived from real per-season leader presence across the
    archive (passing/rushing/receiving/defensive_leaders already carry
    every credited player, not just top-N, since the top-15 cap was
    removed for career_stats()'s sake -- see history_store.py's own
    docstring). +1 everywhere to match history.html's own season-number-
    is-zero-indexed convention."""
    spans: dict[str, list[int]] = {}
    for rec in full_history:
        for pool in (rec.passing_leaders, rec.rushing_leaders, rec.receiving_leaders, rec.defensive_leaders):
            for l in pool:
                spans.setdefault(f"{l.team_abbr}|{l.name}", []).append(rec.season_number)
    return {
        k: (f"Season {min(v) + 1}" if min(v) == max(v) else f"Season {min(v) + 1}–{max(v) + 1}")
        for k, v in spans.items()
    }


def _hof_eligible_candidates(inductee_keys: set[tuple[str, str]], limit: int = 10, path: Path | None = None) -> list[dict]:
    """Real, not-yet-inducted players who've cleared history_store's own
    MIN_HOF_SEASONS bar -- GDD Sec 10.4.8's "Eligible Candidates" list
    (this engine has no voting system, so `progress_pct` stands in for
    the Figma source's voting percentage: each category's own primary
    counting stat as a percentage of that category's current pool
    leader -- a real, if simplified, "how close" proxy, not the exact
    private HOF composite score formula that lives inside
    history_store.hall_of_fame() -- disclosed in the template rather
    than duplicating that formula here). `path` mirrors career_stats()'s
    own optional-path signature (None = the real live history file) --
    lets tests pass a temp path directly instead of monkeypatching
    history_store.DEFAULT_PATH, which would collide with career_stats()'s
    own lru_cache (keyed on the path ARGUMENT, not on DEFAULT_PATH)."""
    passing, rushing, receiving, defense = history_store.career_stats(path)

    def _pool(pool: dict, position: str, stat_fmt, primary):
        eligible = [
            l for l in pool.values()
            if l.seasons >= history_store.MIN_HOF_SEASONS and (l.team_abbr, l.name) not in inductee_keys
        ]
        if not eligible:
            return []
        peak = max(primary(l) for l in eligible) or 1
        return [
            {
                "name": l.name, "team_abbr": l.team_abbr, "position": position, "seasons": l.seasons,
                "stat_line": stat_fmt(l), "progress_pct": round(100 * primary(l) / peak),
            }
            for l in eligible
        ]

    candidates = (
        _pool(passing, "QB", lambda l: f"{l.yards:,} career pass yds, {l.touchdowns} TD", lambda l: l.yards)
        + _pool(rushing, "RB", lambda l: f"{l.yards:,} career rush yds, {l.touchdowns} TD", lambda l: l.yards)
        + _pool(receiving, "WR/TE", lambda l: f"{l.yards:,} career rec yds, {l.touchdowns} TD", lambda l: l.yards)
        + _pool(defense, "DEF", lambda l: f"{l.solo_tackles} career tkl, {l.sacks} sacks, {l.interceptions} INT", lambda l: l.solo_tackles)
    )
    return sorted(candidates, key=lambda c: -c["progress_pct"])[:limit]


def _hof_record_book(path: Path | None = None) -> list[dict]:
    """GDD Sec 10.4.8's League Record Book: top-10 all-time leaders per
    major real category, from the same real career_stats() archive the
    Hall of Fame itself is built on -- one card per category, most-
    productive-first. Field goals are deliberately omitted: M2 built a
    real per-game Kicking box-score line, but nothing rolls it into a
    season or career total anywhere yet, so a Kicking category here
    would have to be fabricated rather than real -- disclosed in the
    template instead of guessed at. `path` mirrors career_stats()'s own
    optional-path signature -- see _hof_eligible_candidates()'s
    docstring for why (lets tests bypass career_stats()'s lru_cache)."""
    passing, rushing, receiving, defense = history_store.career_stats(path)

    def _top(pool: dict, key, limit=10):
        ranked = sorted((l for l in pool.values() if key(l) > 0), key=lambda l: -key(l))
        return [(l.name, l.team_abbr, key(l)) for l in ranked[:limit]]

    return [
        {"label": "Passing Yards", "leaders": _top(passing, lambda l: l.yards)},
        {"label": "Passing TDs", "leaders": _top(passing, lambda l: l.touchdowns)},
        {"label": "Rushing Yards", "leaders": _top(rushing, lambda l: l.yards)},
        {"label": "Rushing TDs", "leaders": _top(rushing, lambda l: l.touchdowns)},
        {"label": "Receiving Yards", "leaders": _top(receiving, lambda l: l.yards)},
        {"label": "Receiving TDs", "leaders": _top(receiving, lambda l: l.touchdowns)},
        {"label": "Sacks", "leaders": _top(defense, lambda l: l.sacks)},
        {"label": "Interceptions", "leaders": _top(defense, lambda l: l.interceptions)},
    ]


def _team_finish(rec: "history_store.SeasonRecord", team_abbr: str) -> str:
    """The one-line "how did this team's season end" label for the Team
    History box (ROADMAP.md, History/HOF merge, 2026-09-11), in Brian's
    explicit priority order: Super Bowl Champion beats Conference
    Champion beats Division Winner beats plain division placement. Real
    data throughout -- champion_abbr/afc_champion_abbr/nfc_champion_abbr
    and division_rank are all computed once, live, at archive_season()
    time (see history_store.py), not re-derived or guessed here."""
    if rec.champion_abbr == team_abbr:
        return "Super Bowl Champion"
    if rec.afc_champion_abbr == team_abbr:
        return "AFC Conference Champion"
    if rec.nfc_champion_abbr == team_abbr:
        return "NFC Conference Champion"
    tr = next((t for t in rec.team_results if t.abbr == team_abbr), None)
    if tr is None or tr.division_rank == 0:
        return "—"
    if tr.division_rank == 1:
        return "Division Winner"
    return f"{_ordinal(tr.division_rank)} in {TEAMS_BY_ABBR[team_abbr].division}"


def _team_history_for(team_abbr: str, full_history: list) -> list[dict]:
    """Team History box (ROADMAP.md, History/HOF merge, 2026-09-11):
    the user's own franchise's real season-by-season record -- year,
    end-of-season power rank (among all 32 teams, the same power_rating
    every other page already ranks by), finish (_team_finish() above),
    real W-L record, and any real MVP/OPOY/DPOY/ROY awards this team's
    own players actually won that season (index 0 of each category's
    archived list is the season's winner, same convention history.html/
    hof.html already use). Deliberately no Coach of the Year line -- no
    Coach entity exists anywhere in this engine yet (ROADMAP.md R3 is
    docs-only so far). Deliberately no attendance/profit column -- this
    engine has no financial/attendance model for either, and Brian
    explicitly asked for them to be left out even if they had existed.
    Most-recent-season-first, matching every other list on this page.

    Power rank is None (rendered as "—", not a misleading number) for any
    season where every team shares the same power_rating -- real for the
    24 real-NFL-history seasons scripts/import_nfl_history.py seeded:
    that script's own docstring discloses it has no real historical
    Power Rating to import, so every team there sits at the same 1500.0
    baseline. Ranking a flat tie would produce a real-looking but
    meaningless placement (a 14-3 Super Bowl champion "ranked 32nd of
    32" purely from stable-sort tie order) -- caught live while
    verifying this box, not a hypothetical."""
    rows = []
    for rec in reversed(full_history):
        tr = next((t for t in rec.team_results if t.abbr == team_abbr), None)
        if tr is None:
            continue
        has_real_spread = len({t.power_rating for t in rec.team_results}) > 1
        power_rank = None
        if has_real_spread:
            ranked = sorted(rec.team_results, key=lambda t: -t.power_rating)
            power_rank = next((i + 1 for i, t in enumerate(ranked) if t.abbr == team_abbr), None)
        awards_won = [
            label for label, candidates in [
                ("MVP", rec.awards.mvp), ("OPOY", rec.awards.opoy),
                ("DPOY", rec.awards.dpoy), ("ROY", rec.awards.roy),
            ]
            if candidates and candidates[0].team_abbr == team_abbr
        ]
        rows.append({
            "season_number": rec.season_number,
            "power_rank": power_rank,
            "finish": _team_finish(rec, team_abbr),
            "wins": tr.wins,
            "losses": tr.losses,
            "awards_won": awards_won,
        })
    return rows


@app.get("/history", response_class=HTMLResponse)
def history_view(request: Request, tab: str = "league", pos: str = "all", q: str = ""):
    """League History + Hall of Fame, combined into one page with two
    top-level tabs (Brian's explicit ask, 2026-09-11) -- previously two
    separate pages/routes (this route, and /hof below, now a redirect
    here for any old links). `tab` picks which one opens by default
    ("league" or "hof"); `pos`/`q` are the Hall of Fame Members filter,
    unchanged from the old /hof route's own query params.

    League History tab: a new Team History box (the user's own
    franchise's real season-by-season record -- see _team_history_for())
    alongside the pre-existing per-season League History cards (champion,
    seeds, awards, stat leaders), now enhanced with the real Super Bowl
    matchup + final score and real AFC/NFC conference champions (see
    history_store.archive_season()'s 2026-09-11 additions -- closes the
    "runner-up/final score not archived" gap the old Super Bowl History
    table used to disclose). Still genuinely unavailable and disclosed
    rather than faked: quarter-by-quarter scoring (no clock/quarter
    model anywhere in this engine, same gap the Dashboard's Box Score
    box already discloses) and Super Bowl MVP / winning-coach detail by
    role (no per-game MVP stat, no Coach entity -- see ROADMAP.md's
    R3/R9 notes).

    Hall of Fame tab: unchanged from the old /hof route -- real
    induction, Class of Season N Inductees, Eligible Candidates,
    filterable Members, League Record Book. See history_store.py's own
    docstring for the disclosed, GDD-underspecified induction formula."""
    season = season_state.get_season()
    full_history = history_store.get_history()
    records = list(reversed(full_history))
    team_history = _team_history_for(season.user_team_abbr, full_history) if season.user_team_abbr else []

    inductees = history_store.hall_of_fame()
    inductee_keys = {(c.team_abbr, c.name) for c in inductees}
    new_keys = _hof_new_inductee_keys(full_history, inductee_keys)
    new_inductees = [c for c in inductees if (c.team_abbr, c.name) in new_keys]

    positions = sorted({c.position for c in inductees})
    members = inductees
    if pos != "all":
        members = [c for c in members if c.position == pos]
    if q:
        ql = q.lower()
        members = [c for c in members if ql in c.name.lower() or ql in c.team_abbr.lower()]

    years_active = _hof_all_years_active(full_history)
    eligible = _hof_eligible_candidates(inductee_keys)
    record_book = _hof_record_book() if full_history else []
    sb_history = [rec for rec in reversed(full_history) if rec.champion_abbr]
    current_season_label = (full_history[-1].season_number + 1) if full_history else None

    return templates.TemplateResponse(request, "history.html", {
        "records": records,
        "team_history": team_history,
        "user_team_abbr": season.user_team_abbr,
        "active_tab": tab,
        "new_inductees": new_inductees,
        "members": members,
        "total_members": len(inductees),
        "eligible": eligible,
        "record_book": record_book,
        "sb_history": sb_history,
        "years_active": years_active,
        "positions": positions,
        "pos_filter": pos,
        "q": q,
        "current_season_label": current_season_label,
    })


@app.get("/hof")
def hof_view_redirect(pos: str = "all", q: str = ""):
    """The old standalone Hall of Fame page merged into /history as a
    tab (Brian's explicit ask, 2026-09-11). Kept as a redirect rather
    than removed, so any old bookmarks/links -- including this app's
    own former hof.html self-links -- keep working."""
    params = {"tab": "hof"}
    if pos != "all":
        params["pos"] = pos
    if q:
        params["q"] = q
    return RedirectResponse(url=f"/history?{urlencode(params)}", status_code=307)


# GDD Sec 9.2.5 (Staff - Coaching Roster & Modifiers) / Figma
# StaffPage.tsx + HeadCoachBox.tsx + CoachCardModal.tsx. Built from the
# real .tsx component sources, not the page's own stale doc blurb --
# ROADMAP.md Sec2b's standing lesson.
#
# What's real and built: every coach on the staff (the real 2026 seed),
# their role/specialty/salary, an Overall and Reputation dial, the
# scheme tags, a Coach Card with the full Sec 7.7.2.2/7.7.2.3 rating
# breakdown and the Sec 7.9 career championship record, a real
# league-wide Find Coaches search, vacant-seat rendering, and a real
# "Trait Effects" panel showing the ACTUAL sim biases this staff
# produces (app/engine/coaching.py's StaffEffect) rather than the
# source's hardcoded demo matrix.
#
# Deliberately NOT built, each disclosed on the page rather than faked:
# - Hire / Fire / Re-sign / Negotiate buttons. GDD Sec 8.2.3's hiring
#   market needs the same offer/negotiation machinery R4a builds for
#   player contracts; a button that silently swapped one generated coach
#   for another would be worse than no button.
# - The source's per-coach "Focus Area" dropdown. It has no consumer
#   anywhere in this engine -- nothing reads a focus area -- so it would
#   be a control that visibly does nothing.
# - "Background" / "Attitude" / "Style" (source fields). No real source
#   and no sim consumer; the real scheme-profile tags cover the same
#   ground with something the engine actually reads.
STAFF_ROLE_ORDER = [CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.ST]


def _staff_effect_rows(effect) -> list[tuple[str, str, str]]:
    """GDD Sec 9.2.5.1's "Trait Effects Matrix", built from the REAL
    biases this staff feeds into the sim (app/engine/coaching.py), so
    the panel shows what the staff is actually doing this season rather
    than a static description of what a coach could theoretically do.
    Each row is (label, value, which engine system consumes it)."""
    def pct(x):
        return f"{x * 100:+.1f}%"

    return [
        ("Pass/run mix", pct(effect.pass_bias), "Play-calling (Sec 6.6.1)"),
        ("Red-zone pass lean", pct(effect.rz_pass_bias), "Play-calling, inside the 20"),
        ("4th-down aggression", pct(effect.fourth_down_bias), "4th-down decision (Sec 6.6.4)"),
        ("Two-point tendency", pct(effect.two_point_bias), "PAT vs. 2-pt (Sec 6.8)"),
        ("Blitz rate", pct(effect.blitz_bias), "Defensive call (Sec 6.6.3)"),
        ("Man coverage", f"{(effect.man_coverage_prob or 0.40) * 100:.0f}%", "Coverage call (league default 40%)"),
        ("Penalty rate", f"{effect.penalty_rate_multiplier:.2f}x", "Penalty system (Sec 7.7.4)"),
        ("FG attempt range", f"{effect.fg_range_bonus:+.1f} yds", "Field-goal decision"),
        ("Player development (off)", f"{effect.dev_multiplier_offense:.2f}x", "Offseason progression (Sec 7.6)"),
        ("Player development (def)", f"{effect.dev_multiplier_defense:.2f}x", "Offseason progression (Sec 7.6)"),
    ]


# Stats page Coach tab (GDD Sec 7.6's Coach stat catalog / Figma
# StatsPage.tsx's third tab). Every column is real: the season W-L comes
# from the live Season records, the career totals from the coach's own
# accumulated Sec 7.9 record, and the ratings from the Coach row itself.
# Deliberately NOT included: any per-game coaching stat (challenges,
# timeouts, clock decisions) -- this engine has no clock or challenge
# model at all, so there is nothing real to count.
COACH_STAT_COLUMNS = [
    ("coach", "Coach", False),
    ("team", "Team", False),
    ("role", "Role", False),
    ("record", "Season", True),
    ("win_pct", "Win%", True),
    ("career", "Career", True),
    ("seasons", "Sea", True),
    ("titles", "Conf", True),
    ("rings", "SB", True),
    ("overall", "OVR", True),
    ("reputation", "Rep", True),
    ("jss", "Job Sec", True),
]


def _coach_stat_rows(season, sort: str, direction: str, query: str = "") -> list[dict]:
    """One row per head coach, with this season's real record alongside
    their accumulated career record. Head coaches only, for the same
    reason coach_of_the_year() uses only head coaches: a team's W-L is
    the head coach's result, and attributing the same 13-4 to all 14
    staff members would make the leaderboard meaningless."""
    rows = []
    q = query.strip().lower()
    for coach in coach_store.all_coaches():
        if coach.retired or not coach.team_abbr or CoachRole(coach.role) is not CoachRole.HC:
            continue
        if q and q not in coach.full_name.lower() and q != coach.team_abbr.lower():
            continue
        record = season.records.get(coach.team_abbr)
        wins = record.wins if record else 0
        losses = record.losses if record else 0
        rows.append({
            "coach": coach.full_name,
            "card": _coach_card_json(coach),
            "team": coach.team_abbr,
            "role": ROLE_TITLES[CoachRole(coach.role)],
            "record": f"{wins}-{losses}",
            "win_pct": round(record.win_pct, 3) if record else 0.0,
            "career": f"{coach.career_wins}-{coach.career_losses}",
            "career_wins": coach.career_wins,
            "seasons": coach.seasons_coached,
            "titles": coach.conference_titles,
            "rings": coach.super_bowl_wins,
            "overall": coach.overall,
            "reputation": coach.reputation,
            "jss": round(coach.job_security_score, 1),
        })

    sort_keys = {
        "record": lambda r: r["win_pct"], "win_pct": lambda r: r["win_pct"],
        "career": lambda r: r["career_wins"], "seasons": lambda r: r["seasons"],
        "titles": lambda r: r["titles"], "rings": lambda r: r["rings"],
        "overall": lambda r: r["overall"], "reputation": lambda r: r["reputation"],
        "jss": lambda r: r["jss"],
    }
    key = sort_keys.get(sort, sort_keys["win_pct"])
    rows.sort(key=lambda r: (key(r), r["coach"]), reverse=(direction != "asc"))
    return rows


@app.get("/staff", response_class=HTMLResponse)
def staff_view(request: Request, q: str = "", role: str = "", team: str = ""):
    """Real Staff page. `team` lets any team's staff be viewed (the
    Scouting Panel's Head Coach link and Find Coaches results both point
    here); it defaults to the user's own team, same convention /roster
    already uses."""
    from app.engine import coaching

    season = season_state.get_season()
    if not coach_store.has_coaches():
        # A database that predates scripts/import_coaches.py -- say so
        # honestly and say how to fix it, rather than rendering 32 empty
        # boxes or pretending the page doesn't exist.
        return templates.TemplateResponse(request, "coming_soon.html", {
            "title": "Staff",
            "season": season,
            "summary": "No coaching staff has been imported into this database yet. Run "
                        "`scripts/import_coaches.py` to seed all 32 teams' real staffs from "
                        "data/raw/coaches/, then reload this page.",
        })

    team_abbr = team or season.user_team_abbr or TEAMS[0].abbr
    staff = coach_store.staff_for(team_abbr)
    by_role = {}
    for coach in staff:
        by_role.setdefault(CoachRole(coach.role), []).append(coach)

    positions = []
    for r in STAFF_ROLE_ORDER:
        holder = by_role.get(r, [None])[0]
        positions.append({
            "role": r.value,
            "title": ROLE_TITLES[r],
            "coach": holder,
            "card": _coach_card_json(holder) if holder else None,
        })
    assistant_rows = [
        {"coach": c, "card": _coach_card_json(c)} for c in by_role.get(CoachRole.AC, [])
    ]

    effect = coaching.staff_effect_for(team_abbr)
    search_results = []
    if q or role:
        search_results = [
            {"coach": c, "card": _coach_card_json(c)}
            for c in coach_store.search(q, role=role, limit=40)
        ]

    return templates.TemplateResponse(request, "staff.html", {
        "season": season,
        "team_abbr": team_abbr,
        "team": TEAMS_BY_ABBR[team_abbr],
        "teams": TEAMS,
        "positions": positions,
        "assistants": assistant_rows,
        "staff_size": len(staff),
        "payroll": _money(sum(c.salary_aav for c in staff)),
        "effect_rows": _staff_effect_rows(effect),
        "search_results": search_results,
        "q": q,
        "role": role,
        "role_options": [(r.value, ROLE_TITLES[r]) for r in
                          (CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.ST, CoachRole.AC)],
        "free_agent_count": len(coach_store.free_agents()),
    })


@app.get("/gm-desk", response_class=HTMLResponse)
def gm_desk_view(request: Request, offer_result: str | None = None, offer_player: str | None = None,
                  counter_aav: str | None = None, counter_years: str | None = None):
    """GDD Sec 10.4.4 / R4a (GDD Sec 8.3): real Cap Summary and Re-sign
    flow, real expiring-contract list. Trade-block browsing/offers and
    draft-eligible prospects still need Trades (R4c) and the Draft (R5),
    which this chunk doesn't build -- disclosed via the summary text at
    the bottom of the page rather than silently omitted."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        return RedirectResponse(url="/team-select", status_code=303)
    user_abbr = season.user_team_abbr

    with get_session() as s:
        roster = list(s.exec(select(Player).where(Player.team_abbr == user_abbr)))

    cap = round(contracts.salary_cap_for_season(season.season_number))
    cap_space = round(contracts.team_cap_space(roster, season.season_number))
    top_cap_hits = sorted(roster, key=lambda p: -p.salary)[:10]
    expiring = sorted(
        (p for p in roster if p.contract_years_remaining <= 1),
        key=lambda p: (p.contract_years_remaining, -p.overall_rating),
    )

    offer_feedback = None
    if offer_result and offer_player:
        offer_feedback = {
            "player_name": offer_player, "verdict": offer_result,
            "counter_aav": int(counter_aav) if counter_aav else None,
            "counter_years": int(counter_years) if counter_years else None,
        }

    return templates.TemplateResponse(request, "gm_desk.html", {
        "title": "GM Desk",
        "season": season, "user_info": TEAMS_BY_ABBR[user_abbr],
        "cap": cap, "cap_space": cap_space, "cap_used": cap - cap_space,
        "top_cap_hits": top_cap_hits, "expiring": expiring,
        "offer_feedback": offer_feedback,
    })


@app.post("/gm-desk/offer")
def gm_desk_offer(request: Request, player_id: str = Form(...), aav: int = Form(...), years: int = Form(...)):
    """R4a's real negotiation flow (GDD Sec 8.3.3): a single deterministic
    ACCEPT/REJECT/COUNTER verdict per submitted offer -- see
    app/engine/contracts.py's module docstring for why this skips Sec
    8.3.3's stateful Mood Meter. An ACCEPT really updates the player's
    real salary/contract_years_remaining in the DB; REJECT/COUNTER
    change nothing."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        raise HTTPException(404, "No team chosen yet")
    if years < 1 or years > 7 or aav < 0:
        raise HTTPException(422, "Invalid offer terms")

    with get_session() as s:
        player = s.get(Player, player_id)
        if player is None or player.team_abbr != season.user_team_abbr:
            raise HTTPException(404, "Player not found on your roster")

        team_rating = roster_strength.compute_roster_strength(season.user_team_abbr).team_rating
        result = contracts.evaluate_offer(player, float(aav), years, season.season_number, team_rating)

        if result.verdict == contracts.OfferVerdict.ACCEPT:
            player.salary = aav
            player.contract_years_remaining = years
            s.add(player)
            s.commit()

        params = {"offer_result": result.verdict.value, "offer_player": player.full_name}
        if result.verdict == contracts.OfferVerdict.COUNTER:
            params["counter_aav"] = result.counter_aav
            params["counter_years"] = result.counter_years

    return RedirectResponse(url="/gm-desk?" + urlencode(params), status_code=303)


@app.get("/draft", response_class=HTMLResponse)
def draft_view(request: Request):
    """GDD Sec 10.4.5: Post-MVP."""
    return templates.TemplateResponse(request, "coming_soon.html", {
        "title": "Draft",
        "gdd_section": "GDD §10.4.5",
        "summary": "A draft-class scouting board (reusing the Roster table interface, with multi-select "
                    "prospect comparison), your draft picks by round, and position-quota filtering. Needs the "
                    "Draft system (Part 2) first.",
    })


PLAYOFF_VIEWS = ("full", "afc", "nfc", "superbowl")


def _rounds_by_conference(bracket, conference: str | None) -> dict[str, list]:
    """Bracket rounds filtered to one conference (WC/DIV/CONF matchups
    for "AFC"/"NFC", or the single Super Bowl matchup for `None`) --
    each round in `bracket.rounds` mixes both conferences' games
    together (and the WC/DIV/CONF rounds happen in the same round-list
    entry for whichever games are ready), so the Full/AFC/NFC/Super Bowl
    tab views (GDD Sec 10.4.6) all read from this rather than each
    re-filtering `bracket.rounds` in the template."""
    result: dict[str, list] = {}
    for round_ in bracket.rounds:
        name = round_[0].round_name
        result[name] = [m for m in round_ if m.conference == conference]
    return result


def _conference_hunt_and_standings(season, afc_seeds: list[str], nfc_seeds: list[str]) -> tuple[dict, dict]:
    """Real "In The Hunt" bubble teams and real division standings for
    the AFC/NFC Playoffs views (GDD Sec 10.4.6) -- both built from the
    same real tiebreak-chain functions the bracket seeding itself uses
    (`bubble_teams`/`final_division_standings` in playoffs.py), not a
    separate approximate ranking.

    Takes plain seed lists rather than a `PlayoffBracket` (ROADMAP.md
    Sec2c follow-up: Brian's own ask for a real in-season "current
    playoff picture" preview, not just a post-season one) -- `seed_
    conference()` is pure computation over `season.records` and works
    perfectly well mid-season, so this function never actually needed a
    real, already-built bracket at all. Callers pass either
    `bracket.afc_seeds`/`nfc_seeds` (post-season, real final seeds) or
    `seed_conference(season, "AFC"/"NFC")` directly (in-season, "if the
    season ended today" seeds) -- same function, same real tiebreak
    logic either way.

    M12 correction adds two real per-team fields HuntCard.tsx specifies
    (`seed_if_made`/`gb`), computed rather than fabricated:
    - `seed_if_made`: `8 + index` in `bubble_teams`' own real wildcard-
      tiebreak-chain order (the exact order between bubble teams is
      exact, from the real chain -- the "8" starting point is a stated,
      disclosed simplifying convention assuming all 7 real seeds already
      outrank every bubble team in that same chain, true for the
      overwhelming majority of real standings; not re-deriving a second,
      separate absolute-rank computation across all 16 conference teams
      just to cover the rare case a weak division winner doesn't).
    - `gb` ("games back"): the standard sports games-behind formula
      against the conference's actual 7-seed (the real cutoff line),
      using each team's real win/loss record -- not a modeled stat, just
      arithmetic on data already in `season.records`.
    """
    div_standings_raw = final_division_standings(season)
    hunt: dict[str, list[dict]] = {}
    standings: dict[str, dict[str, list[dict]]] = {}
    for conf, seeds in (("AFC", afc_seeds), ("NFC", nfc_seeds)):
        cutoff = season.records[seeds[6]]  # the real 7-seed -- the actual bubble line
        bubble = bubble_teams(season, conf, seeds)
        hunt[conf] = [
            {
                "abbr": abbr, "location": TEAMS_BY_ABBR[abbr].location, "record": season.records[abbr],
                "seed_if_made": 8 + i,
                "gb": round(((cutoff.wins - season.records[abbr].wins) + (season.records[abbr].losses - cutoff.losses)) / 2, 1),
            }
            for i, abbr in enumerate(bubble)
        ]
        standings[conf] = {
            div: [
                {"abbr": abbr, "location": TEAMS_BY_ABBR[abbr].location, "record": season.records[abbr]}
                for abbr in abbrs
            ]
            for (c, div), abbrs in div_standings_raw.items() if c == conf
        }
    return hunt, standings


def _conference_champion(bracket, conference: str) -> dict | None:
    """The real conference champion once that conference's CONF round is
    complete, for the Full Bracket/Conference Bracket Champion columns
    (FullPlayoffTree.tsx/ConferenceBracket.tsx) -- None (renders as TBD)
    until then."""
    conf_matchup = next((m for round_ in bracket.rounds for m in round_ if m.conference == conference and m.round_name == "CONF"), None)
    if conf_matchup is None or not conf_matchup.is_complete:
        return None
    return {"abbr": conf_matchup.winner_abbr, "seed": conf_matchup.winner_seed, "location": TEAMS_BY_ABBR[conf_matchup.winner_abbr].location}


@app.get("/playoffs", response_class=HTMLResponse)
def playoffs_view(request: Request, view: str = "full"):
    """GDD Sec 10.4.6: Full Bracket / AFC / NFC / Super Bowl tab views,
    matching the Figma-derived layout -- AFC/NFC views also show real
    "In The Hunt" bubble teams and real division standings.

    ROADMAP.md Sec2c follow-up: before the regular season finishes (no
    real bracket exists yet), Week 5+ shows a real "current playoff
    picture" preview instead of nothing -- current seeds/hunt/standings
    computed live from `season.records` via `seed_conference()` (pure
    computation, not dependent on a real, already-built bracket), same
    real data the post-season view uses, just not yet final. Weeks 1-4
    show a "check back after Week 4" message instead (see
    STANDINGS_BASED_FEATURES_MIN_WEEK's own docstring for why).

    Brian flagged (2026-09-11) that this preview didn't read as a
    bracket at all -- just hunt cards and standings tables, unlike
    Figma's FullPlayoffTree.tsx which always renders a 9-column tree
    (with TBD placeholders for anything not decided yet). Added a real
    projected Wild Card round via `build_wild_card_round()` -- the exact
    same pure function (seeds from `seed_conference()`, no mutation of
    `season`) that builds the REAL Week-18+ Wild Card round, just called
    a few weeks early against the current in-progress standings. DIV/
    CONF/Champ/SB stay genuinely TBD (those rounds' matchups depend on
    WC results that don't exist yet), rendered with the Full Bracket
    tab's own `full_tree` macro so this is the same visual component,
    not a second implementation."""
    if view not in PLAYOFF_VIEWS:
        view = "full"
    season = season_state.get_season()
    if not season.is_complete:
        preview = None
        projected_afc_rounds = projected_nfc_rounds = None
        if season.current_week >= STANDINGS_BASED_FEATURES_MIN_WEEK:
            afc_seeds = seed_conference(season, "AFC")
            nfc_seeds = seed_conference(season, "NFC")
            in_the_hunt, division_standings = _conference_hunt_and_standings(season, afc_seeds, nfc_seeds)
            preview = {"in_the_hunt": in_the_hunt, "division_standings": division_standings}
            projected_bracket = build_wild_card_round(season)
            projected_afc_rounds = _rounds_by_conference(projected_bracket, "AFC")
            projected_nfc_rounds = _rounds_by_conference(projected_bracket, "NFC")
        return templates.TemplateResponse(request, "playoffs.html", {
            "season": season, "bracket": None, "round_labels": ROUND_LABELS, "view": view,
            "preview": preview,
            "projected_afc_rounds": projected_afc_rounds, "projected_nfc_rounds": projected_nfc_rounds,
        })
    if season.playoffs is None:
        season_state.simulate_playoff_round()  # builds the Wild Card round on first visit
        season = season_state.get_season()
    bracket = season.playoffs
    in_the_hunt, division_standings = _conference_hunt_and_standings(season, bracket.afc_seeds, bracket.nfc_seeds)
    afc_rounds = _rounds_by_conference(bracket, "AFC")
    nfc_rounds = _rounds_by_conference(bracket, "NFC")
    sb_matchups = _rounds_by_conference(bracket, None).get("SB", [])
    sb_matchup = sb_matchups[0] if sb_matchups else None

    ctx = {
        "season": season, "bracket": bracket, "round_labels": ROUND_LABELS,
        "view": view, "in_the_hunt": in_the_hunt, "division_standings": division_standings,
        "afc_rounds": afc_rounds, "nfc_rounds": nfc_rounds, "sb_matchup": sb_matchup,
        "teams_by_abbr": TEAMS_BY_ABBR,
    }

    if view == "full":
        # M12 correction (real source: FullPlayoffTree.tsx): the Champion
        # columns flanking the Super Bowl card.
        ctx["afc_champion"] = _conference_champion(bracket, "AFC")
        ctx["nfc_champion"] = _conference_champion(bracket, "NFC")

    if view in ("afc", "nfc"):
        # M12 correction (real source: ConferenceBracket.tsx): the 4th
        # "Champion" column this view never had.
        ctx["conf_champion"] = _conference_champion(bracket, "AFC" if view == "afc" else "NFC")

    if view == "superbowl":
        # M12 correction (real source: SuperBowlView.tsx): compact side
        # Wild Card previews (real, just the first 2 of each conference's
        # 3 WC games), a real Scouting Panel per SB team (reusing
        # build_scouting_report() and the Dashboard's own .dash-tab
        # widget, not a second implementation), and -- once the game is
        # actually simulated -- a real final-score summary linking to the
        # full box score/play-by-play (playoffs_game_view below) rather
        # than a second, duplicate inline copy of that same page. MVP is
        # deliberately NOT included: no per-game "player of the game"
        # stat exists anywhere in this engine (awards.py's MVP is a real,
        # but SEASON-long, computation), and Figma's own MVP block is
        # itself hardcoded demo data ("Tom Brady... Kansas City Chiefs"),
        # not something a real API would ever return either -- faking a
        # number here would be strictly worse than the source.
        ctx["afc_wc_preview"] = afc_rounds.get("WC", [])[:2]
        ctx["nfc_wc_preview"] = nfc_rounds.get("WC", [])[:2]
        if sb_matchup is not None:
            ctx["sb_scouting"] = {
                sb_matchup.home_abbr: build_scouting_report(season, sb_matchup.home_abbr),
                sb_matchup.away_abbr: build_scouting_report(season, sb_matchup.away_abbr),
            }

    return templates.TemplateResponse(request, "playoffs.html", ctx)


@app.get("/playoffs/game/{round_name}/{home_abbr}/{away_abbr}", response_class=HTMLResponse)
def playoffs_game_view(request: Request, round_name: str, home_abbr: str, away_abbr: str):
    """Same result.html play-by-play + box score view as a regular-season
    game (app/main.py's season_game_view) -- playoff games are simulated
    with the same engine and retain the same full GameResult."""
    season = season_state.get_season()
    if season.playoffs is None:
        raise HTTPException(404, "No playoff bracket yet")

    matchup = next(
        (m for round_ in season.playoffs.rounds for m in round_
         if m.round_name == round_name and m.home_abbr == home_abbr and m.away_abbr == away_abbr),
        None,
    )
    if matchup is None or matchup.result is None:
        raise HTTPException(404, "That playoff game hasn't been played yet")

    home_info = TEAMS_BY_ABBR[home_abbr]
    away_info = TEAMS_BY_ABBR[away_abbr]
    home = TeamSim(name=home_info.location, abbr=home_info.abbr, ratings=None)
    away = TeamSim(name=away_info.location, abbr=away_info.abbr, ratings=None)

    result = matchup.result
    home_box = build_box_score(result.plays, home_info.abbr)
    away_box = build_box_score(result.plays, away_info.abbr)
    home_defense = build_defensive_box_score(result.plays, home_info.abbr)
    away_defense = build_defensive_box_score(result.plays, away_info.abbr)
    game_seed = stable_seed(season.league_seed, "playoffs", round_name, home_abbr, away_abbr)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "home": home,
            "away": away,
            "result": result,
            "quarters": quarter_scores(result.events),
            "league_seed": season.league_seed,
            "game_seed": game_seed,
            "home_box": home_box,
            "away_box": away_box,
            "home_defense": home_defense,
            "away_defense": away_defense,
            "back_url": "/playoffs",
            "back_label": "Back to playoffs",
        },
    )


@app.get("/team-select", response_class=HTMLResponse)
def team_select_view(request: Request):
    """GDD Sec 10.1: the one-time, conference/division-grouped team grid
    shown at franchise creation. No records or power rankings shown --
    a brand-new league has no history yet (see Sec 10.1's note that this
    step deliberately does exactly one job)."""
    season = season_state.get_season()
    current = season.user_team_abbr
    current_conf = TEAMS_BY_ABBR[current].conference if current else "AFC"
    return templates.TemplateResponse(
        request,
        "team_select.html",
        {"grouped": _grouped_teams(), "current": current, "current_conf": current_conf},
    )


@app.post("/team-select")
def team_select_submit(team_abbr: str = Form(...)):
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")
    season_state.set_user_team(team_abbr)
    return RedirectResponse(url="/dashboard", status_code=303)


def _safe_internal_redirect(path: str | None, default: str) -> str:
    """Only ever redirects back to a path on THIS app -- rejects
    anything that could be an open redirect (an absolute URL, or a
    protocol-relative "//host/..." path browsers still treat as
    absolute) rather than trusting the submitted value outright."""
    if not path or not path.startswith("/") or path.startswith("//"):
        return default
    return path


@app.post("/season/simulate-week")
def season_simulate_week(redirect_to: str | None = Form(None)):
    """GDD Sec 4's game loop (Regular Season -> Playoffs -> Championship)
    is one continuous cycle from the player's perspective -- a single
    "Sim Week" control, matching the Figma header's one sim button
    (Sec 10.3), now persistent across every page (base.html's header,
    via _header_context()) rather than living only on /season. Once the
    regular season is done, the same button just starts simulating
    playoff rounds instead. `redirect_to` (the page the button was
    clicked from, a hidden field in the header's own form) sends the
    player back to where they were rather than always yanking them to
    /season/-/playoffs -- the whole point of a persistent control is
    that using it doesn't lose your place."""
    season = season_state.get_season()
    if season.is_complete:
        season_state.simulate_playoff_round()
        return RedirectResponse(url=_safe_internal_redirect(redirect_to, "/playoffs"), status_code=303)
    season_state.simulate_current_week()
    return RedirectResponse(url=_safe_internal_redirect(redirect_to, "/season"), status_code=303)


@app.post("/season/reset")
def season_reset():
    season_state.reset_season()
    return RedirectResponse(url="/season", status_code=303)


@app.post("/season/new-season")
def season_new_season():
    """GDD Sec 4's Offseason step + Sec 7.6 (Player Progression &
    Regression): moves the franchise into its next season once the
    playoffs are fully decided. 404s rather than silently no-op'ing if
    called too early."""
    try:
        season_state.start_new_season()
    except ValueError as e:
        raise HTTPException(404, str(e))
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/simulate", response_class=HTMLResponse)
def simulate(request: Request, home_abbr: str = Form(...), away_abbr: str = Form(...)):
    league_seed = get_league_seed()

    home_info = TEAMS_BY_ABBR[home_abbr]
    away_info = TEAMS_BY_ABBR[away_abbr]

    home = TeamSim(name=home_info.location, abbr=home_info.abbr, ratings=ratings_for(home_info, league_seed))
    away = TeamSim(name=away_info.location, abbr=away_info.abbr, ratings=ratings_for(away_info, league_seed))

    # Derived per-game RNG, distinct from the placeholder-rating RNG above,
    # matching the "derived, not global" spirit of GDD Part 1 Sec 1.3.
    game_seed = stable_seed(league_seed, home_abbr, away_abbr, "demo_game")
    rng = RNG.with_seed(game_seed)

    result = simulate_game(rng, home, away)
    home_box = build_box_score(result.plays, home_info.abbr)
    away_box = build_box_score(result.plays, away_info.abbr)
    home_defense = build_defensive_box_score(result.plays, home_info.abbr)
    away_defense = build_defensive_box_score(result.plays, away_info.abbr)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "home": home,
            "away": away,
            "result": result,
            "quarters": quarter_scores(result.events),
            "league_seed": league_seed,
            "game_seed": game_seed,
            "home_box": home_box,
            "away_box": away_box,
            "home_defense": home_defense,
            "away_defense": away_defense,
        },
    )
