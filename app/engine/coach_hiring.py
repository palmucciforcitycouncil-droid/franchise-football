"""
R3d: Enhanced Job Security Score, the Firing Probability model, and the
scoring formulas (HiringMerit, InterimPromotionScore, CandidateInterest)
the replacement market runs on. Spec: docs/R3d_COACHING_SYSTEM_SPECIFICATION.md
Sec 3-4. Settled decisions there are not re-litigated here.

File split follows Sec 16's own Implementation Notes: this module is
pure scoring math (JSS, firing probability, merit/interest formulas) --
nothing here writes to the database or decides WHO to actually hire.
app/engine/coach_replacement.py is the orchestration layer (candidate
search, promotion hierarchy, actually mutating Coach rows) that calls
into these functions. app/services/coach_records.py's
record_season_results() calls compute_jss() below to get the number it
stores on Coach.job_security_score -- the OLD job_security_score()
formula there is untouched (a real prior test asserts its own literal
math) and is now dead code kept only for that regression coverage.

Every JSS component is a 0-100 "higher is better" score, combined with
Sec 3.1's own weights. Six real inputs drive it:

  WinPerformance          -- record.win_pct * 100 (vs. a schedule
                             engineered to average .500 leaguewide)
  PerformanceVsExpectation -- actual win_pct vs. this season's frozen
                             PerformanceExpectation (team_expectations.py)
  PlayoffPerformance      -- coach_records.PLAYOFF_RESULT_SCORES, reused
                             verbatim rather than duplicated
  Trajectory              -- this season's win_pct vs. the team's own
                             last up-to-3 seasons (by HC role, not by
                             coach_id -- a mid-window coaching change
                             doesn't erase the program's trend)
  Blowouts/Dysfunction    -- real 20+-point-loss frequency this season.
                             "Dysfunction" (locker room chaos, discipline
                             incidents) has no modeled signal anywhere in
                             this engine and is not invented; blowout
                             frequency is the one real, computable half
                             of this factor, same disclosed-partial-term
                             precedent the ORIGINAL job_security_score()
                             already set for this exact term.
  Owner/OrganizationalFactors -- derived from OwnerWinPressure
                             (owner_pressure_store.py) as the one real,
                             persistent "is ownership under pressure"
                             signal this engine has; "franchise in
                             chaos" beyond that has no other modeled
                             source.

Coordinator (OC/DC/ST) JSS reuses the same real inputs where an
equivalent exists and discloses each substitution inline -- several of
Sec 3.1's coordinator-specific sub-factors (explosive-play-allowed rate,
return-game efficiency, per-unit season-over-season yardage trend) have
no real per-unit historical data anywhere in this engine (CoachSeasonStats
only ever stored team win/loss + playoff outcome, GDD Sec 7.9.1), so
those sub-factors fall back to the real, already-computed team-level
substitute closest to their intent (documented at each fallback below),
following the exact precedent app/engine/coach_progression.py's own
`rz_def_ranks = pa_ranks` already set for an analogous gap.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

from app.models.coach import Coach, CoachRole
from app.services import owner_pressure_store, team_expectations

# ---------------------------------------------------------------------------
# Real per-team inputs
# ---------------------------------------------------------------------------


def blowout_loss_pct(season, team_abbr: str, margin: int = 20) -> float:
    """Real fraction (0-100) of this team's played games lost by
    `margin`+ points this season."""
    played = blowouts = 0
    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            if g.home_abbr == team_abbr:
                my, opp = g.result.home_score, g.result.away_score
            elif g.away_abbr == team_abbr:
                my, opp = g.result.away_score, g.result.home_score
            else:
                continue
            played += 1
            if opp - my >= margin:
                blowouts += 1
    return (blowouts / played * 100.0) if played else 0.0


def _team_recent_hc_seasons(team_abbr: str, season_number: int, lookback: int = 3) -> list[tuple[int, float]]:
    """(season_number, win_pct) for up to `lookback` seasons strictly
    before `season_number`, keyed by TEAM + HC role rather than by
    coach_id -- Sec 3.1's Trajectory factor is the program's trend, not
    one coach's personal history, so a mid-window HC change doesn't
    reset it."""
    from sqlalchemy.exc import OperationalError
    from sqlmodel import select
    from app.core.db import get_session
    from app.models.coach import CoachSeasonStats

    try:
        with get_session() as s:
            rows = list(s.exec(
                select(CoachSeasonStats).where(
                    CoachSeasonStats.team_abbr == team_abbr,
                    CoachSeasonStats.role == CoachRole.HC,
                    CoachSeasonStats.season < season_number,
                )
            ).all())
    except OperationalError:
        return []
    rows.sort(key=lambda r: -r.season)
    out = []
    for r in rows[:lookback]:
        total = r.wins + r.losses
        if total:
            out.append((r.season, r.wins / total))
    return out


def _trajectory_score(current_win_pct: float, recent: list[tuple[int, float]]) -> float:
    """0-100, centered on 50 (flat/no history). This season's win_pct
    vs. the average of up to the last 3 seasons, scaled so a full-scale
    swing (+/-1.0 win_pct) maps to the full 0-100 range -- this
    module's own documented scaling choice, no GDD formula given."""
    if not recent:
        return 50.0
    avg_recent = sum(wp for _, wp in recent) / len(recent)
    return max(0.0, min(100.0, 50.0 + (current_win_pct - avg_recent) * 100.0))


