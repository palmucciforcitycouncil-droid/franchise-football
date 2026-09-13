---
name: R5 Draft System Specification
date: 2026-09-12
scope: Design + Implementation Plan
---

# R5: Draft System Specification

**Depends on:** R4a (rookie contracts exist) ✓
**Status:** Design Phase
**Target:** Two implementation sessions (R5b core + R5c UI)

---

## 1. Overview

The Draft system provides a 7-round annual rookie class injection, deterministically generated at league seed. Each `LEAGUE_SEED` produces a **unique draft class size (235-265 prospects) and positional breakdown** (within configurable bands), ensuring variety across leagues while maintaining reproducibility. The `/draft` page allows teams to:
1. View prospects (all 250 generated rookies)
2. Build a personal draft board (shortlist up to 35-50)
3. See their own picks across 7 rounds
4. Simulate draft picks one at a time
5. (Future R5.1) Make live pick decisions + trade picks during the draft event

---

## 2. Data Model & Generation

### 2.1 Prospect & Undrafted Rookie Entities

```python
class Prospect:
    prospect_id: str              # Deterministic ID per DRAFT_SEED
    name: str                     # Seeded generation
    college: str                  # Seeded from real college pool
    position: str                 # Quota-sampled (QB/RB/WR/TE/OL/DL/LB/CB/S/K/P)
    
    # Attributes (0-99 scale, derived from position-specific formulas)
    overall: int                  # Derived from position-weighted attr formula
    potential: int                # Ceiling rating (OVR + seeded noise, max 99)
    speed: int
    strength: int
    agility: int
    throw_power: int              # (if QB-group)
    throw_accuracy: int           # (if QB-group)
    catch: int
    tackle: int
    
    # Physical
    height: int                   # inches
    weight: int                   # lbs
    
    # Metadata
    draft_grade: str              # "A" / "B" / "C" / "D" (derived from OVR band)
    scouting_noise: dict          # Per-team noise applied to this prospect
    acquired_by: str | None       # team_abbr once drafted (None if undrafted)
    draft_round: int | None       # 1-7 once drafted (None if undrafted)
    draft_pick: int | None        # Overall pick number 1-224 once drafted (None if undrafted)
```

**Undrafted Flow:** Prospects with `acquired_by=None` at end of draft are converted to `UndraftedRookie` entries and added to FA pool.

```python
class UndraftedRookie:
    # (Inherits from Player or is a Player with special flags)
    player_id: str                # Will become a real Player if signed
    name: str                     # From original Prospect
    college: str                  # From original Prospect
    position: str
    
    # All attributes inherited from Prospect
    overall: int
    potential: int
    # ... (8 attributes as per Prospect)
    
    # Undrafted-Specific
    years_remaining: int          # 1-3, decrements each offseason, deletes at 0
    acquired_via: str = "UNDRAFTED"
    team_abbr: None               # Will be set if signed
    salary: int                   # League minimum (or negotiated)
    contract_years_remaining: int # Typically 1 (can be extended on signing)
```

### 2.2 Prospect Generation Algorithm

**Timing:** Generated fresh once per league at season initialization (new `season.draft_class`), NOT re-rolled per season. Each new `LEAGUE_SEED` produces a different class size and composition.

**Process:**

1. **Class Size Band:** 235-265 prospects (draws from a band, not fixed at 250)
   - Actual size seeded on `stable_seed(LEAGUE_SEED, "draft", "class_size")` → generates random int in [235, 265]
   - Buffer for trades/drops remains implicit (any size in band works)

2. **Position Quota Bands:** Each position drawn from a band based on real NFL 10-year data (2017-2026), scaled to 1.224x for 300-prospect class size. Total sums to class_size.

**Real NFL 10-Year Averages (Basis):**
| Position | Min | Max | Avg |
|----------|-----|-----|-----|
| QB | 9 | 14 | 11.5 |
| RB | 16 | 25 | 20.2 |
| WR | 27 | 37 | 32.8 |
| TE | 11 | 16 | 13.5 |
| OT | 18 | 26 | 22.4 |
| iOL (C/G) | 18 | 25 | 21.6 |
| EDGE | 22 | 31 | 26.5 |
| iDL | 17 | 24 | 20.1 |
| LB | 19 | 28 | 23.3 |
| CB | 26 | 36 | 31.0 |
| S | 14 | 22 | 18.2 |
| K/P/LS | 2 | 6 | 3.8 |
| **TOTAL** | **199** | **290** | **245** |

