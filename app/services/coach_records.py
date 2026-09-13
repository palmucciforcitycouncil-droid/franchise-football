"""
Coach season & career accounting (GDD Part 1 Sec 7.9).

Two write paths, both idempotent by construction:

1. `credit_championship_round()` -- called from
   season_state.simulate_playoff_round() right after a CONF or SB round
   finishes. Credits every coach on the winning staff **by the role
   they held** (Sec 7.9.2), writing a CoachSeasonStats row and bumping
   the matching career counter. Sec 7.9.2's own Idempotency clause
   ("re-finalizing the same game must not double-count") is enforced by
   reading the existing CoachSeasonStats row first and only
   incrementing the career counter when the row's value actually
   changes -- so a replayed or re-saved round is a no-op, not a
   duplicate ring.

2. `record_season_results()` -- called from
   season_state.start_new_season() at rollover. Writes each staff's
   real regular-season W/L and playoff appearance into their
   CoachSeasonStats row, rolls those into career_wins/career_losses/
   seasons_coached, and recomputes job_security_score (Sec 8.2.3).

Sec 7.9.1's StaffAssignment table (a dated role-history log, so credit
can be resolved "at kickoff" for a mid-season role change) is
deliberately NOT built: nothing in this engine can change a coach's
role mid-season yet -- there is no hiring/firing/promotion flow -- so
the current Coach.role IS the role held at kickoff, and a second table
tracking a history that cannot vary would be dead weight. Sec 7.9.3's
"Interim HC" and "mid-season role change" edge cases are unreachable
for the same reason. When a real lifecycle system lands (GDD Sec 8.2.3
/ ROADMAP R3's hire-fire flow), that's the chunk that needs
StaffAssignment, and this module's credit pass is where it would be
read.
"""
from __future__ import annotations
from dataclasses import dataclass

from sqlalchemy.exc import OperationalError
from sqlmodel import select

from app.core.db import get_session
from app.data.teams import TEAMS_BY_ABBR
from app.models.coach import (
    Coach, CoachRole, CoachSeasonStats,
    CONFERENCE_TITLE_NONE, SUPER_BOWL_NONE, SUPER_BOWL_LOSS, SUPER_BOWL_WIN,
)
from app.services import coach_store

# career counter prefixes, by role (GDD Sec 7.9.1's rollup field names).
_ROLE_PREFIX = {
    CoachRole.HC: "hc", CoachRole.OC: "oc", CoachRole.DC: "dc",
    CoachRole.ST: "st", CoachRole.AC: "ac",
}


def _season_row(session, coach_id: str, season: int, role: CoachRole) -> CoachSeasonStats | None:
    return session.get(CoachSeasonStats, (coach_id, season, role))


def _get_or_create(session, coach: Coach, season_number: int) -> CoachSeasonStats:
    role = CoachRole(coach.role)
    row = _season_row(session, coach.coach_id, season_number, role)
    if row is None:
        row = CoachSeasonStats(
            coach_id=coach.coach_id, season=season_number, role=role,
            team_abbr=coach.team_abbr or "",
        )
        session.add(row)
    return row


def credit_championship_round(season, round_name: str) -> int:
    """Credits a finished CONF or SB round to both teams' staffs.
    Returns the number of coach rows actually changed (0 on a replay,
    which is how the idempotency requirement shows up in practice)."""
    if round_name not in ("CONF", "SB") or season.playoffs is None:
        return 0

    matchups = [m for r in season.playoffs.rounds for m in r
                if m.round_name == round_name and m.is_complete]
    if not matchups:
        return 0

    changed = 0
    try:
        with get_session() as session:
            for matchup in matchups:
                winner = matchup.winner_abbr
                loser = matchup.home_abbr if winner == matchup.away_abbr else matchup.away_abbr
                if round_name == "CONF":
                    conference = TEAMS_BY_ABBR[winner].conference  # "AFC" | "NFC"
                    changed += _apply_conference_title(session, winner, season.season_number, conference)
                else:
                    changed += _apply_super_bowl(session, winner, season.season_number, SUPER_BOWL_WIN)
                    changed += _apply_super_bowl(session, loser, season.season_number, SUPER_BOWL_LOSS)
            session.commit()
    except OperationalError:
        return 0  # database has no coach tables -- nothing to credit

    if changed:
        coach_store.clear_cache()
    return changed