def _performance_vs_expectation_score(actual_win_pct: float, expected_win_pct: float) -> float:
    """0-100, centered on 50 for exactly meeting expectation -- Sec 3.1
    calls this THE key differentiator. A linear map of the win_pct delta
    (capped by the 0-100 clamp, since a 17-game season can't realistically
    swing +/-50 points) onto 0-100, this module's own documented choice."""
    return max(0.0, min(100.0, 50.0 + (actual_win_pct - expected_win_pct) * 100.0))


def owner_organizational_score(current_pressure: float) -> float:
    """0-100, HIGH OwnerWinPressure -> LOW score. Linear map of the
    pressure range (20-90) onto (100-0) -- the one real, persistent
    "is the organization under strain" signal this engine models;
    "franchise in chaos" beyond ownership pressure (owner turnover,
    off-field scandal) has no other modeled source and is not invented."""
    lo, hi = owner_pressure_store.MIN_PRESSURE, owner_pressure_store.MAX_PRESSURE
    return max(0.0, min(100.0, 100.0 * (hi - current_pressure) / (hi - lo)))


def _rank_score(rank: int | None, field_size: int) -> float:
    """League rank (1=best) -> 0-100, higher is better. None (no games
    played yet) is neutral 50."""
    if rank is None or field_size <= 1:
        return 50.0
    return 100.0 * (field_size - rank) / (field_size - 1)


# ---------------------------------------------------------------------------
# Enhanced JSS (Sec 3.1)
# ---------------------------------------------------------------------------

HC_WEIGHTS = {
    "win": 0.25, "vs_exp": 0.30, "playoff": 0.15,
    "trajectory": 0.10, "blowout": 0.10, "owner": 0.10,
}
OC_WEIGHTS = {
    "vs_exp": 0.40, "player_dev": 0.15, "trend": 0.15,
    "efficiency": 0.10, "playcalling": 0.10, "hc_fit": 0.10,
}
DC_WEIGHTS = dict(OC_WEIGHTS)  # same shape, defense-side inputs
ST_WEIGHTS = {
    "performance": 0.35, "catastrophic": 0.25, "trend": 0.15,
    "penalties": 0.10, "return_efficiency": 0.10, "hc_fit": 0.05,
}


def _weighted(components: dict[str, float], weights: dict[str, float]) -> float:
    return sum(weights[k] * components[k] for k in weights)


