# R3d Design Review Summary — September 12, 2026

**Status: DESIGN COMPLETE. IMPLEMENTATION READY.**

---

## What Happened

You provided comprehensive guidance on building the coach hiring/firing/promotion market (R3d). Over this chat, we:

1. **Reviewed existing systems** — JSS (partial, stub), Coach entity (R3c, done), free agency (R4b, done), contracts (R4a, done)
2. **Identified conflicts** — discovered that "coach firing was uncertain" was actually resolved by THIS design (you DO want it)
3. **Designed the complete system** — multi-factor JSS, franchise-level OwnerWinPressure, probabilistic firing, replacement logic, FA pool seeding
4. **Created comprehensive specification** — 17-section R3d specification document covering all mechanics, algorithms, edge cases, testing scenarios
5. **Created implementation prompt** — ready to paste into a new chat to build the system

---

## What You Get

### Three New Documents

1. **docs/R3d_COACHING_SYSTEM_SPECIFICATION.md** (16KB)
   - Complete, detailed design specification
   - All formulas, algorithms, decision trees
   - 20 testing scenarios (what narratives should emerge)
   - Calibration targets (6-9 HC firings per season, 12-16 coordinator changes, etc.)
   - Settled decisions (no re-opening of design choices)
   - Scope cuts explicitly listed (multi-team bidding wars, salary negotiation, salary caps)

2. **R3d_IMPLEMENTATION_PROMPT.txt** (4KB)
   - Copy-paste ready for a new Claude Code session
   - Lists what to read first (HANDOFF.md, ROADMAP.md, spec)
   - Clear implementation order (JSS → OwnerWinPressure → Firing Prob → Replacement → Pool → AI → UI)
   - Expected deliverables
   - Scoring targets

3. **Memory file: project_r3d_design_complete.md**
   - Captured all key design decisions
   - Future reference for what was decided and why

### Updated Memory Index

- Updated MEMORY.md to reflect R3d is now designed
- Resolved the "JSS is uncertain" question — it's no longer uncertain; Brian wants the system and it's been fully designed

---

## Key Design Decisions Made

### Architecture

| Component | Decision | Rationale |
|---|---|---|
| **JSS Formula** | Multi-factor (Win 25%, ExpDelta 30%, Playoff 15%, Trajectory 10%, Blowouts 10%, Owner 10%) | Context-aware firing, not just wins |
| **OwnerWinPressure** | Franchise-level, persistent, 20-90 range, annual adjustment | Accumulates pressure over years; doesn't reset when HC fires |
| **Firing Probability** | Probabilistic model with logistic function, not deterministic thresholds | Same JSS can produce different outcomes based on context |
| **In-Season Gates** | HC: 0.05× (weeks 1-4), 0.25× (weeks 5-8), 0.60× (weeks 9-12), 1.00× (weeks 13-18) | Early firings extraordinarily rare; more plausible later |
| **Replacement Logic** | Separate from firing; two-part (internal promotion score + external hiring merit) | Avoids unrealistic "perfect replacement in October" scenarios |
| **Interim vs. Permanent** | Explicit appointment types; interim evaluated at season's end | Produces realistic "interim becomes permanent" narratives |
| **Coordinator Autonomy** | Can fire independently of HC if unit underperforms | Realistic coordinator turnover; HC can survive if coordinators are the problem |
| **Coach FA Pool** | Seeded from real coaches (Excel file); college coaches rated LOWER than NFL | Prevents fabricated narratives; keeps NFL coaches competitive |
| **College HC Constraint** | Big-school college HC won't accept interim or assistant roles | Realistic — top college coaches have pride |
| **AI Autonomy** | All 31 non-user teams autonomously hire/fire/promote | User controls only their own team (manual buttons) |

### Calibration Targets

- **HC Firings:** ~6-9 per season (NFL 2021-2025: 7.4 average)
- **Coordinator Changes:** ~12-16 per season
- **Realistic tenure distribution** — not all coaches fired, not all survive
- **Probabilistic outcomes** — identical JSS produces different results based on context

---

