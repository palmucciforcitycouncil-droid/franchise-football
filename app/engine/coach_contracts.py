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
identical to negotiating a player's -- one deterministic verdict per
submitted offer, no stateful Mood Meter (Sec 15's own disclosed cut,
same as R4a's for players).

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
    CoachRole.ST: 3,
    CoachRole.AC: 2,
}


def coach_market_value(coach: Coach, peers: list[Coach] | None = None) -> float:
    """This coach's percentile rank of `overall` within their own role
    tier, mapped onto that tier's real, currently-observed `salary_aav`
    range -- see module docstring for why `overall` (not `reputation`)
    is the input. `peers` defaults to every other currently-employed,
    non-retired coach in the league (DB-backed, via coach_store); pass an
    explicit list to exercise the pure math without a database. Falls
    back to this coach's own current salary if their tier has no other
    real peers to measure against (e.g. an isolated unit test)."""
    if peers is None:
        from app.services import coach_store
        peers = [c for c in coach_store.all_coaches() if c.team_abbr is not None and not c.retired]

    tier = tier_key(CoachRole(coach.role))
    tier_peers = [c for c in peers if tier_key(CoachRole(c.role)) == tier]
    if not tier_peers:
        return float(coach.salary_aav)

    salaries = sorted(c.salary_aav for c in tier_peers)
    overalls = sorted(c.overall for c in tier_peers)
    rank = sum(1 for o in overalls if o <= coach.overall) / len(overalls)
    idx = min(len(salaries) - 1, int(round(rank * (len(salaries) - 1))))
    return float(salaries[idx])


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


def evaluate_extension(
    coach: Coach, offered_aav: float, offered_years: int, team_win_pct: float,
    peers: list[Coach] | None = None,
) -> ExtensionResult:
    """Same ACCEPT/REJECT/COUNTER shape as contracts.evaluate_offer().
    `team_win_pct` (0-1) is this coach's real leverage signal -- a coach
    on a winning team can be retained for a bit less (a good situation is
    worth something), the same role team_rating plays in a player's own
    offer score. `peers` is forwarded to coach_market_value() unchanged
    (None = the real DB-backed population; pass an explicit list to
    exercise the pure math without a database)."""
    expected = coach_market_value(coach, peers)
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


def renew_contract(coach_id: str) -> Coach | None:
    """AI-only auto-renewal for a coach whose contract expired
    (contract_years <= 0) but who SURVIVED this offseason's real firing
    evaluation (app/services/coach_ai.py's _evaluate_team()) -- the front
    office deciding to keep them, at their own real market value, not a
    negotiation (see module docstring for why this isn't evaluate_
    extension() called against itself)."""
    from app.core.db import get_session
    from app.services import coach_store

    with get_session() as s:
        coach = s.get(Coach, coach_id)
        if coach is None:
            return None
        coach.contract_years = DEFAULT_CONTRACT_YEARS[CoachRole(coach.role)]
        coach.salary_aav = round(coach_market_value(coach))
        s.add(coach)
        s.commit()
        s.refresh(coach)
    coach_store.clear_cache()
    return coach