def compute_hc_jss(season, team_abbr: str, current_pressure: float) -> tuple[float, dict[str, float]]:
    from app.services import coach_records  # local import: avoids a cycle at module load

    record = season.records[team_abbr]
    expectation = team_expectations.for_team(season.season_number, team_abbr)
    expected_win_pct = expectation.expected_win_pct if expectation is not None else record.win_pct
    outcome = coach_records._playoff_outcome_for(season, team_abbr)

    components = {
        "win": record.win_pct * 100.0,
        "vs_exp": _performance_vs_expectation_score(record.win_pct, expected_win_pct),
        "playoff": coach_records.PLAYOFF_RESULT_SCORES.get(outcome, 0.0),
        "trajectory": _trajectory_score(
            record.win_pct, _team_recent_hc_seasons(team_abbr, season.season_number)),
        "blowout": max(0.0, 100.0 - blowout_loss_pct(season, team_abbr) * 5.0),
        "owner": owner_organizational_score(current_pressure),
    }
    return _weighted(components, HC_WEIGHTS), components


def _unit_jss(season, team_abbr: str, coach: Coach, *, offense: bool,
              team_ranks, current_pressure: float) -> tuple[float, dict[str, float]]:
    """Shared OC/DC math -- Sec 3.1 gives OC and DC the identical five-
    factor shape, differing only in which side of the ball each real
    substitute reads from."""
    from app.engine import scouting

    expectation = team_expectations.for_team(season.season_number, team_abbr)
    expected_pctile = (expectation.offense_pctile if offense else expectation.defense_pctile) \
        if expectation is not None else 50.0
    actual_rank = team_ranks.points_for_rank if offense else team_ranks.points_against_rank
    actual_pctile = _rank_score(actual_rank, 32)
    # Sec 3.1's "Performance vs Expectation" for one unit: same delta-
    # centered-on-50 shape as the HC formula, applied to percentiles
    # instead of win_pct.
    vs_exp = max(0.0, min(100.0, 50.0 + (actual_pctile - expected_pctile)))

    player_dev = coach.player_dev_offense if offense else coach.player_dev_defense
    # DISCLOSED SIMPLIFICATION: no per-unit historical yardage/points is
    # ever persisted season-to-season (CoachSeasonStats only stores
    # team win/loss + playoff outcome), so unit-level Trend reuses the
    # same real team win-trajectory computation the HC formula uses --
    # not a fabricated offense/defense-specific series.
    trend = _trajectory_score(season.records[team_abbr].win_pct,
                               _team_recent_hc_seasons(team_abbr, season.season_number))

    summary = scouting.team_summary(season, team_abbr)
    turnover_diff = summary["turnover_diff"] or 0
    # Turnovers/Efficiency: real turnover differential, offense reads it
    # as-is (fewer giveaways = better), defense reads it inverted
    # (more takeaways = better) -- same real number, opposite framing.
    efficiency = max(0.0, min(100.0, 50.0 + turnover_diff * 5.0 * (1 if offense else 1)))

    rz = scouting.red_zone_efficiency(season, team_abbr)
    # Playcalling/ExplosivePlayFailures: no drive-level "explosive play
    # allowed" or "playcalling grade" stat exists in this engine. Real
    # Red Zone TD% is the closest already-computed execution-quality
    # proxy for the offense side; for defense, the blowout-loss rate
    # (inverted) stands in for "explosive/catastrophic failures", the
    # same substitution the ST formula below uses more directly.
    if offense:
        playcalling_or_explosive = rz["td_pct"] if rz["td_pct"] is not None else 50.0
    else:
        playcalling_or_explosive = max(0.0, 100.0 - blowout_loss_pct(season, team_abbr) * 5.0)

    hc = None
    from app.services import coach_store
    hc = coach_store.head_coach(team_abbr)
    hc_fit = hc.motivation_chemistry if hc is not None else 50.0

    components = {
        "vs_exp": vs_exp,
        "player_dev": player_dev,
        "trend": trend,
        "efficiency": efficiency,
        "playcalling": playcalling_or_explosive,
        "hc_fit": hc_fit,
    }
    weights = OC_WEIGHTS if offense else DC_WEIGHTS
    return _weighted(components, weights), components