**Scaled to 300-Prospect Class (×1.224):**
   - QB: **10-17** (avg 14)
   - RB: **20-31** (avg 25)
   - WR: **33-46** (avg 40)
   - TE: **13-21** (avg 16.5)
   - OT: **22-32** (avg 27)
   - iOL (C/G/T): **22-31** (avg 26)
   - EDGE: **27-38** (avg 32.5)
   - iDL: **21-29** (avg 25)
   - LB: **23-34** (avg 29)
   - CB: **32-44** (avg 38)
   - S: **17-27** (avg 22)
   - K/P/LS: **2-7** (avg 5)
   - **Expected Total: 280-320 (midpoint ~299)**
   
   Algorithm:
   - Draw class_size first (seeded)
   - For each position in order, draw from its band (seeded per position)
   - After final position, adjust that position's count to make total = class_size (ensures exact sum)

3. **Per-Prospect Generation:** Seeded on `stable_seed(LEAGUE_SEED, "draft", prospect_index)`:
   - **Name:** Procedurally generated from a syllable-pool (first + last, deterministic seeded draw).
   - **College:** Random from ~130 real FBS colleges (deterministic seeded draw)

4. **Class Strength Band (QB-specific variance):**
   
   Each year's draft class QB composition is drawn seeded per `stable_seed(LEAGUE_SEED, "draft", "class_strength")`:
   
   **Real NFL Pattern (9-14 QBs/year):**
   - **Elite QB Year (~25%):** 13-14 QBs drafted (multiple premium Round 1 picks), distribution skews high (3-4 QBs OVR 85+)
   - **Strong QB Year (~50%):** 11-12 QBs drafted (solid 1-2 Round 1 prospects), distribution normal (1-2 QBs OVR 85+, several 75-84)
   - **Weak QB Year (~25%):** 9-10 QBs drafted (few premium picks, mostly Day 3 depth), distribution skews low (0-1 QBs OVR 85+, most 60-75)
   
   **Mechanism:** 
   1. Draw "class_strength" (0-100) seeded per LEAGUE_SEED
   2. Map to year type: 0-25 → Weak, 26-75 → Strong, 76-100 → Elite
   3. QB band adjusts: Weak uses 9-10 QBs, Strong uses 11-12, Elite uses 13-14
   4. Individual QB base talents seeded within distribution, ensuring realistic variation
   
   **Result:** Matches real NFL (9-14 range), with some years producing elite talent classes and others producing thin QB pools.

5. **Attribute Generation (Position-Specific Formulas):**

   Attributes are **NOT uniform random**, but derived from position-specific formulas. Each prospect's eight attributes are generated seeded per `stable_seed(LEAGUE_SEED, "draft", prospect_index, attribute_name)`:

   **Base Formula:**
   - Draw a base talent level (0-99 scale) per prospect, seeded
   - Each attribute is: Base + Position_Offset + Seeded_Variance (capped)
   - Variance per attribute (typical): ±10 to ±20, ensuring realistic profiles

   **Examples:**

   *WR with Base Talent = 75:*
   - SPD: 75 + 0 ± 12 = ~75-87 (speed is core)
   - AGI: 75 - 5 ± 15 = ~55-85 (wide variance)
   - CTH: 75 + 5 ± 10 = ~70-90 (heavy emphasis)
   - STR: 75 - 15 ± 12 = ~48-72 (much lower)
   - Result: realistic WR profile (fast, catchable, weak)

   *QB with Base Talent = 78:*
   - SPD: 78 - 10 ± 12 = ~56-80 (less mobile)
   - STR: 78 + 5 ± 10 = ~73-93 (arm strength valued)
   - TPW: 78 + 8 ± 8 = ~78-94 (throw power core)
   - TAC: 78 + 3 ± 15 = ~66-96 (wide variance — some accurate, some wild)
   - Result: realistic QB variation (strong arm, inconsistent accuracy)

6. **Overall Rating (Derived):**
   - Formula: Position-weighted average of key attributes
   - Example: WR_OVR = SPD×0.28 + AGI×0.28 + CTH×0.32 + STR×0.12
   - Distribution is **banded per class strength** (not fixed 72 mode)
   - Elite QB year → QB OVRs lean higher; Weak year → QB OVRs lean lower

7. **Potential Rating:**
   - Formula: Overall + seeded ceiling noise (±0 to +20), capped at 99
   - Interpretation: Rookie's max development by age 26

