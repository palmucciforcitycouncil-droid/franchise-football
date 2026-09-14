"""
End-of-season honors pipeline (Brian's ask, 2026-09-14): the moments a
season's honors get DECIDED and frozen into app/services/honors_store.py,
kept out of season_state.py so that file only gains one-line hooks.

- finalize_regular_season(): right after the last regular-season week.
  Final MVP/OPOY/DPOY/OROY/DROY/ROY/COTY (top 10 each) and the AFC/NFC
  Pro Bowl rosters; credits each winner's and every Pro Bowler's
  permanent award history, and the COTY winner's Coach record.
- record_playoff_round(): after each CONF/SB round. Conference titles and
  Super Bowl titles (with years) for every coach on the winning staff;
  the Super Bowl result + MVP; "Super Bowl MVP" and "Super Bowl Champion"
  for players.
- retire_players(): during begin_offseason(), after progression has aged
  everyone (app/engine/retirement.py for the formula).
- record_offseason_headlines(): the offseason-start headlines.

Every function is idempotent -- a replayed call (a re-saved round, a
double-clicked Sim Week, begin_offseason() running the pre-offseason
safety calls on a season that already finalized) changes nothing twice.
"""
from __future__ import annotations
from dataclasses import asdict

from sqlalchemy.exc import OperationalError
from sqlmodel import select

from app.config import season_year
from app.core.db import get_session
from app.data.teams import TEAMS_BY_ABBR
from app.engine import awards
from app.engine.schedule import N_WEEKS
from app.models.player import Player
from app.services import honors_store

AWARD_NAMES = {
    "mvp": "MVP",
    "opoy": "Offensive Player of the Year",
    "dpoy": "Defensive Player of the Year",
    "oroy": "Offensive Rookie of the Year",
    "droy": "Defensive Rookie of the Year",
}

# headlines_history keys everything by an integer week; the playoff rounds
# already occupy N_WEEKS+1..+4 (season_state.simulate_playoff_round()'s
# pseudo_week), so the offseason-start headlines sit right after them.
OFFSEASON_HEADLINES_WEEK = N_WEEKS + 5


def _players_by_key() -> dict[tuple[str, str], tuple[str, str]]:
    """(team_abbr, name) -> (player_id, real position) -- the awards
    candidates only carry a name and a stat-pool label ("DEF", "WR/TE")."""
    with get_session() as s:
        return {(p.team_abbr, p.full_name): (p.player_id, p.position.value)
                for p in s.exec(select(Player).where(Player.team_abbr != None))}  # noqa: E711


def finalize_regular_season(season) -> bool:
    """Returns True if this call actually finalized (False: already done,
    or the regular season isn't over)."""
    if not season.is_complete or honors_store.get_final_awards(season.season_number) is not None:
        return False

    players = _players_by_key()
    lists = awards.season_award_lists(season, awards.AWARDS_RACE_TOP_N)
    final: dict[str, list[dict]] = {}
    for key, cands in lists.items():
        rows = []
        for c in cands:
            row = asdict(c)
            if key != "coty":
                row["player_id"], row["player_position"] = players.get((c.team_abbr, c.name), ("", ""))
            rows.append(row)
        final[key] = rows

    rosters = awards.pro_bowl_rosters(season)
    pro_bowl = {conf: {side: [asdict(p) for p in side_players] for side, side_players in sides.items()}
                for conf, sides in rosters.items()}

    honors_store.save_final_awards(season.season_number, final)
    honors_store.save_pro_bowl(season.season_number, pro_bowl)

    sn = season.season_number
    player_entries = [
        (final[key][0]["player_id"], sn, label) for key, label in AWARD_NAMES.items() if final.get(key)
    ]
    for sides in pro_bowl.values():
        for side_players in sides.values():
            player_entries.extend((p["player_id"], sn, "Pro Bowl") for p in side_players)
    honors_store.add_player_awards(player_entries)

    if final.get("coty"):
        added = honors_store.add_coach_awards([(final["coty"][0]["coach_id"], sn, "Coach of the Year")])
        if added:
            _bump_coach_counter(final["coty"][0]["coach_id"], "coach_awards")
    return True