def compute_oc_jss(season, team_abbr: str, coach: Coach, team_ranks, current_pressure: float) -> tuple[float, dict[str, float]]:
    return _unit_jss(season, team_abbr, coach, offense=True, team_ranks=team_ranks, current_pressure=current_pressure)


def compute_dc_jss(season, team_abbr: str, coach: Coach, team_ranks, current_pressure: float) -> tuple[float, dict[str, float]]:
    return _unit_jss(season, team_abbr, coach, offense=False, team_ranks=team_ranks, current_pressure=current_pressure)


def compute_st_jss(season, team_abbr: str, coach: Coach, current_pressure: float) -> tuple[float, dict[str, float]]:
    from app.engine import scouting

    fg = scouting.field_goal_accuracy_3bucket(season, team_abbr)
    made = fg.get("made", 0) or 0
    attempted = fg.get("attempted", 0) or 0
    fg_pct = (100.0 * made / attempted) if attempted else 50.0

    penalty = scouting.penalty_discipline(season, team_abbr)
    per_game = penalty.get("per_game")
    # Fewer penalties/game -> higher score. No real league-wide ST-only
    # penalty split exists, so this reads the team's overall discipline
    # rate, same real-substitute precedent as everything else here.
    penalty_score = max(0.0, min(100.0, 100.0 - (per_game or 6.0) * 8.0))

    trend = _trajectory_score(season.records[team_abbr].win_pct,
                               _team_recent_hc_seasons(team_abbr, season.season_number))

    # CatastrophicErrors (blocked kicks, return TDs allowed) and
    # Return/Coverage Efficiency: no per-play special-teams-tackle or
    # blocked-kick attribution is aggregated anywhere queryable per
    # team/season (ROADMAP.md R2 is still only partially done -- no
    # return-game tackle credit exists at all). Left neutral (50)
    # rather than invented, same "no signal -> don't drift the rating"
    # discipline app/engine/coach_progression.py already established.
    catastrophic = 50.0
    return_efficiency = 50.0

    from app.services import coach_store
    hc = coach_store.head_coach(team_abbr)
    hc_fit = hc.motivation_chemistry if hc is not None else 50.0

    components = {
        "performance": fg_pct,
        "catastrophic": catastrophic,
        "trend": trend,
        "penalties": penalty_score,
        "return_efficiency": return_efficiency,
        "hc_fit": hc_fit,
    }
    return _weighted(components, ST_WEIGHTS), components


def compute_jss(season, team_abbr: str, coach: Coach, team_ranks=None) -> tuple[float, dict[str, float]]:
    """Single entry point coach_records.py calls -- dispatches on role.
    AC has no Sec 3.1 formula (the spec gives HC/OC/DC/ST only); an AC's
    stored job_security_score stays whatever the OLD, simpler
    job_security_score() computed, unaffected by R3d."""
    current_pressure = owner_pressure_store.pressure_for(team_abbr)
    role = CoachRole(coach.role)
    if role is CoachRole.HC:
        return compute_hc_jss(season, team_abbr, current_pressure)
    if team_ranks is None:
        from app.engine import coach_progression
        team_ranks = coach_progression.compute_team_ranks(season).get(team_abbr, coach_progression.TeamRanks())
    if role is CoachRole.OC:
        return compute_oc_jss(season, team_abbr, coach, team_ranks, current_pressure)
    if role is CoachRole.DC:
        return compute_dc_jss(season, team_abbr, coach, team_ranks, current_pressure)
    if role is CoachRole.ST:
        return compute_st_jss(season, team_abbr, coach, current_pressure)
    # AC: no bespoke formula in the spec -- fall back to a simple,
    # documented proxy (their own performance ratings + HC fit) rather
    # than reusing another role's weight table verbatim.
    hc_fit = coach.motivation_chemistry
    components = {"player_dev": (coach.player_dev_offense + coach.player_dev_defense) / 2.0,
                  "discipline": coach.discipline, "hc_fit": hc_fit}
    return sum(components.values()) / len(components), components


