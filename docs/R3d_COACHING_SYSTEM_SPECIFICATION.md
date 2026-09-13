# R3d: Coach Hiring, Firing & Promotion Market

**Status:** Design Complete (2026-09-12). Ready for Implementation.  
**Roadmap Entry:** ROADMAP.md §4d  
**Related:** GDD Sec 8.2.3 (updated 2026-09-12)  
**Dependencies:** R3a/R3b/R3c (DONE), R4a (Contracts, DONE), A1/A2/A3 (Roster Strength, DONE)

---

## 1. Overview

R3d builds the complete coach hiring/firing/promotion market on top of the existing Job Security Score system (R3c). This is NOT a deterministic "JSS < 30 fires HC" system. Instead:

- **Job Security Score** reflects "how satisfied is the org with this coach?" (0-100, context-aware)
- **OwnerWinPressure** reflects "how urgently does ownership want to win?" (20-90, franchise-level, persistent)
- **Firing Probability** combines both, plus trajectory, expectations, unit performance, tenure, and randomness
- **Replacement Logic** is separate: when a coach is fired, the system decides **who to hire**, not just "fire or keep"

AI teams (all 31 non-user) autonomously manage coaching every offseason and in-season. The user's own team is manual via Staff page controls (Hire, Fire, Promote buttons).

---

## 2. Settled Decisions (Do Not Reopen)

1. **AI coaching is autonomous, not user-controlled** except for the user's own team
2. **AI coaching follows the same deterministic-verdict pattern as player FA** (Sec 8.3.3, 8.4) — not a complex multi-team bidding war
3. **No salary cap on coach contracts** — real NFL has none, so this engine has none
4. **Multi-team AI bidding wars are out of scope** — single verdicts only (same R4 pattern)
5. **JSS's existing partial formula is fair game** (can fire off current state without finishing `PreseasonPowerRankDelta`/`BlowoutLosses%`)
6. **OwnerWinPressure replaces the old OwnerPatience flat-50 stub** — call it `owner_patience` in code but make it dynamic and persistent
7. **Coach free-agent pool is seeded from Excel file** — real coaches and real ratings, college coaches rated lower than current NFL, big-school college HC won't accept assistant roles
8. **Build hiring/firing/promotion systems simultaneously**, not in separate phases

---

## 3. Core Systems

### 3.1 Job Security Score (JSS) — Enhanced

**Applies to:** HC, OC, DC, ST, AC (all separately)

**Formula (0-100 scale):**
```
JSS = 25%×WinPerformance 
    + 30%×PerformanceVsExpectation 
    + 15%×PlayoffPerformance 
    + 10%×Trajectory 
    + 10%×Blowouts/Dysfunction 
    + 10%×Owner/OrganizationalFactors
```

**Each component:**
- **WinPerformance:** Actual wins vs. league average (normalized)
- **PerformanceVsExpectation:** Actual results vs. preseason expectations (THE key differentiator; a 7-10 rebuilding team doing better than expected has higher JSS than a 10-7 contender doing worse)
- **PlayoffPerformance:** How far did the team go? Made playoffs? Lost early? Won playoff game? Conference? Super Bowl?
- **Trajectory:** Is the team improving, stable, declining, or collapsing year-over-year?
- **Blowouts/Dysfunction:** Frequency of 20+ point losses, late-season collapses, discipline issues
- **Owner/Organizational:** Is the franchise itself in chaos? Owner turnover? Major medical/personal issues?

**Interpretation:**
| JSS | Status |
|---|---|
| 80-100 | Extremely secure |
| 65-79 | Secure |
| 50-64 | Stable |
| 35-49 | Warm seat |
| 20-34 | Hot seat |
| 10-19 | Very hot |
| 0-9 | Critical |

**Coordinator-specific JSS:**
- **OC:** Offensive Performance vs Expectation (40%), QB/Player Dev (15%), Offensive Trend (15%), Turnovers/Efficiency (10%), Playcalling (10%), HC/Fit (10%)
- **DC:** Defensive Performance vs Expectation (40%), Player Dev (15%), Defensive Trend (15%), Efficiency (10%), Explosive Play Failures (10%), HC/Fit (10%)
- **ST:** Overall ST Performance (35%), Catastrophic Errors (25%), Trend (15%), Penalties (10%), Return/Coverage Efficiency (10%), HC/Fit (5%)