def _bump_coach_counter(coach_id: str, field: str) -> None:
    """Coach.coach_awards existed (GDD Sec 7.9.1) but nothing ever credited
    it; only called when honors_store says the award is genuinely new, so
    the counter and the dated history can't drift apart."""
    from app.models.coach import Coach
    from app.services import coach_store
    try:
        with get_session() as s:
            coach = s.get(Coach, coach_id)
            if coach is None:
                return
            setattr(coach, field, getattr(coach, field) + 1)
            s.add(coach)
            s.commit()
    except OperationalError:
        return
    coach_store.clear_cache()


def _staff_ids(team_abbr: str) -> list[str]:
    from app.models.coach import Coach
    try:
        with get_session() as s:
            return [c.coach_id for c in s.exec(
                select(Coach).where(Coach.team_abbr == team_abbr, Coach.retired == False)  # noqa: E712
            )]
    except OperationalError:
        return []


def record_playoff_round(season, round_name: str) -> None:
    # Backfill for a save whose last regular-season week was simulated
    # before season honors existed -- a no-op otherwise.
    finalize_regular_season(season)
    if season.playoffs is None or round_name not in ("CONF", "SB"):
        return
    sn = season.season_number
    matchups = [m for r in season.playoffs.rounds for m in r if m.round_name == round_name and m.is_complete]
    if not matchups:
        return

    if round_name == "CONF":
        entries = []
        for m in matchups:
            conference = TEAMS_BY_ABBR[m.winner_abbr].conference
            entries.extend((cid, sn, f"{conference} Champion") for cid in _staff_ids(m.winner_abbr))
        honors_store.add_coach_awards(entries)
        return

    if honors_store.get_super_bowl(sn) is not None:
        return
    sb = matchups[0]
    winner = sb.winner_abbr
    loser = sb.home_abbr if winner == sb.away_abbr else sb.away_abbr
    winner_score = sb.result.home_score if winner == sb.home_abbr else sb.result.away_score
    loser_score = sb.result.away_score if winner == sb.home_abbr else sb.result.home_score
    conf_winners = {
        m.conference: m.winner_abbr
        for r in season.playoffs.rounds for m in r if m.round_name == "CONF" and m.is_complete
    }
    mvp = awards.super_bowl_mvp(sb.result.plays, winner)
    year = season_year(sn)
    summary = {
        "season_number": sn, "year": year, "numeral": awards.super_bowl_numeral(year),
        "home_abbr": sb.home_abbr, "away_abbr": sb.away_abbr,
        "home_score": sb.result.home_score, "away_score": sb.result.away_score,
        "winner_abbr": winner, "loser_abbr": loser, "winner_score": winner_score, "loser_score": loser_score,
        "afc_champion_abbr": conf_winners.get("AFC"), "nfc_champion_abbr": conf_winners.get("NFC"),
        "mvp": mvp,
    }
    honors_store.save_super_bowl(sn, summary)

    with get_session() as s:
        roster_ids = [p.player_id for p in s.exec(select(Player).where(Player.team_abbr == winner))]
    player_entries = [(pid, sn, "Super Bowl Champion") for pid in roster_ids]
    if mvp and mvp.get("player_id"):
        player_entries.append((mvp["player_id"], sn, "Super Bowl MVP"))
    honors_store.add_player_awards(player_entries)
    honors_store.add_coach_awards([(cid, sn, "Super Bowl Champion") for cid in _staff_ids(winner)])


def _honors_summary(player_id: str) -> str:
    return ", ".join(
        f"{g['count']}x {g['award']}" if g["count"] > 1 else g["award"]
        for g in honors_store.group_awards(honors_store.player_awards(player_id))
    )


def _protect_minimum_rosters(on_team: list, free_agents: list, rolled_team: list, rolled_fa: list) -> list:
    """Which rolled retirements actually happen. The depth chart indexes a
    starter at every position unconditionally, and fill_roster_gaps() can
    only backfill a hole from players who still exist -- so a retirement
    that would leave a team below free_agency.MIN_ROSTER_COUNTS with no
    free agent left to sign is called off (the player gives it one more
    year), and an unsigned free agent's retirement is called off first
    whenever the pool at his position is already too thin to cover the
    league's existing holes."""
    from collections import Counter
    from app.engine.free_agency import MIN_ROSTER_COUNTS

    team_counts = Counter((p.team_abbr, p.position) for p in on_team)
    demand: Counter = Counter()
    for abbr in TEAMS_BY_ABBR:
        for position, minimum in MIN_ROSTER_COUNTS.items():
            demand[position] += max(0, minimum - team_counts[(abbr, position)])
    rolled_fa_ids = {p.player_id for p in rolled_fa}
    supply = Counter(p.position for p in free_agents if p.player_id not in rolled_fa_ids)

    fa_leaving = list(rolled_fa)

    def unretire_fa(position) -> bool:
        match = next((p for p in fa_leaving if p.position == position), None)
        if match is None:
            return False
        fa_leaving.remove(match)
        supply[position] += 1
        return True

    for position in list(demand):
        while supply[position] < demand[position] and unretire_fa(position):
            pass

    team_leaving = []
    for p in rolled_team:
        key = (p.team_abbr, p.position)
        if team_counts[key] - 1 >= MIN_ROSTER_COUNTS.get(p.position, 0):
            team_counts[key] -= 1
            team_leaving.append(p)
        elif supply[p.position] > demand[p.position] or unretire_fa(p.position):
            team_counts[key] -= 1
            demand[p.position] += 1
            team_leaving.append(p)
    return team_leaving + fa_leaving