def _staff_rows(session, team_abbr: str) -> list[Coach]:
    return list(session.exec(
        select(Coach).where(Coach.team_abbr == team_abbr, Coach.retired == False)  # noqa: E712
    ).all())


def _apply_conference_title(session, team_abbr: str, season_number: int, conference: str) -> int:
    changed = 0
    for coach in _staff_rows(session, team_abbr):
        row = _get_or_create(session, coach, season_number)
        row.made_playoffs = True
        if row.conference_title == conference:
            continue  # already credited -- Sec 7.9.2 idempotency
        row.conference_title = conference
        field = f"{_ROLE_PREFIX[CoachRole(coach.role)]}_{conference.lower()}_championships"
        setattr(coach, field, getattr(coach, field) + 1)
        session.add(coach)
        session.add(row)
        changed += 1
    return changed


def _apply_super_bowl(session, team_abbr: str, season_number: int, result: str) -> int:
    changed = 0
    for coach in _staff_rows(session, team_abbr):
        row = _get_or_create(session, coach, season_number)
        row.made_playoffs = True
        if row.super_bowl_result == result:
            continue  # already credited
        row.super_bowl_result = result
        if result == SUPER_BOWL_WIN:
            field = f"{_ROLE_PREFIX[CoachRole(coach.role)]}_super_bowl_wins"
            setattr(coach, field, getattr(coach, field) + 1)
            coach.sb_titles += 1
        session.add(coach)
        session.add(row)
        changed += 1
    return changed


def job_security_score(win_pct: float, playoff_result_score: float, owner_patience: float,
                        blowout_loss_pct: float = 0.0, preseason_rank_delta: float = 0.0) -> float:
    """GDD Sec 8.2.3's JSS, on a 0-100 scale:

        JSS = 0.55*WinPct + 0.20*PreseasonPowerRankDelta + 0.15*PlayoffResultScore
              + 0.10*OwnerPatience - 0.10*BlowoutLosses%

    Every term is real except BlowoutLosses% and PreseasonPowerRankDelta,
    which default to 0: this engine records a final score per game (so a
    blowout IS computable) but has no preseason Power Rating snapshot to
    diff a rank against -- power_rank_history.py only starts recording
    once week 1 has been simulated. Callers that can compute those terms
    pass them; the default is a disclosed omission, not a fabricated
    value. owner_patience has no modeled source either and defaults to a
    neutral 50 at the call site (Sec 7.7.2.4 defines it as a team-level
    factor computed each offseason, which nothing computes yet)."""
    return max(0.0, min(100.0,
        0.55 * (win_pct * 100)
        + 0.20 * preseason_rank_delta
        + 0.15 * playoff_result_score
        + 0.10 * owner_patience
        - 0.10 * blowout_loss_pct
    ))


# How far a team got, as the 0-100 "PlayoffResultScore" term above.
PLAYOFF_RESULT_SCORES = {
    None: 0.0, "MISSED": 0.0, "WC": 40.0, "DIV": 60.0, "CONF": 80.0, "SB_LOSS": 90.0, "SB_WIN": 100.0,
}
NEUTRAL_OWNER_PATIENCE = 50.0


@dataclass
class SeasonCredit:
    """What one season's rollover wrote, for logging/testing."""
    coaches_updated: int = 0
    seasons_recorded: int = 0


