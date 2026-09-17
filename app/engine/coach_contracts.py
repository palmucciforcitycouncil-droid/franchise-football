"""
Coach Contract Realism + "Extend Contract" (docs/R3d_COACHING_SYSTEM_
SPECIFICATION.md Sec 11: "Re-negotiate for improved terms to reduce JSS
volatility"; Sec 15's own "Hiring salary negotiation... out of scope,
coaches accept/reject based on Hiring Merit + interest, not salary
haggling" -- that cut is about the HIRING market, not an EXISTING
coach's own renegotiation, which this module is).

**The real gap this closes**: `Coach.contract_years` existed since R3b
but was completely inert -- never decremented, never set by
`coach_replacement.execute_hire()` on a new hire (silently leaving an
external pool candidate stuck at `salary_aav=0` and `contract_years=2`
forever), and read by nothing. Same "if a rating does nothing, it
shouldn't exist" standard this project already applied to
`clock_management`/`challenge_sense` (ROADMAP.md Sec 4c-addendum) --
except here the fix is making the field real instead of deleting it,
since Sec 11 explicitly calls for a real Extend Contract control.

**Coach market value, this module's own disclosed formula** (no GDD
source specifies one, same category as `contracts.expected_market_
value()`'s own disclosed player formula): a coach's percentile rank of
`overall` (their CURRENT, ratings-driven composite -- not the fixed-at-
import `reputation`) within their own role tier's real, currently-
employed salary distribution. `overall` is used specifically because
`reputation` never moves after import/hire, while `overall` DOES drift
with real post-hire performance via `coach_progression.py` -- a coach
who's genuinely improved should be able to command more at extension
time, the same "prove it, get paid" dynamic real contract negotiation
has. Measured against the real, current population (same `coaching.
LeagueBaseline` philosophy: measure, don't assume), not a fabricated
curve.

**Extend Contract negotiation** mirrors `contracts.evaluate_offer()`'s
exact ACCEPT/REJECT/COUNTER shape (same weights-solved-backwards counter
math) so the user's experience negotiating a coach's extension feels
identical to negotiating a player's. As of 2026-09-14 the Staff page runs
it through the same shared Negotiation modal and the same stateful mood
layer (app/engine/negotiation.py) as player re-signs and free agency.

**Staff salary cap (2026-09-14)**: all of a team's coach salaries combined
must fit contracts.coach_salary_cap_for_season() ($15M in 2026, growing
with the player cap). The user's hire/extend routes refuse an offer that
breaks it; AI hires and renewals trim salary to the room left
(affordable_salary()). Coach market value is priced on Brian's real 2026
role ranges grown by the same cap growth factor, so demands escalate
every year.

**"Reduce JSS volatility" made concrete**: `coach_hiring.py` had no
actual volatility variable to reduce -- `contract_modifier()` below is
the real, disclosed mechanic Sec 11's one-line spec maps onto: a coach
sitting on real years of a fresh contract is protected (real-world "the
owner just paid this coach, won't eat a fresh buyout"), while an expired
contract (0 years, a "lame duck") carries no such protection and is
slightly MORE likely to be moved on from. Wired into `coach_hiring.
firing_probability()`.

**AI-side contract expiration** (`renew_contract()`) is deliberately NOT
a self-negotiation through `evaluate_extension()` -- an AI front office
doesn't haggle with itself. Instead, `app/services/coach_ai.py`'s
`_evaluate_team()` reuses the SAME firing-probability roll it already
does every offseason: a coach who survives that roll (including the real
`contract_modifier()` lame-duck penalty above) gets a fresh contract at
their own real market value; a coach who doesn't survive it goes through
the existing fire-and-replace pipeline exactly as before. The user's own
team is never auto-renewed or auto-let-go this way (`run_offseason_
autonomy()`'s existing `exclude_team_abbr` already guarantees this) --
an expiring contract on the user's own team just sits at 0 until the
user explicitly Extends or Fires, same "the user's own coaching moves are
always manual" precedent R3d already established for Fire/Hire.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum

from app.models.coach import Coach, CoachRole, tier_key

# This module's own documented choice (no GDD source): real-world-ish
# tenure by organizational level, used both for a NEW hire's fresh deal
# (coach_replacement.execute_hire()) and for an AI team's auto-renewal on
# contract expiration (renew_contract() below).
DEFAULT_CONTRACT_YEARS: dict[CoachRole, int] = {
    CoachRole.HC: 4,
    CoachRole.OC: 3,
    CoachRole.DC: 3,
    CoachRole.AC: 2,
}


# Brian's 2026-09-14 fixes doc: every team may carry at most 4 assistant
# coaches (HC + OC + DC + ST + 4 AC = a 9-coach staff), enforced at every
# point a coach can join a team (user hire route, AI backfill, execute_hire).
MAX_ASSISTANTS = 4

# Brian's real-world 2026 salary ranges by role, (min, median, max) -- the
# same table scripts/migrate_2026_09_14_staff_payroll.py mapped every
# existing coach onto. Market value is a position inside this range, grown
# by contracts.cap_growth_factor() so coach demands escalate each year at
# exactly the rate the player cap and the staff cap do.
ROLE_SALARY_RANGE_2026: dict[CoachRole, tuple[int, int, int]] = {
    CoachRole.HC: (4_000_000, 7_000_000, 10_000_000),
    CoachRole.OC: (1_000_000, 1_500_000, 2_500_000),
    CoachRole.DC: (1_000_000, 1_500_000, 2_500_000),
    CoachRole.AC: (200_000, 500_000, 800_000),
}


def _growth(season_number: int | None) -> float:
    if season_number is None:
        return 1.0
    from app.engine import contracts
    return contracts.cap_growth_factor(season_number)


def role_salary_floor(role: CoachRole, season_number: int | None) -> float:
    return ROLE_SALARY_RANGE_2026[role][0] * _growth(season_number)


def _range_value(role: CoachRole, pct: float) -> float:
    lo, mid, hi = ROLE_SALARY_RANGE_2026[role]
    pct = max(0.0, min(1.0, pct))
    if pct <= 0.5:
        return lo + (mid - lo) * (pct / 0.5)
    return mid + (hi - mid) * ((pct - 0.5) / 0.5)


def coach_market_value(coach: Coach, peers: list[Coach] | None = None,
                       season_number: int | None = None) -> float:
    """What this coach can command in `role` = coach.role: their
    percentile rank of `overall` within their own role tier's employed
    peers (see module docstring for why `overall`, not `reputation`),
    mapped onto that role's real 2026 range (ROLE_SALARY_RANGE_2026,
    piecewise through the median) and grown to `season_number`'s dollars.

    Changed 2026-09-14: this used to return a PEER'S CURRENT SALARY at that
    percentile, which never grew with the cap (Brian: "salary demands
    escalate along with the salary cap") and returned $0 for anyone whose
    tier peers were unpaid pool candidates. `peers` defaults to every
    employed, non-retired coach (DB-backed); pass an explicit list to
    exercise the pure math without a database. With no peers at all, the
    percentile falls back to `overall` itself on the 40-99 rating scale.
    `season_number=None` means 2026 dollars (DB-backed callers that know
    the season should always pass it)."""
    return market_value_for_role(coach, CoachRole(coach.role), peers, season_number)


def market_value_for_role(coach: Coach, role: CoachRole, peers: list[Coach] | None = None,
                          season_number: int | None = None) -> float:
    """coach_market_value() priced for `role` instead of the coach's
    current one -- what a promotion or a pool hire into `role` would cost."""
    if peers is None:
        from app.services import coach_store
        peers = [c for c in coach_store.all_coaches() if c.team_abbr is not None and not c.retired]

    tier = tier_key(role)
    tier_overalls = [c.overall for c in peers if tier_key(CoachRole(c.role)) == tier]
    if tier_overalls:
        pct = sum(1 for o in tier_overalls if o <= coach.overall) / len(tier_overalls)
    else:
        pct = (coach.overall - 40) / 59.0
    return _range_value(role, pct) * _growth(season_number)


def team_staff_payroll(team_abbr: str, exclude_coach_id: str | None = None) -> int:
    """Sum of salary_aav across a team's employed, non-retired staff."""
    from app.services import coach_store
    return sum(c.salary_aav for c in coach_store.staff_for(team_abbr) if c.coach_id != exclude_coach_id)


def staff_cap_room(team_abbr: str, season_number: int, exclude_coach_id: str | None = None) -> float:
    """Staff cap (contracts.coach_salary_cap_for_season) minus current
    payroll -- `exclude_coach_id` frees that coach's own salary first (an
    extension replaces it; a promotion re-prices it)."""
    from app.engine import contracts
    return contracts.coach_salary_cap_for_season(season_number) - team_staff_payroll(team_abbr, exclude_coach_id)


def affordable_salary(role: CoachRole, market: float, room: float, season_number: int | None) -> float:
    """What an AI front office actually pays: market value, trimmed to the
    staff cap room it has. Never below the role's own floor -- a staff so
    over the cap that even the floor doesn't fit is a disclosed edge case
    (the migrated payrolls all sit well under $15M), not a $0 coach."""
    return max(role_salary_floor(role, season_number), min(market, room))


class ExtensionVerdict(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    COUNTER = "COUNTER"


@dataclass(frozen=True)
class ExtensionResult:
    verdict: ExtensionVerdict
    offer_score: float
    counter_aav: float | None = None
    counter_years: int | None = None


# This module's own documented weights/thresholds -- same category as
# contracts.py's own Sec-8.3.3-derived W_AAV/W_YEARS/W_TEAM (a real
# formula shape reused, not a fabricated new one). Years counts for
# slightly more than a player deal's (5 vs. 4 "full security" years) --
# real coaching contracts commonly run a year or two longer than a
# veteran player's.
W_AAV = 0.70
W_YEARS = 0.15
W_TEAM = 0.15
YEARS_FULL_POINTS = 5.0
ACCEPT_THRESHOLD = 0.97
COUNTER_THRESHOLD = 0.80


CONSIDERING_FLOOR = 0.88


def negotiation_model(coach: Coach, season_number: int | None):
    """This module's thresholds/AAV weight for app/engine/negotiation.py's
    mood layer, which runs on top of evaluate_extension()'s raw score."""
    from app.engine.negotiation import ScoreModel
    return ScoreModel(
        accept_threshold=ACCEPT_THRESHOLD, counter_threshold=COUNTER_THRESHOLD,
        considering_floor=CONSIDERING_FLOOR, w_aav=W_AAV,
        expected_aav=coach_market_value(coach, season_number=season_number), reaction=coach_offer_reaction,
    )


def coach_offer_reaction(score: float) -> str:
    """Live "Coach Reaction" label for the shared Negotiation modal --
    the same bands contracts.offer_reaction() uses, since this module's
    ACCEPT/COUNTER thresholds (0.97/0.80) are identical to that one's."""
    if score >= 1.05:
        return "Very Interested"
    if score >= ACCEPT_THRESHOLD:
        return "Interested"
    if score >= CONSIDERING_FLOOR:
        return "Considering"
    if score >= COUNTER_THRESHOLD:
        return "Lowball"
    return "Not Interested"


def evaluate_extension(
    coach: Coach, offered_aav: float, offered_years: int, team_win_pct: float,
    peers: list[Coach] | None = None, season_number: int | None = None,
) -> ExtensionResult:
    """Same ACCEPT/REJECT/COUNTER shape as contracts.evaluate_offer().
    `team_win_pct` (0-1) is this coach's real leverage signal -- a coach
    on a winning team can be retained for a bit less (a good situation is
    worth something), the same role team_rating plays in a player's own
    offer score. `peers`/`season_number` are forwarded to
    coach_market_value() unchanged (None peers = the real DB-backed
    population; pass an explicit list to exercise the pure math without a
    database)."""
    expected = coach_market_value(coach, peers, season_number)
    aav_points = min(1.3, offered_aav / expected) if expected else 1.0
    years_points = min(1.0, offered_years / YEARS_FULL_POINTS)
    team_points = max(0.0, min(1.0, team_win_pct))

    score = W_AAV * aav_points + W_YEARS * years_points + W_TEAM * team_points

    if score >= ACCEPT_THRESHOLD:
        return ExtensionResult(ExtensionVerdict.ACCEPT, score)
    if score >= COUNTER_THRESHOLD:
        needed_aav_points = (ACCEPT_THRESHOLD - W_YEARS * years_points - W_TEAM * team_points) / W_AAV
        counter_aav = math.ceil(max(offered_aav, needed_aav_points * expected))
        return ExtensionResult(ExtensionVerdict.COUNTER, score, counter_aav=counter_aav, counter_years=offered_years)
    return ExtensionResult(ExtensionVerdict.REJECT, score)


def renew_contract(coach_id: str, season_number: int | None = None) -> Coach | None:
    """AI-only auto-renewal for a coach whose contract expired
    (contract_years <= 0) but who SURVIVED this offseason's real firing
    evaluation (app/services/coach_ai.py's _evaluate_team()) -- the front
    office deciding to keep them, at their own real market value, not a
    negotiation (see module docstring for why this isn't evaluate_
    extension() called against itself). 2026-09-14: the renewal salary is
    trimmed to what the team's staff cap can absorb (affordable_salary)."""
    from app.core.db import get_session
    from app.services import coach_store

    with get_session() as s:
        coach = s.get(Coach, coach_id)
        if coach is None:
            return None
        role = CoachRole(coach.role)
        coach.contract_years = DEFAULT_CONTRACT_YEARS[role]
        market = coach_market_value(coach, season_number=season_number)
        if coach.team_abbr is not None and season_number is not None:
            room = staff_cap_room(coach.team_abbr, season_number, exclude_coach_id=coach.coach_id)
            coach.salary_aav = round(affordable_salary(role, market, room, season_number))
        else:
            coach.salary_aav = round(market)
        s.add(coach)
        s.commit()
        s.refresh(coach)
    coach_store.clear_cache()
    return coach