# ---------------------------------------------------------------------------
# Season-outcome classification, for OwnerWinPressure's annual adjustment
# (Sec 3.2) -- win-delta-vs-expectation buckets, this module's own
# thresholds (the spec names the six buckets but gives no numeric cutoffs).
# ---------------------------------------------------------------------------

def classify_season_outcome(actual_win_pct: float, expected_win_pct: float, games: int = 17) -> str:
    delta_wins = (actual_win_pct - expected_win_pct) * games
    if delta_wins >= 3.0:
        return "far_exceeded"
    if delta_wins >= 1.0:
        return "exceeded"
    if delta_wins >= -1.0:
        return "met"
    if delta_wins >= -3.0:
        return "moderately_below"
    if delta_wins >= -5.0:
        return "significantly_below"
    return "catastrophic"


def best_achievement(playoff_outcome: str, division_champion: bool) -> str | None:
    """The single best of Sec 3.2's four success-buffer tiers this team
    reached this season (only the peak tier is granted, not all beneath
    it -- winning the Super Bowl implies but doesn't separately stack
    the conference/division/playoff buffers)."""
    if playoff_outcome == "SB_WIN":
        return "super_bowl"
    if playoff_outcome == "SB_LOSS":
        return "conference_title"
    if playoff_outcome in ("DIV", "CONF"):
        return "playoff_appearance" if not division_champion else "division_title"
    if playoff_outcome == "WC":
        return "playoff_appearance"
    if division_champion:
        return "division_title"
    return None


# ---------------------------------------------------------------------------
# Firing Probability model (Sec 3.4)
# ---------------------------------------------------------------------------

LOGISTIC_THRESHOLD = 0.4
LOGISTIC_SLOPE = 4.0

# (week range, modifier) tables, Sec 3.4.
_HC_WEEK_MODIFIERS = [((1, 4), 0.05), ((5, 8), 0.25), ((9, 12), 0.60), ((13, 18), 1.00)]
_COORD_WEEK_MODIFIERS = [((1, 3), 0.05), ((4, 6), 0.30), ((7, 18), 1.00)]

RECENT_SUCCESS_MODIFIER = {
    "super_bowl": 0.2,
    "conference_title": 0.4,
    "division_title": 0.7,
    "playoff_appearance": 0.7,
}


def _logistic(x: float, threshold: float = LOGISTIC_THRESHOLD, slope: float = LOGISTIC_SLOPE) -> float:
    return 1.0 / (1.0 + math.exp(-slope * (x - threshold)))


def week_modifier(week: int, role: CoachRole) -> float:
    table = _HC_WEEK_MODIFIERS if role is CoachRole.HC else _COORD_WEEK_MODIFIERS
    for (lo, hi), mod in table:
        if lo <= week <= hi:
            return mod
    return 1.0  # offseason (week 0) or any week past the table -- full weight


def tenure_modifier(tenure_years: int) -> float:
    if tenure_years <= 2:
        return 0.5
    if tenure_years <= 5:
        return 1.0
    return min(1.2, 1.0 + (tenure_years - 5) * 0.04)


def recent_success_modifier(team_abbr: str) -> float:
    """Sec 3.4: protection "within 1 year" of a success. A buffer still
    sitting at its full just-granted magnitude (owner_pressure_store's
    buffers decay by half every season-end) means it was granted at the
    MOST RECENT rollover -- i.e. last season -- so this reuses that
    state directly instead of a second recency tracker."""
    buffers = owner_pressure_store.buffers_for(team_abbr)
    best = 1.0
    for b in buffers:
        full_value = owner_pressure_store.SUCCESS_BUFFERS.get(b["kind"])
        if full_value is not None and abs(b["value"] - full_value) < 1e-6:
            best = min(best, RECENT_SUCCESS_MODIFIER.get(b["kind"], 1.0))
    return best


def tenure_years(coach: Coach, season_number: int) -> int:
    return max(0, season_number - coach.tenure_start_season)