8. **Height/Weight:** Deterministic range per position (WR: 5'10"-6'4", 180-220 lbs, etc.)

9. **Draft Grade:** Derived from OVR band:
   - A: 85-99
   - B: 70-84
   - C: 55-69
   - D: 40-54

10. **Scouting Noise (Per-Team Variance):**
    Each team sees a different noise-perturbed view of each prospect's attributes, **but NOT their OVR** (OVR is league-consensus). Noise reseeded per `stable_seed(LEAGUE_SEED, "draft", prospect_index, team_abbr)`:
    - Each attribute: **±0-4 point noise** (tight uncertainty; scout views don't diverge wildly)
    - Noise is pre-computed and stored in `Prospect.scouting_noise` dict per team
    - **Disclosed on the UI:** "Your scouting view differs from league consensus" when noise differs materially from OVR

---

## 2.3 Rookie Scale AAV (DECIDED: Simplified + Cap Correlation)

**Approach:** Simplified game-scale base table (tuned to $720M season-1 cap), with **automatic annual scaling tied to league salary cap growth**.

**Base Table (Season 1, $720M cap):**

| Round | Pick 1-8 | Pick 9-16 | Pick 17-24 | Pick 25-32 |
|-------|----------|----------|----------|----------|
| 1     | $8.0M    | $6.0M    | $4.5M    | $3.5M    |
| 2     | $3.0M    | $2.2M    | $1.8M    | $1.5M    |
| 3     | $1.2M    | $1.0M    | $0.9M    | $0.8M    |
| 4     | $0.7M    | $0.6M    | $0.55M   | $0.5M    |
| 5     | $0.5M    | $0.45M   | $0.4M    | $0.35M   |
| 6     | $0.35M   | $0.3M    | $0.28M   | $0.25M   |
| 7     | $0.25M   | $0.22M   | $0.2M    | $0.18M   |

**Cap Correlation (NEW):**

Rookie scale AAV grows **automatically each offseason** proportional to cap growth:

```
Season N Rookie AAV = Base_Table_Value × (Current_Season_Cap / $720M)
```

**Example:**
- Season 1 (cap $720M): Pick #1 = $8.0M × (720/720) = **$8.0M**
- Season 2 (cap $774M, +7.5% growth): Pick #1 = $8.0M × (774/720) = **$8.6M**
- Season 3 (cap $832M, +7.5% growth): Pick #1 = $8.0M × (832/720) = **$9.2M**

This ensures rookies stay competitive with veteran contracts as the league grows.

**League Minimum:** $885K in season 1, also scales with cap growth.

**Contract Length:** 
- **Drafted rookies:** 4-year contracts (standard rookie deals)
- **Undrafted rookies:** 1-year contracts (can be extended on re-signing)

**Disclosure on UI:** "Draft pick salary is game-balanced and scales with league cap growth."

---

## 2.4 Game Calendar / Season Flow (DECIDED)

**After Season 1+ ends, the calendar is:**

1. **Playoffs** (simulated, bowl games complete)
2. **Coaching Staff Market** (R3d: Hiring, firing, promotions happen here)
3. **Contract Renewals** (R4a: Release expired contracts, renew existing players)
4. **Free Agent Market** (R4b: FA signings, bidding, offers)
5. **Draft** (R5: This chapter — all picks simulated)
6. **Preseason** (R10: Small exhibition slate, builds Week 1 stats)
7. **Regular Season** (18 weeks, 32 teams)
8. **Playoffs** (repeat)

**Trading Window:** 
- Trading is **allowed only after Playoffs end** (step 1 completes)
- Disabled during coaching hires/contract renewals/FA/draft/preseason/regular season

**New Season Start:** After Playoffs complete, new season begins immediately (before step 2 coaching market)

**Implication for R5:**
- Draft happens AFTER contract expirations are cleared
- Draft happens AFTER all coaching decisions are made (new coaches can immediately use draft picks)
- Draft happens BEFORE preseason (no time to build preseason momentum with new rookies — they start Week 1 cold)

---

## 3. Pick Order & Draft Schedule

### 3.1 Draft Order Determination

**Timing:** Computed once, right after `archive_season()` completes (team records are final).

**Algorithm:**
1. Rank by prior season's record (worst to best)
2. **Tiebreaker 1:** Strength of Schedule (SOS) — lower SOS wins (weaker schedule = worse team)
3. **Tiebreaker 2:** Conference Record (fewer wins)
4. **Tiebreaker 3:** Seeded coin flip (`stable_seed(LEAGUE_SEED, season, "draft_tiebreak", team_abbr_a, team_abbr_b)`)

**Result:** A static `DraftOrder` row (team_abbr, rank 1-32) stored once and used for all 224 picks.

### 3.2 Draft Phases

- **Preseason:** Draft class exists and is viewable by all teams, but no picks happen
- **Offseason (Week 1-7):** Teams can build draft boards (prep phase)
- **Draft Week (Week 0.5 or special event):** TBD (R5.1 feature; for now, simulate all picks instantly in `reset_season()`)

---

## 4. DraftPick Entity

```python
class DraftPick:
    draft_pick_id: str            # Composite (season, round, overall_pick)
    season: int
    round: int                    # 1-7
    overall_pick: int             # 1-224
    team_abbr: str
    
    prospect_id: str              # FK to Prospect
    pick_order_rank: int          # 1-32 (team's position in this round)
    
    made_at: datetime | None      # When the pick was made (None if simulated all at once)
    
    # Pick Value (for trade purposes)
    pick_value: float             # From pick-value chart (see § 4.1)
```

### 4.1 Pick Value Chart

**Source:** Simplified chart (not real NFL pick value chart, designed for this game's scale).

**Purpose:** Used in trade evaluation (R4c) to price draft picks.

**Table (example, to be tuned):**

| Round | Pick 1-8 | Pick 9-16 | Pick 17-24 | Pick 25-32 |
|-------|----------|----------|----------|----------|
| 1     | 3000     | 2200     | 1800     | 1400     |
| 2     | 1000     | 800      | 600      | 500      |
| 3     | 400      | 300      | 250      | 200      |
| 4     | 150      | 120      | 100      | 80       |
| 5     | 60       | 50       | 40       | 30       |
| 6     | 25       | 20       | 15       | 10       |
| 7     | 8        | 6        | 4        | 2        |

**Implementation:** Hardcoded table in `app/engine/draft.py` or a CSV loaded at startup. Values are **disclosed as a game-balance simplification**, not a real NFL claim.

---

## 5. Draft Board (Personal Shortlist)

### 5.1 DraftBoard Entity

```python
class DraftBoard:
    team_abbr: str
    board_id: str                 # Composite (team_abbr, season)
    
    board_slots: list[DraftBoardSlot]  # Ordered list
    
    # Metadata
    created_at: datetime
    last_updated_at: datetime
    class_size: int               # Total draft class size this year (235-265)
```

```python
class DraftBoardSlot:
    slot_index: int               # 1-50 (position on board, soft limit)
    prospect_id: str
    
    note: str | None              # Optional personal note
    tier: str | None              # "Must Have" / "Target" / "Value" / etc. (optional badges)
```

### 5.2 Board Operations

- **Add to Board:** `POST /draft/{team_abbr}/board` with prospect_id → appends to end
- **Reorder:** `POST /draft/{team_abbr}/board/reorder` with new slot order → moves prospect up/down
- **Remove:** `DELETE /draft/{team_abbr}/board/{prospect_id}`
- **View:** `GET /draft/{team_abbr}/board` → returns ordered list

**Capacity:** 50 slots max per team (soft limit, not enforced hard — UI shows "X/50")

---

## 6. UI Layout & Pages

### 6.1 `/draft` Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ NE · New England Patriots | Record: 10-7 | Power Rank: 8th     │
├─────────────────────────────────────────────────────────────────┤
│ Dashboard | Roster | Staff | GM Desk | Draft | Playoffs | ... │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ┌──── TEAM PICKS (7) ────┐  ┌─── TEAM NEEDS ───┐              │
│ │ R1 Pick #9  │ R2 Pick #33 │ WR | CB | OL | DL               │
│ │ R1 Pick #17 │ R2 Pick #41 │ LB                               │
│ │ R1 Pick #25 │ R2 Pick #49 │                                  │
│ │             │ R2 Pick #57 │                                  │
│ └────────────────────────┘  └──────────────────┘              │
│                                                                   │
│ ┌─ DRAFT RESULTS ─┐        ┌──── PROSPECTS (250) ────────────┐ │
│ │ Pause  "You're  │        │ Draft Year: 2025 [2026][2027]   │ │
│ │        on the   │        │ Select up to 5 to compare       │ │
│ │        clock"   │        │                                  │ │
│ │ Pick #5         │        │ [ALL 250] [OFF 132] [DEF 118]   │ │
│ │                 │        │ QB 26 | RB 22 | WR 27 | ...     │ │
│ │ [1][2][3][4]... │        │                                  │ │
│ │                 │        │ [Search: name, POS, college]    │ │
│ │ Sim to Next     │        │                                  │ │
│ │ Pick            │        │ ┌─────────────────────────────┐ │ │
│ │                 │        │ │ Darius Johnson · QB (99 OVR) │ │ │
│ │ [Pick Order]    │        │ │ POT: 99 | SPD: 81 | STR: 92  │ │ │
│ │ 1. NE           │        │ │ H: 6'2"  W: 220 lbs  Age: 21 │ │ │
│ │ 2. KC           │        │ │ [Add to Board] [+Compare]    │ │ │
│ │ 3. SF           │        │ │ └─────────────────────────────┘ │ │
│ │ ...             │        │ [Next prospect...]                │ │
│ │                 │        │                                  │ │
│ └─────────────────┘        └──────────────────────────────────┘ │
│                                                                   │
│ ┌──────── DRAFT BOARD (5) ──────────┐                           │
│ │ 1. Darius Brown (S, 99 OVR)  [⋮]  │                           │
│ │ 2. Tyler Johnson (CB, 99)    [⋮]  │                           │
│ │ 3. Jaylen Brown (LB, 99)     [⋮]  │                           │
│ │ 4. Jaylen Williams (LB, 99)  [⋮]  │                           │
│ │ 5. [Empty slot]                   │                           │
│ │                                    │                           │
│ │ [+ Add from Prospects]             │                           │
│ └────────────────────────────────────┘                           │
│                                                                   │
│ ┌──────── ROSTER (sorted by OVR/POT, all draftees) ────────────┐ │
│ │ Player | OVR | POT | SPD | STR | AGI | TPW | TAC | CTH | Age│ │
│ │ ─────────────────────────────────────────────────────────────│ │
│ │ Darius Johnson · QB  │ 99 | 99 | 81 | 92 | 85 | 70 | 99 | 21│ │
│ │ Jordan Jones · DL    │ 99 | 99 | 69 | 75 | 75 | 95 | 81 | 22│ │
│ │ Brandon Davis · S    │ 99 | 99 | 75 | 66 | 94 | 73 | 96 | 21│ │
│ │ [...]                                                          │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Component Details

#### **Team Picks Box**
- Shows all 7 picks for the user's team
- Format: "Round X Pick #N"
- Clickable to jump to that pick in the order list (left panel)
- Color: Gold/yellow if pick is "on the clock" (current pick during draft event)

#### **Team Needs Box**
- Pills showing position groups where the team is below-quota (derived from `roster_strength.py`'s group counts)
- Clicking a need pill filters the Prospects box to that group
- Disclosed as advisory, not a hard constraint ("Your scouting sees needs at...")

#### **Draft Results Box**
- Round tabs (1-6 shown, scrollable for round 7)
- "On the clock" indicator during draft event (hidden in preseason/offseason)
- "Pause" button (during draft only, not visible in preseason)
- "Sim to Next Pick" button (simulates picks until it's the user's team's turn)
- Pick order list (teams 1-32, scrollable)

#### **Prospects Box**
- **Tabs:** "ALL 250", then filtered tabs for each position group
- **Top Row:** Draft year selector (2025, 2026, 2027, 2028) — for now, only current year shows real data
- **Stat Columns:** Player Name | OVR | POT | SPD | STR | AGI | TPW | TAC | CTH | Height | Weight | Age | Draft Grade
- **Per Row Actions:** 
  - Checkbox (select up to 5 for side-by-side compare)
  - "Add to Board" button → appends to the user's draft board
  - Star icon (wishlist, favorite — optional R5.1 feature)
- **Search:** Name, position, college (live client-side filtering)
- **Sorting:** Click column headers to sort (GET params + reload, same pattern as Roster)

#### **Draft Board Box**
- Ordered list of prospects the user has added
- **Per Slot:** Rank number | Player card (mini) | Reorder handle (drag or ⋮ menu for move up/down/remove)
- **Capacity:** Shows "X/50"
- **Empty State:** "No prospects added. Add from the Prospects box →"
- **Buttons:** 
  - "+ Add from Prospects" → modal/dropdown to search and pick
  - Export Board (button, stub for now)

#### **Roster Box (Draft Prospects)**
- Same table as main `/roster` page, but scoped to draft class
- Columns: Player | OVR | POT | SPD | STR | AGI | TPW | TAC | CTH | Height | Weight | Age
- Rows are clickable → opens a Prospect Card (new modal)
- Default sort: OVR descending
- No depth-chart badges (these are draft prospects, not yet rostered)

---

## 7. Prospect Card Modal

```
┌─────────────────────────────────────────┐
│ [Close]  Darius Johnson · QB            │
├─────────────────────────────────────────┤
│ [Overview] [Ratings] [Stats] [Compare]  │
├─────────────────────────────────────────┤
│                                         │
│ **Overview**                            │
│ Draft Grade: A (99 OVR)                │
│ College: Clemson                        │
│ Height: 6'2"  Weight: 220 lbs           │
│ Age: 21                                 │
│                                         │
│ Scouting Report:                       │
│ Elite arm talent with strong mobility. │
│ High ceiling, low floor (raw decision- │
│ maker). Scheme fit varies widely.       │
│ [Your Scouting View differs by ±X pts] │
│                                         │
│ Pick Value (Trade): 3000                │
│ (for a 1st-round pick slot)             │
│                                         │
│ ┌─ Attributes ──────────┐              │
│ │ Overall: 99           │              │
│ │ Potential: 99         │              │
│ │ Speed: 81             │              │
│ │ [... all 8 attrs]     │              │
│ └───────────────────────┘              │
│                                         │
│ [Add to Board] [Compare]                │
└─────────────────────────────────────────┘
```

**Tabs:**
1. **Overview:** College, phys attributes, scouting narrative, pick value
2. **Ratings:** Per-attribute dial charts (0-99), with league-average overlay
3. **Stats:** (Stub: "Coming in R5.1 — college production stats")
4. **Compare:** (Future: side-by-side vs. selected draft board members)

---

## 8. Rookie Contracts & Integration

### 8.1 Rookie Scale (R4a Integration)

**Timeline:** At draft time, each drafted `Prospect` becomes a `Player` with:
- `contract_years_remaining = 4` (standard rookie contract, per GDD §8.1)
- `salary = rookie_scale_aav(round, overall_pick_in_round)`

**Rookie Scale AAV (FINALIZED - Real NFL 2026 Data):**

Based on real Over The Cap 2026 contracts. Annual salary is AAV (Average Annual Value), normalized to single amount per year (no separate signing bonus).

| Draft Pick | Real NFL 2026 AAV | 4-Year Total | Guaranteed/Year |
|---|---|---|---|
| Pick #1 | $13.64M | $54.57M | $13.64M (100%) |
| Pick #2 | $13.03M | $52.10M | $13.03M |
| Pick #10 | $7.40M | $29.61M | $7.40M |
| Pick #32 | $6.93M | $27.72M | $6.93M |
| Pick #33 (R2) | $3.23M | $12.90M | $1.62M (50%) |
| Pick #100 (R3) | $1.45M | $5.80M | $0.44M (30%) |
| Day 3 (R4-7) | ~$1.1M–$1.2M | ~$4.4M–$4.8M | ~$0.36M (30%) |

**Cap Correlation:**
- Rookie AAV scales automatically each year: `AAV × (Current_Cap / $302M)`
- With 7.5% annual cap growth, Pick #1 salary grows from $13.64M (season 1) to ~$14.66M (season 2), ~$15.75M (season 3), etc.
- Maintains rookie competitiveness with veteran salaries as league grows

**Guaranteed:** Real NFL scale shown above; varies by pick (100% for top-10, declining to 30% for late-round)

---

## 9. Pick Simulation & Draft Events

### 9.1 Current Implementation (R5b+c)

For now, all picks are simulated instantly at the start of each new league:

```python
# In season_state.start_new_league():
draft_class = generate_draft_class(LEAGUE_SEED, season=1)
picks = simulate_all_draft_picks(draft_class, draft_order)

for pick in picks:
    prospect = draft_class[pick.prospect_id]
    new_player = Player(
        name=prospect.name,
        college=prospect.college,
        position=prospect.position,
        # ... all attributes from prospect
        contract_years_remaining=4,
        salary=rookie_scale_aav(pick.round, pick.pick_in_round),
        team_abbr=pick.team_abbr
    )
    db.session.add(new_player)
```

**Pick Selection:** Each AI team picks the best-available prospect at their biggest roster need (greedy, deterministic, seeded).

### 9.2 Undrafted Rookies → Free Agent Pool (DECIDED)

**Lifecycle:**

1. **At draft end:** All 280-320 prospects that were NOT drafted by any team are added to the free agent pool as undrafted rookies
   - Typical undrafted count: 75–90 per year (depends on team draft depth vs quality)
   - Status: Available, `years_remaining = 3`
   - Salary: League minimum ($885K) unless negotiated up
   - Can be signed by any team (same as regular free agents)

2. **On signing:** Undrafted rookie becomes a real `Player` with:
   - `contract_years_remaining = 1-2` (typically 1 year for UDFAs, can be extended)
   - `salary = $885K` (league minimum, negotiable upward per R4a)
   - `acquired_via = "UNDRAFTED"`

3. **Annual Cleanup (Age-Weighted Two-Tier):**
   Every offseason (`apply_coach_offseason()` time), prune undrafted FA pool:
   
   - **Tier 1 (Auto-delete):** Remove all UDFAs with `years_remaining = 0` (hard expiration)
   - **Tier 2 (Selective delete):**
     - Delete **bottom 25%** of UDFAs with `years_remaining = 1` (about to expire anyway)
     - Delete **bottom 10%** of UDFAs with `years_remaining = 2-3` (keep younger talent)
   
   **Rationale:** Keeps pool stable without losing good young prospects. Older/worse performers exit naturally. Discourages hoarding UDFAs (only viable to keep good ones).
   
   **Example (300 UDFAs in pool):**
   - Year 3 cohort (100, years_remaining=0): Delete all 100
   - Year 2 cohort (100, years_remaining=1): Delete bottom 25, keep 75
   - Year 1 cohort (100, years_remaining=2-3): Delete bottom 10, keep 90
   - **Pool result after cleanup:** 300 - 135 deleted + 250 new draft class = ~415 UDFAs (equilibrium)

4. **Hard Expiration:** Undrafted rookies MUST be deleted at end of year 3 (auto-delete when `years_remaining` hits 0).

---

### 9.3 Future Work (R5.1 - Live Draft Event)

- User can make their own pick decision during their turn
- AI teams pick autonomously (same greedy algorithm)
- "Pause" the draft, "Resume", "Sim to Next Pick"
- (Even further future: trading picks during the draft)

---

## 10. Routes & Endpoints

### Reads (GET)

| Route | Purpose |
|-------|---------|
| `GET /draft` | Draft page for user's team |
| `GET /api/draft/prospects?year=2025&position=QB` | Prospect search/filter |
| `GET /api/draft/prospect/{id}` | Single prospect data (for modal) |
| `GET /api/draft/picks?team_abbr=NE` | All picks for a team |
| `GET /api/draft/order` | Full draft order (all 32 teams, all 7 rounds) |
| `GET /api/draft/{team_abbr}/board` | User's draft board |
| `GET /api/draft/needs?team_abbr=NE` | Team's positional needs |

### Writes (POST/PUT/DELETE)

| Route | Purpose |
|-------|---------|
| `POST /api/draft/{team_abbr}/board` | Add prospect to board |
| `PUT /api/draft/{team_abbr}/board/reorder` | Reorder board slots |
| `DELETE /api/draft/{team_abbr}/board/{prospect_id}` | Remove from board |
| `POST /api/draft/{team_abbr}/pick` | Make a pick (R5.1 - live draft) |

---

## 11. Database Schema

### Tables to Add/Modify

1. **Prospect** — one per generated draft class (235-265 rows per league, varies by LEAGUE_SEED)
   - `prospect_id`, `season`, `name`, `college`, `position`, `overall`, `potential`, `[8 attributes: speed, strength, agility, throw_power, throw_accuracy, catch, tackle, awareness]`, `height`, `weight`, `draft_grade`, `scouting_noise` (JSON per-team), `acquired_by`, `draft_round`, `draft_pick`

2. **DraftPick** — one per pick slot (varies per league, ~224-240 picks across 7 rounds × 32 teams)
   - `draft_pick_id`, `season`, `round`, `overall_pick`, `team_abbr`, `prospect_id`, `pick_value`, `made_at`

3. **DraftOrder** — 32 rows per league
   - `draft_order_id`, `season`, `team_abbr`, `rank`, `tiebreaker_sos`, `tiebreaker_conf_record`

4. **DraftBoard** — one per team per season (32 rows per league)
   - `draft_board_id`, `team_abbr`, `season`, `board_slots` (JSON array of prospect_id + slot_index + note), `class_size`

5. **Player** (modify existing to track undrafted rookies):
   - Add: `acquired_via` enum (DRAFT, UNDRAFTED, FA, TRADE, EXTENSION) — existing for drafted players and other origins
   - For undrafted rookies: `acquired_via = "UNDRAFTED"`, `years_in_fa_pool = 1-3` (tracks years remaining for undrafted cleanup)

---

## 12. Disclosed Gaps & Scope Cuts

1. **College Stats:** Prospect card shows college name but no real box-score data (tab says "Coming in R5.1")
2. **Multi-Pick Trades:** Can't trade picks during the draft yet (R5.1 feature)
3. **Prospect Comparisons:** "Compare" tab is a stub (R5.1 — side-by-side view vs. draft board members)
4. **Live Draft Event:** All picks simulated at league init; no paused draft, no live "on the clock" experience (R5.1)
5. **Scouting Report Text:** Narratives are stubs ("Elite arm talent with strong mobility...") — a real LLM-generation candidate for R9 (Headlines), not built here
6. **Comp Players:** No "NFL comp" player comparable to a prospect (would need a real source or LLM generation)

---

## 13. Implementation Plan

### R5a: Design (THIS DOCUMENT + Figma review) ✓

### R5b: Core Engine (2-3 hour session, Sonnet)

**Key Files:**
- `app/models/prospect.py` (new) — Prospect entity + schema
- `app/models/draft.py` (new) — DraftPick, DraftOrder, DraftBoard entities
- `app/engine/draft.py` (new) — `generate_draft_class()`, `simulate_all_draft_picks()`, `assign_picks_to_teams()`
- `tests/test_draft.py` (new) — 15-20 tests covering generation determinism, pick simulation, rookie contracts

**Acceptance Criteria:**
- Prospect generation is reproducible (same LEAGUE_SEED = same class)
- 250 prospects generated, position quota matched
- Draft order computed correctly from prior-season record + tiebreakers
- All picks simulated and assigned to teams
- Drafted prospects become real Players with rookie-scale contracts
- Full suite passes

### R5c: UI (2-3 hour session, Sonnet)

**Key Files:**
- `app/templates/draft.html` (new)
- `app/main.py` — new `draft_view` + `/api/draft/*` routes
- `app/templates/base.html` — new Prospect Card modal (re-use Player Card skeleton)
- `tests/test_draft_page.py` (new) — 10 tests covering route responses, filtering, board operations

**Acceptance Criteria:**
- `/draft` page renders with all 6 boxes (Team Picks, Team Needs, Draft Results, Prospects, Draft Board, Roster)
- Prospect filtering by position works
- "Add to Board" appends to draft board
- Draft board reordering works (UI + backend)
- Prospect Card modal opens with Overview/Ratings tabs
- Full suite passes
- Live verification in browser (port 8020, read-only)

---

## 14. Implementation Notes

**ALL DECISIONS FINALIZED (✓):**

1. **Prospect names:** Procedurally generated
2. **Dynamic draft class:** 235-265 prospects per LEAGUE_SEED (banded)
3. **Position quota bands:** QB: 7-9, RB: 24-28, WR: 33-37, TE: 16-20, OL: 40-44, DL: 30-34, LB: 24-28, CB: 22-26, S: 14-18, K: 1-2, P: 1-2
4. **QB class variance:** Yes (Elite/Strong/Average/Weak years per LEAGUE_SEED)
5. **Attribute generation:** Position-specific formulas with ±variance, NOT uniform random
6. **Undrafted rookies:** Auto-add to FA pool, 3-year `years_remaining` window, age-weighted two-tier annual cleanup (delete 100% at year 0, 25% at year 1, 10% at year 2-3)
7. **Rookie Scale AAV:** Simplified game-scale table (see §2.3), tuned to $720M cap, disclosure on UI
8. **League minimum salary:** $885K (all players, including undrafted rookies)
9. **Scouting noise:** ±0-4 points per attribute (tight tolerance)
10. **Draft board limit:** 50 slots per team
11. **Game calendar:** Playoffs → Coaching market (R3d) → Contract renewals (R4a) → FA market (R4b) → Draft (R5) → Preseason (R10) → Regular season → Playoffs repeat
12. **Trading window:** Only after Playoffs end, disabled during other phases
13. **Scouting narratives/Comp players:** Defer to future (likely R9)

---

## 15. Ready for R5b/c Implementation

**R5b (Core Engine)** — 2-3 hour session (Sonnet):
- Generate draft class (deterministic, banded size + positions)
- Simulate all picks (greedy AI: best-available at need)
- Convert drafted prospects to Players (with rookie-scale AAV)
- Convert undrafted prospects to UDFA pool entries
- Implement annual cleanup logic

**R5c (UI)** — 2-3 hour session (Sonnet):
- `/draft` page (6 boxes: Team Picks, Team Needs, Draft Results, Prospects, Draft Board, Roster)
- Prospect filtering, sorting, "Add to Board"
- Draft Board reordering
- Prospect Card modal (Overview/Ratings tabs)
- Integration with `/api/draft/*` routes

**Tests:**
- Determinism (same LEAGUE_SEED = same class)
- Position quotas and class size bands
- Draft order calculation
- Pick simulation and Player creation
- Undrafted cleanup logic

---

**End Specification.**