**Key insight:** ST is especially sensitive to catastrophic failures (blocked kicks, return TDs allowed). **One mistake ≠ automatic firing.** Repeated failures do carry weight.

### 3.2 OwnerWinPressure — New Franchise-Level State

**Range:** 20-90 (persistent, does NOT reset when HC is fired)

**Annual adjustment (after season ends):**
| Outcome | Change |
|---|---|
| Far exceeded expectations | -3 |
| Exceeded expectations | -2 |
| Met expectations | 0 |
| Moderately below expectations | +2 |
| Significantly below expectations | +4 |
| Catastrophic failure | +6 |

**Recent success buffers** (decaying):
- Super Bowl championship: -8
- Conference championship: -5
- Division championship: -3
- Playoff appearance: -1

These decay — a Super Bowl winner going 8-9 the next year survives. If poor performance continues, protection evaporates.

**Key mechanics:**
- One bad season creates concern
- Two consecutive bad seasons create meaningful pressure
- Three+ create severe pressure
- Sustained success gradually reduces pressure
- Owner pressure has **memory** across years

### 3.3 PerformanceExpectation — Season-Specific State

Derived from **preseason Power Ranking** (app/engine/roster_strength.py's `team_rating`), frozen at start of Week 1.

**Captures:**
- Expected wins
- Expected playoff probability
- Expected division/conference finish
- Expected championship contention level
- Expected offensive/defensive/special-teams performance

**Midseason adjustments** (bounded, slow-moving):
- Starting QB injury: -2 to -4 expected wins
- Multiple major injuries: -1 to -2 wins
- Major trade/FA changes: ±1 to ±2 wins
- Significant player development: ±0.5 to ±1 wins

*Adjust expectations cautiously — they're the baseline for coaching evaluation.*

### 3.4 Firing Probability Model

**NOT a hard threshold.** Instead, a probabilistic model:

```
BaseScore = 0.25×WinPerf + 0.30×ExpDelta + 0.15×PlayoffPerf 
          + 0.10×Trajectory + 0.10×BlowoutDysf + 0.10×Owner/Org

FiringProbability = Logistic(BaseScore, threshold=0.4, slope=4.0)
                  × InSeasonWeekModifier
                  × TenureModifier
                  × RecentSuccessModifier
```

**In-Season Week Modifiers (HC):**
| Weeks | Modifier |
|---|---|
| 1-4 | 0.05 |
| 5-8 | 0.25 |
| 9-12 | 0.60 |
| 13-18 | 1.00 |

**Early-season HC firings are extraordinarily rare but not impossible.** Emergency overrides exist for severe locker-room collapse, catastrophic performance relative to expectations, or extreme organizational dysfunction.

**Coordinator Modifiers (earlier gates):**
| Weeks | Modifier |
|---|---|
| 1-3 | 0.05 |
| 4-6 | 0.30 |
| 7-18 | 1.00 |

**Tenure Modifier:**
- Year 1-2: 0.5 (high tolerance for volatility)
- Year 3-5: 1.0 (normal)
- Year 6+: 1.0-1.2 (declining immunity over time)

**Recent Success Modifier:**
- Within 1 year of playoffs: 0.7
- Within 1 year of conference title: 0.4
- Within 1 year of Super Bowl: 0.2

---

## 4. Replacement Logic — Separate from Firing

When a coach is fired, the system decides **WHO TO HIRE** via this flow:

### 4.1 Interim Promotion vs. External Hire

**InterimPromotionScore** (for internal candidates):
| Factor | Weight |
|---|---|
| Existing role/experience | 20% |
| Current role performance | 25% |
| Leadership/management ability | 20% |
| Player relationships | 10% |
| Scheme/philosophical fit | 10% |
| Organizational familiarity | 10% |
| Prior HC/coordinator experience | 5% |

**Decision:**
- Calculate promotion probability for each eligible coach
- If high-scored internal candidate exists: probably promote (interim status)
- If no strong internal candidate: search external pool

**Promotion Hierarchy (for each vacant role):**
- **HC vacancy:** OC > DC > ST > QB coach > position coach > external
- **OC vacancy:** QB coach > Passing Game Coordinator > Run Game Coordinator > assistant > external
- **DC vacancy:** Defensive Pass Coordinator > LB coach > DB coach > DL coach > assistant > external
- **ST vacancy:** Assistant ST coach > ST specialist > other > external

### 4.2 External Candidate Pool & Ratings

**Tier 1 (Internal):** Current staff members

**Tier 2 (External NFL):**
- Unemployed former HCs
- Recent fired coaches
- Unemployed coordinators
- Experienced assistants from other teams

**Tier 3 (College & Other):**
- College HCs (Power Five, Group of Five, FCS)
- College coordinators
- Former NFL coaches retired/out of work

**Rating Assignment** (see Excel seed file for details):
- **Current NFL HCs/OC/DC/ST:** Base ratings 70-99 (real coaches, real spread)
- **Current NFL AC:** Base ratings 40-75
- **Former NFL HCs:** 55-85 (depends on record, how long ago)
- **Former NFL OC/DC:** 50-80
- **College HCs:** 
  - Power Five: 50-80 (capped below best NFL HCs)
  - Group of Five: 45-70
  - FCS: 40-65
- **College OC/DC:** 45-75
- **Background bonus:** Real credentials (2x national champion, etc.) boost ratings; vague backgrounds don't fabricate numbers

**Key constraint:** College coaches rated LOWER than current NFL coaches. No wholesale replacement of NFL staff.

### 4.3 Coach_Hiring_Merit Score

When evaluating a candidate for a specific vacancy:

```
HiringMerit = 0.25×CoachingAbility 
            + 0.20×SchemeFit 
            + 0.15×RosterQualityMatch 
            + 0.10×Experience 
            + 0.10×PlayerDevelopment 
            + 0.10×Leadership 
            + 0.05×OrgPhilosophy 
            + 0.05×CandidateInterest
```

**Each term is REAL and MODELED:**
- **CoachingAbility:** Coach's overall rating (40-99 scale)
- **SchemeFit:** Can OC's offensive philosophy match this QB's strengths? Can DC match opponent styles?
- **RosterQualityMatch:** How does candidate's success history correlate with roster talent levels?
- **Experience:** HC experience, years in role, breadth
- **PlayerDevelopment:** QB dev (for OC), defensive player dev (for DC)
- **Leadership:** Can manage difficult personalities, player relationships, locker room culture
- **OrgPhilosophy:** Owner's style, franchise identity
- **CandidateInterest:** Will this coach actually take the job? (see 4.4)

### 4.4 Candidate Interest

A coach doesn't automatically accept every offer.

**Candidate rejects if:**
- Roster is too weak (HC won't inherit a doomed team)
- Team has very high OwnerWinPressure (high early-firing risk)
- Recent HC turnover indicates instability
- Job is interim-only (major college HCs will NOT accept this)
- Scheme conflict is severe

**Candidate accepts if:**
- Roster is competitive
- Owner has reasonable patience
- Real HC/OC opportunity (not a demotion)
- Long-term security

---

## 5. Appointment Types

When hired, a coach gets one of these designations:

- **Permanent:** Full-season multi-year commitment
- **Interim:** Mid-season replacement, low permanent-retention probability (will be evaluated at season's end)
- **Acting:** Temporary within a game or week, rare
- **TemporaryPromotion:** Elevated from staff with explicit understanding it's temporary

**Interim HC Special Handling:**
- Promoted interim HC has reduced authority to make long-term staff changes (can't fire DC and hire from outside mid-season)
- At season's end: performance eval determines permanent vs. open search
- Interim who finished 7-2 after inheriting 3-5 probably becomes permanent
- Interim who finished 3-14 probably doesn't

---

## 6. New HC Effect

When a new HC is hired:

- Existing coordinators become **immediately vulnerable**
- New HC likely replaces 1-2 coordinators (typically 50-70% replacement probability)
- Retained coordinators get slight temporary protection (they "survived the cut")
- New HC's personal JSS history doesn't transfer (blank slate)
- **OwnerWinPressure DOES transfer** (it's a franchise property, not personal to the fired HC)

---

## 7. Coordinator-Specific Logic

### 7.1 OC Firing

Fires when:
- Offense ranks 25th+ league-wide AND expectation was better
- QB development metrics poor AND team has good QB prospect
- 2-3 consecutive weeks of 20%+ below-expected offensive performance
- HC attempting to save own job (scapegoat)

### 7.2 DC Firing

Same as OC, but for defense:
- Defense ranks 25th+ AND expectation was better
- 2-3 consecutive weeks of 20%+ below-expected defensive performance
- Repeated catastrophic unit failures

### 7.3 ST Firing

Different threshold — **catastrophic failures only:**
- Multiple blocked kicks in one season
- Return TDs allowed (rare but catastrophic)
- Repeated missed FGs (if kicker changes mid-season, ST coordinator shares blame)
- Repeated punt-return disasters

One bad kick ≠ firing. Pattern of failures does.

---

## 8. Coach Free-Agent Pool Seeding

**Source:** Top_100_Football_Coaching_Candidates.xlsx (converted to structured data)

**Pool Categories:**
1. **Current NFL HCs** (32)
2. **Current NFL OC/DC/ST** (95)
3. **Current NFL AC** (305+)
4. **Unemployed/Fired NFL Coaches** (built from fired coach history)
5. **College Coaches** (Power Five/Group of Five/FCS, pre-loaded from seed)

**Ratings Algorithm:**
- Current NFL coaches: Use salary_aav percentile within role tier (anchors to real data)
- College coaches: Derive from program prestige + real history + background description
- Fired NFL coaches: Last known rating, decay over years out of work

**Pool Management:**
- When HC fires, HC becomes free agent
- When OC/DC/ST fires, coordinator becomes free agent
- AC typically not moved to FA (most ACs don't leave voluntarily)
- Hired coaches **leave** the FA pool and enter their team's staff
- Retired coaches (age-based R3c) vacate but don't enter FA pool

---

## 9. In-Season vs. Offseason Hiring

### 9.1 In-Season (Weeks 5+)

- Interim HC almost always promoted from inside (stability, no mid-season system change)
- Coordinator replacement: internal promotion favored, external only if no internal option
- Temporary appointment type is common
- Pool restrictions apply (week 5 vs. week 13 changes timing pressure)

### 9.2 Offseason

- Full market opens (internal + external)
- Permanent appointments normal
- Can bring in college coaches (they won't take interim jobs)
- Full multi-team competition for top candidates
- Long-term contracts negotiated

---

## 10. AI Hiring Logic Flow

Every offseason + (after each game if JSS threshold triggers):

```
FOREACH AI TEAM:
  FOREACH COACH (HC, OC, DC, ST, AC):
    Calculate JSS
    Calculate Firing Probability
    IF firing_probability > rand(0, 1):
      FIRE COACH
      Generate internal candidate list
      Calculate InterimPromotionScore for each
      IF best_internal_score > threshold:
        Promote internally (interim)
      ELSE:
        Search external pool
        Score all candidates
        Evaluate candidate interest
        Hire best-interested candidate
      Update team staff
      Recalculate team expectations
```

---

## 11. User Team Hiring (Manual Controls)

**Staff Page Hire/Fire/Promote Buttons:**

- **Fire HC/OC/DC/ST:** Opens confirmation + shows replacement options (2-3 top candidates, reason to hire each)
- **Promote AC → OC/DC/ST:** Confirmation + shows which ACs are qualified
- **Hire External:** Shows FA pool filtered by role, searchable by name/background/ratings
- **Extend Contract:** Re-negotiate for improved terms to reduce JSS volatility

**Constraints:**
- Can't hire a coach already employed elsewhere (they'd have to be fired first)
- College HC won't accept interim-only role (must offer permanent HC or full coordinator role)
- Can't field team without HC (game won't simulate)

---

## 12. Emergent Narratives the System Should Produce

1. **Patient owner + improving team:** 6-11 → 7-10 → 8-9. Coach survives despite losing record.
2. **Impatient owner + strong roster:** 12-5 → 9-8 → 7-10. Coach fired despite better record than some survivors.
3. **Rebuilding success:** Expected 4 wins, actual 6. JSS improves despite losing record.
4. **Repeated playoff failure:** Makes playoffs 3 years, loses early every time. Pressure accumulates → firing.
5. **Super Bowl hangover:** 13-4 → 8-9 (next year). Coach usually survives (recent success buffer).
6. **Coordinator scapegoat:** Offense terrible, DC/ST fine. OC gets fired, HC survives. (Unit-based blame allocation.)
7. **New HC turnover:** New HC fires both coordinators, hires own staff. Realistic completely-new-system scenario.
8. **Interim success:** HC fired week 9 (3-6 record), interim OC takes over, finishes 7-2. Interim becomes permanent HC.
9. **College coach transition:** Big-school college HC joins as OC, proves himself, gets HC opportunity next year.
10. **Fired HC rehired elsewhere:** Fired coach goes to FA pool, gets hired by different team, succeeds.

---

## 13. Testing Scenarios (20 Required Unit Tests)

See ROADMAP.md §4d for the full list. Each scenario has explicit expected outcomes:

1. Low-expectation team significantly exceeds expectations
2. High-expectation team significantly underperforms
3. Patient owner + improving team
4. Impatient owner + declining team
5. Super Bowl winner follows with mediocre season
6. Super Bowl winner has two consecutive bad seasons
7. Coach underperforms for three consecutive seasons
8. Poor offense causes OC firing but HC survival
9. Poor defense causes DC firing but HC survival
10. Repeated special-teams disasters cause ST firing
11. New HC replaces both coordinators
12. New HC retains one coordinator
13. Strong roster + repeated playoff failure
14. Weak roster + improving record
15. Single catastrophic loss does not automatically fire HC
16. Rare in-season HC firing (only under extreme circumstances)
17. Coordinator mid-season firing after repeated catastrophic failures
18. Firing HC does not reset franchise OwnerWinPressure
19. New HC does not inherit previous HC's JSS
20. Recent championship protection decays after continued poor performance

---

## 14. Calibration Target

**NFL HC Firing Data (2021-2025):**
- Total firings: 37 across 5 seasons
- Average: 7.4 per season
- Range: 5-9 per season

**Target this system produces:** ~6-9 HC firings per season (realistic variation)

**Coordinator Turnover:**
- Target: ~12-16 OC/DC changes per season
- Natural variation acceptable (12-20 range OK)

**Testing:** Run 10,000-season calibration (or smaller if time-prohibitive) to verify statistical targets are met. Adjust firing probability formula slope/threshold if needed.

---

## 15. What's NOT in Scope (Disclosed)

- Multi-team AI bidding wars (single deterministic verdict per offer)
- Coach salary cap (no such cap exists in real NFL)
- Complex mood-meter / multi-round patience (single ACCEPT/REJECT/COUNTER per offer)
- Hiring salary negotiation (coaches accept/reject based on Hiring Merit + interest, not salary haggling)
- Trade-backs (coach fired, then re-hired by same team same season — can happen but not optimized for)

---

## 16. Implementation Notes

**Key Files (existing, to integrate):**
- `app/models/coach.py` — add `job_security_score`, `owner_patience` fields; modify JSS calculation
- `app/services/coach_records.py` — enhance JSS computation; add OwnerWinPressure tracking
- `app/main.py` — add Staff page route; add Hire/Fire/Promote controls (user team only)
- `app/templates/staff.html` — add job performance box; add coaching controls

**New Files:**
- `app/engine/coach_hiring.py` — FiringProbability, HiringMerit, InterimPromotionScore
- `app/engine/coach_replacement.py` — Replacement logic, candidate pool, matching
- `app/services/coach_pool.py` — FA pool management, seeding, pool queries
- `scripts/seed_coach_pool.py` — One-time script to parse Excel and populate initial FA pool

**Tests:**
- 20+ unit tests for each narrative scenario
- 10,000-season calibration simulation (or smaller)
- Integration tests for user team hire/fire workflow

---

## 17. User-Visible Changes

**Staff Page (enhanced):**
- Real HC/OC/DC/ST/AC roster with real ratings and backgrounds
- **Job Performance Box** shows each coach's JSS (0-100 dial), updated weekly
- **Hire/Fire/Promote buttons** for user team only (AI teams handle their own)
- **Coach Cards** show full background, ratings, tenure, JSS history
- **Recruitment Interface** shows FA pool candidates, reason each is recommended

**Dashboard:**
- COTY award (already live from R3c)
- Coaching staff strength indicators (already live from R3c)

**No breaking changes to existing systems** (contracts, FA, trades, etc.)

---

END SPECIFICATION. Ready for implementation prompt.