def _playoff_outcome_for(season, team_abbr: str) -> str:
    """How far this team got, as a PLAYOFF_RESULT_SCORES key."""
    bracket = season.playoffs
    if bracket is None:
        return "MISSED"
    played = [m for r in bracket.rounds for m in r
              if team_abbr in (m.home_abbr, m.away_abbr)]
    if not played:
        return "MISSED"
    best = "MISSED"
    order = ["MISSED", "WC", "DIV", "CONF", "SB_LOSS", "SB_WIN"]
    for m in played:
        if not m.is_complete:
            continue
        won = m.winner_abbr == team_abbr
        if m.round_name == "SB":
            reached = "SB_WIN" if won else "SB_LOSS"
        else:
            # Reaching a round at all means you survived the previous
            # one; the round you LOST in is how far you got.
            reached = {"WC": "WC", "DIV": "DIV", "CONF": "CONF"}[m.round_name]
            if won:
                reached = {"WC": "DIV", "DIV": "CONF", "CONF": "SB_LOSS"}[m.round_name]
        if order.index(reached) > order.index(best):
            best = reached
    return best


def record_season_results(season) -> SeasonCredit:
    """Rolls one completed season into every employed coach's career
    record (GDD Sec 7.9.1's career rollups + Sec 7.7.2.4's lifecycle
    counters). Idempotent: a CoachSeasonStats row that already carries
    this season's W/L is not counted into the career totals twice.

    `job_security_score` is R3d's Enhanced JSS (app/engine/coach_hiring.
    compute_jss(), per role -- HC/OC/DC/ST each get their own real
    formula, AC a simplified real-fields proxy), computed per coach
    rather than the old flat per-team job_security_score() above (kept
    only for test_coaching.py's own literal-math test, otherwise dead).
    team_ranks is computed once for the whole league, not once per
    coach -- the numbers are identical for every coach on the same
    staff, and O(32) coaches x a fresh 32-team rank scan each would be
    real, avoidable waste (same reasoning coach_progression.py's own
    compute_team_ranks() docstring already gives)."""
    from app.engine import coach_hiring, coach_progression

    credit = SeasonCredit()
    team_ranks = coach_progression.compute_team_ranks(season)
    try:
        with get_session() as session:
            for team_abbr, record in season.records.items():
                outcome = _playoff_outcome_for(season, team_abbr)
                for coach in _staff_rows(session, team_abbr):
                    row = _get_or_create(session, coach, season.season_number)
                    already_recorded = (row.wins, row.losses) == (record.wins, record.losses) and row.wins + row.losses > 0
                    row.team_abbr = team_abbr
                    row.wins, row.losses = record.wins, record.losses
                    row.made_playoffs = outcome != "MISSED"
                    if not already_recorded:
                        coach.career_wins += record.wins
                        coach.career_losses += record.losses
                        coach.seasons_coached += 1
                        if outcome in ("DIV", "CONF", "SB_LOSS", "SB_WIN"):
                            # A playoff "win" is a round survived: the
                            # bracket itself is the source, not a
                            # separate counter that could drift from it.
                            coach.playoff_wins += {"DIV": 1, "CONF": 2, "SB_LOSS": 3, "SB_WIN": 4}[outcome]
                        credit.seasons_recorded += 1
                    jss, _ = coach_hiring.compute_jss(season, team_abbr, coach, team_ranks.get(team_abbr))
                    coach.job_security_score = jss
                    session.add(coach)
                    session.add(row)
                    credit.coaches_updated += 1
            session.commit()
    except OperationalError:
        return credit  # no coach tables in this database

    coach_store.clear_cache()
    return credit


def season_history(coach_id: str) -> list[CoachSeasonStats]:
    """GDD Sec 7.9.4's Coach Profile -> Season History: one row per
    season per role, newest first."""
    try:
        with get_session() as session:
            rows = list(session.exec(
                select(CoachSeasonStats).where(CoachSeasonStats.coach_id == coach_id)
            ).all())
    except OperationalError:
        return []
    return sorted(rows, key=lambda r: -r.season)