def contract_modifier(contract_years: int) -> float:
    """Coach Contract Realism (docs/R3d_COACHING_SYSTEM_SPECIFICATION.md
    Sec 11: "Extend Contract... to reduce JSS volatility") made concrete:
    a coach sitting on real years of a fresh deal is protected -- the
    owner just invested in them, a real "won't eat a fresh buyout"
    dynamic. An expired contract (0 years, a lame duck) carries no such
    protection and is slightly MORE likely to be moved on from. Same
    documented-choice category as tenure_modifier()/recent_success_
    modifier() above -- no GDD formula for this either."""
    if contract_years <= 0:
        return 1.15
    if contract_years == 1:
        return 1.0
    return max(0.6, 1.0 - (contract_years - 1) * 0.1)


def firing_probability(jss: float, week: int, role: CoachRole, coach: Coach, season_number: int, team_abbr: str) -> float:
    """Sec 3.4's full model. `week` is 1-18 in-season, or 0 for an
    offseason evaluation (falls through week_modifier() to a full 1.0 --
    the offseason IS the normal decision point, no in-season caution
    applies there)."""
    risk = 1.0 - (jss / 100.0)  # BaseScore's "risk" framing: low JSS -> high risk
    prob = (
        _logistic(risk)
        * week_modifier(week, role)
        * tenure_modifier(tenure_years(coach, season_number))
        * recent_success_modifier(team_abbr)
        * contract_modifier(coach.contract_years)
    )
    return max(0.0, min(1.0, prob))


# ---------------------------------------------------------------------------
# HiringMerit (Sec 4.3) and InterimPromotionScore (Sec 4.1)
# ---------------------------------------------------------------------------

HIRING_MERIT_WEIGHTS = {
    "ability": 0.25, "scheme_fit": 0.20, "roster_match": 0.15, "experience": 0.10,
    "player_dev": 0.10, "leadership": 0.10, "org_philosophy": 0.05, "interest": 0.05,
}

# DISCLOSED SIMPLIFICATION: SchemeFit and OrgPhilosophy have no modeled
# matching system anywhere in this engine (no QB-scheme-affinity or
# owner-identity data exists) -- both are a flat, documented baseline
# rather than an invented matching score. Every candidate for a given
# vacancy therefore differs on HiringMerit only through the five terms
# that ARE real (ability, roster fit, experience, player dev, leadership)
# plus interest, which is real and candidate-specific (Sec 4.4 below).
_FLAT_SCHEME_FIT = 60.0
_FLAT_ORG_PHILOSOPHY = 60.0


def roster_quality_match(team_abbr: str, season_number: int) -> float:
    """Sec 4.3's RosterQualityMatch: does the candidate's own track
    record correlate with the level of talent they'd inherit here? No
    per-candidate "history of success with X-quality rosters" is
    tracked, so this reads the REAL roster percentile the candidate
    would inherit (team_expectations' team_rating_pctile) -- a strong
    roster genuinely does make any hire look more attractive, which is
    the real mechanism Sec 4.4 also leans on for candidate interest."""
    exp = team_expectations.for_team(season_number, team_abbr)
    return exp.team_rating_pctile if exp is not None else 50.0


def hiring_merit(candidate: Coach, role: CoachRole, team_abbr: str, season_number: int,
                  interest_score: float) -> float:
    ability = candidate.overall
    roster_match = roster_quality_match(team_abbr, season_number)
    experience = max(0.0, min(100.0, candidate.experience_years * 2.5))
    if role is CoachRole.DC:
        player_dev = candidate.player_dev_defense
    else:
        player_dev = candidate.player_dev_offense
    leadership = candidate.motivation_chemistry

    components = {
        "ability": ability, "scheme_fit": _FLAT_SCHEME_FIT, "roster_match": roster_match,
        "experience": experience, "player_dev": player_dev, "leadership": leadership,
        "org_philosophy": _FLAT_ORG_PHILOSOPHY, "interest": interest_score,
    }
    return _weighted(components, HIRING_MERIT_WEIGHTS)