def retire_players(season, session, rostered_players: list) -> list[dict]:
    """Rolls app/engine/retirement.py's check for every Player row (the
    caller's rostered players plus every free agent) and removes the
    retirees. Runs inside season_state.finish_offseason()'s own session:
    `rostered_players` is that function's live list, pruned IN PLACE, so
    its fill_roster_gaps() pass right after sees the real post-retirement
    roster; the caller commits.

    Hard-deletes the row -- the same way an expired undrafted rookie
    already leaves the league (undrafted_pool.decrement_and_expire()) --
    since there is no "retired" status any roster/free-agency query would
    know to skip. Nothing is lost: career stats and League History are
    keyed by (team, name) in the archived history, never by a live Player
    row, and the retiree's line is frozen into honors_store for the
    season summary. The team shown is the player's LAST team (a player
    just released at contract expiry shows as FA)."""
    from app.engine.retirement import rolls_retirement
    from app.services import undrafted_pool

    existing = honors_store.get_retired_players(season.season_number)
    if existing is not None:
        return existing

    free_agents = list(session.exec(select(Player).where(Player.team_abbr == None)).all())  # noqa: E711
    on_team = [p for p in rostered_players if p.team_abbr is not None]
    # Released at contract expiry moments ago (still in the caller's
    # rostered list) vs. unsigned all season -- only the latter gets the
    # "nobody's calling" free-agent bump.
    just_released = {p.player_id for p in rostered_players if p.team_abbr is None}
    rolled_fa = sorted(
        (p for p in free_agents
         if rolls_retirement(p, season.league_seed, season.season_number, p.player_id not in just_released)),
        key=lambda p: (-p.overall_rating, p.player_id))
    rolled_team = sorted(
        (p for p in on_team if rolls_retirement(p, season.league_seed, season.season_number, False)),
        key=lambda p: p.player_id)
    leaving = _protect_minimum_rosters(on_team, free_agents, rolled_team, rolled_fa)

    retirees: list[dict] = []
    retired_ids: set[str] = set()
    for p in leaving:
        retirees.append({
            "player_id": p.player_id, "name": p.full_name, "position": p.position.value,
            "team_abbr": p.team_abbr, "age": p.age, "overall_rating": p.overall_rating,
            "years_pro": p.years_pro, "honors": _honors_summary(p.player_id),
        })
        retired_ids.add(p.player_id)
        session.delete(p)
    rostered_players[:] = [p for p in rostered_players if p.player_id not in retired_ids]
    session.flush()
    for r in retirees:
        if r["team_abbr"] is None:  # only an unsigned player can still be in the undrafted pool
            undrafted_pool.remove(r["player_id"])

    retirees.sort(key=lambda r: (-r["overall_rating"], r["name"]))
    honors_store.save_retired_players(season.season_number, retirees)
    return retirees


def record_offseason_headlines(season) -> list[str]:
    from app.engine.offseason_headlines import season_end_headlines
    from app.services import headlines_history

    lines = season_end_headlines(
        season_year(season.season_number),
        honors_store.get_super_bowl(season.season_number),
        honors_store.get_final_awards(season.season_number),
    )
    headlines_history.record_week_headlines(season.season_number, OFFSEASON_HEADLINES_WEEK, lines)
    return lines


def offseason_headlines(season_number: int) -> list[str] | None:
    from app.services import headlines_history
    return headlines_history.get_week_headlines(season_number, OFFSEASON_HEADLINES_WEEK)