## What's NOT in R3d (Disclosed Scope Cuts)

- Multi-team AI bidding wars (single deterministic verdict, like R4)
- Coach salary negotiation (accept/reject based on merit + interest only)
- Coach salary cap (real NFL has none)
- Hiring salary negotiation complexity (no haggling)

---

## Implementation Checklist (For Next Chat)

When you start the implementation chat, you'll need to:

- [ ] Read HANDOFF.md (context on how this project works)
- [ ] Read ROADMAP.md (what's been built, what order to work in)
- [ ] Read GDD_v3.2.md Sections 8.2.3, 8.3.3, 8.4, 7.9 (relevant specs)
- [ ] Read docs/R3d_COACHING_SYSTEM_SPECIFICATION.md (the full design you'll build)
- [ ] Understand how AI teams autonomously run coaching every offseason
- [ ] Understand interim vs. permanent appointment is a real mechanic
- [ ] Design new files needed (coach_hiring.py, coach_replacement.py, coach_pool.py)
- [ ] Enhance existing files (coach_records.py for enhanced JSS, main.py for Staff page controls)
- [ ] Implement in order: JSS → OwnerWinPressure → Firing Prob → Replacement → Pool → AI → UI
- [ ] Test each piece before moving on
- [ ] Run 20 scenario tests (emergent narratives)
- [ ] Run 10K-season calibration (verify stats targets) OR smaller if time-prohibitive

---

## What's Working Now (Don't Change)

- Coach entity (R3c) — fully working, all ratings, all progression
- JSS computation (partial, stub formula) — exists, can be enhanced
- Staff page (R3c) — renders coaches, stats, cards
- Free agency system (R4b) — players, works fine, R3d just adds coaches
- Contracts (R4a) — player contracts, coach contracts will use same system

---

## Open Questions (All Resolved)

✅ **Where does OwnerWinPressure live?**  
→ Team/Franchise entity, persistent across seasons

✅ **How is JSS history stored?**  
→ Weekly (or sampled) on Coach entity; stored per-season in CoachSeasonStats

✅ **Do coordinators get independent JSS?**  
→ Yes, each role (HC/OC/DC/ST/AC) has its own formula

✅ **How are college coaches seeded?**  
→ From Excel file; rated by program prestige + background + real history, always lower than current NFL HCs

✅ **What's the firing probability model?**  
→ Multi-factor logistic function, not hard thresholds

✅ **Can a coordinator be fired without firing the HC?**  
→ Yes, explicitly. Poor unit performance can trigger coordinator firing; HC survives if other units are fine.

✅ **Who makes coaching decisions for AI teams?**  
→ Autonomous; algorithm runs every offseason and after each game

✅ **What does the user control?**  
→ Only their own team; manual Hire/Fire/Promote buttons on Staff page

---

## Files Modified / Created

### Modified
- `app/models/coach.py` — add JSS fields
- `app/services/coach_records.py` — enhance JSS formula; add OwnerWinPressure tracking
- `app/main.py` — Staff page route; AI autonomy loop
- `app/templates/staff.html` — job performance box; coaching controls
- ROADMAP.md — add R3d section
- GDD_v3.2.md — update Sec 8.2.3

### New
- `docs/R3d_COACHING_SYSTEM_SPECIFICATION.md` — full spec (created 2026-09-12)
- `app/engine/coach_hiring.py` — FiringProbability, HiringMerit
- `app/engine/coach_replacement.py` — Replacement logic, candidate matching
- `app/services/coach_pool.py` — FA pool management
- `scripts/seed_coach_pool.py` — One-time seed script from Excel
- `tests/test_coach_hiring.py` — 20 scenario tests + calibration

---

## Next Steps

**You now have everything needed to implement R3d in another chat.**

Copy the **R3d_IMPLEMENTATION_PROMPT.txt** into a new Claude Code session. That session will:
1. Read the specification
2. Design the architecture
3. Implement in stages
4. Test thoroughly
5. Calibrate against NFL data
6. Ship it

**The design is complete and settled. No further design work needed.**

---

End of summary.