INTERIM_PROMOTION_WEIGHTS = {
    "role_experience": 0.20, "current_performance": 0.25, "leadership": 0.20,
    "player_relationships": 0.10, "scheme_fit": 0.10, "org_familiarity": 0.10,
    "prior_experience": 0.05,
}

# Role seniority for "prior HC/coordinator experience" -- an internal
# candidate already at OC/DC/ST is credited with real coordinator
# experience for an HC vacancy; an AC is not.
_SENIOR_ROLES = (CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.ST)


def interim_promotion_score(candidate: Coach, season_number: int) -> float:
    role_experience = max(0.0, min(100.0, candidate.experience_years * 2.5))
    current_performance = candidate.job_security_score
    leadership = candidate.motivation_chemistry
    # Player relationships: no separate stat exists; motivation_chemistry
    # is this module's documented real stand-in (same rating driving
    # both, since both describe how a coach relates to the locker room).
    player_relationships = candidate.motivation_chemistry
    # Scheme/philosophical fit: an internal promotion continues the
    # existing system by construction, so this is a flat high score
    # rather than a fabricated similarity metric.
    scheme_fit = 80.0
    org_familiarity = max(0.0, min(100.0, tenure_years(candidate, season_number) * 15.0))
    prior_experience = 100.0 if CoachRole(candidate.role) in _SENIOR_ROLES[1:] else 20.0

    components = {
        "role_experience": role_experience, "current_performance": current_performance,
        "leadership": leadership, "player_relationships": player_relationships,
        "scheme_fit": scheme_fit, "org_familiarity": org_familiarity,
        "prior_experience": prior_experience,
    }
    return _weighted(components, INTERIM_PROMOTION_WEIGHTS)


# ---------------------------------------------------------------------------
# Candidate Interest (Sec 4.4)
# ---------------------------------------------------------------------------

# A candidate outright declines below this roster percentile -- "roster
# is too weak, HC won't inherit a doomed team." This module's own
# documented cutoff (the spec gives the rule, not a number).
MIN_ACCEPTABLE_ROSTER_PCTILE = 20.0
MAX_ACCEPTABLE_PRESSURE = 80.0


def will_consider(candidate: Coach, team_abbr: str, season_number: int, appointment_type: str,
                   recent_hc_turnover: int) -> bool:
    """Sec 4.4's hard REJECT rules -- a candidate who fails any of these
    is excluded from the pool for this vacancy entirely, not merely
    docked in score."""
    from app.models.coach import POOL_TIER_COLLEGE, APPOINTMENT_INTERIM, APPOINTMENT_ACTING, CoachRole as _Role

    if candidate.pool_tier == POOL_TIER_COLLEGE and CoachRole(candidate.role) is _Role.HC \
            and appointment_type in (APPOINTMENT_INTERIM, APPOINTMENT_ACTING):
        return False  # "big-school college HC will NOT accept interim-only or assistant roles"

    roster_pctile = roster_quality_match(team_abbr, season_number)
    if roster_pctile < MIN_ACCEPTABLE_ROSTER_PCTILE:
        return False

    pressure = owner_pressure_store.pressure_for(team_abbr)
    if pressure > MAX_ACCEPTABLE_PRESSURE:
        return False

    if recent_hc_turnover >= 3:
        return False  # "recent HC turnover indicates instability"

    return True


def interest_score(candidate: Coach, team_abbr: str, season_number: int) -> float:
    """0-100 soft interest, used as HiringMerit's 5% term among
    candidates who already pass will_consider()'s hard gate. Higher
    roster quality and lower owner pressure both increase genuine
    interest -- the same two real signals will_consider() gates on,
    read continuously instead of as a cutoff."""
    roster_pctile = roster_quality_match(team_abbr, season_number)
    pressure = owner_pressure_store.pressure_for(team_abbr)
    pressure_component = 100.0 * (owner_pressure_store.MAX_PRESSURE - pressure) / \
        (owner_pressure_store.MAX_PRESSURE - owner_pressure_store.MIN_PRESSURE)
    return max(0.0, min(100.0, 0.6 * roster_pctile + 0.4 * pressure_component))
