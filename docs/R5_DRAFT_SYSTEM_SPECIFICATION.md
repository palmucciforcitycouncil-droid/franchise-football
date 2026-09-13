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

2. **Position Quota Bands:** Each position drawn from a band, total sums to class size
   - QB: 7-9
   - RB: 24-28
   - WR: 33-37
   - TE: 16-20
   - OL: 40-44 (C/G/T, internal split seeded)
   - DL: 30-34
   - LB: 24-28
   - CB: 22-26
   - S: 14-18
   - K: 1-2
   - P: 1-2
   - **Total: varies based on band draws, sums to class_size**
   
   Algorithm:
   - Draw class_size first (seeded)
   - For each position in order, draw from its band (seeded per position)
   - After final position, adjust that position's count to make total = class_size (ensures exact sum)

3. **Per-Prospect Generation:** Seeded on `stable_seed(LEAGUE_SEED, "draft", prospect_index)`:
   - **Name:** Procedurally generated from a syllable-pool (first + last, deterministic seeded draw).
   - **College:** Random from ~130 real FBS colleges (deterministic seeded draw)

4. **Class Strength Band (QB-specific variance):**
   
   Each year's draft class has a **strength level** drawn seeded per `stable_seed(LEAGUE_SEED, "draft", "class_strength")`, affecting QB quality distribution:
   
   - **Elite QB Year (rare):** 1-2 QBs with OVR 88-99, 1-2 with 78-87, rest 60-77
   - **Strong QB Year:** 2-3 QBs with OVR 83-92, 2-3 with 75-82, rest 55-74
   - **Average QB Year:** 1-2 QBs with OVR 80-89, 3-4 with 70-79, rest 50-69
   - **Weak QB Year:** 0-1 QBs with OVR 78+, most QBs 55-75, some 40-54
   
   **Mechanism:** A "QB class strength" roll (0-100) determines the distribution band, then individual QB base talents are seeded within that band. This ensures some years are weak, some are elite, matching real NFL variation.

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
    - Each attribute: ±0-8 point noise (stochastic uncertainty)
    - Noise is pre-computed and stored in `Prospect.scouting_noise` dict per team
    - **Disclosed on the UI:** "Your scouting view differs from league consensus" when noise differs materially from OVR

---

## 2.3 Rookie Scale AAV: NFL Formula vs. Simplified

**Decision Required:** Choose one approach below. Both maintain reproducibility (same LEAGUE_SEED = same scale).

### Option A: Real NFL Formula (2025 Actual)

**Pros:**
- Authentic to real-world precedent
- Integrates with real draft-value charts (players know the anchor)
- Pick #1 overall = authentic top-pick leverage point

**Cons:**
- Real 2025 scale: ~$40M for pick #1, ~$1M for 7th rounder
- This engine's salary cap is rescaled to $720M (§8.4 of R4a)
- At real scales, even a 3rd-round pick costs 0.2% of total cap — everything under round 4 is nearly free
- Creates two unintended incentives: (1) ignore mid-round picks as cost-irrelevant, (2) always trade down (every pick below round 2 is "throwing away value")

**Formula (if chosen):**
```
Base = [Real 2025 NFL scale per round/position]
Adjustment = [scale Real_2025_NFL_Cap / $301.2M] × [this_engine_cap / $720M]
Final_AAV = Base × Adjustment
```
Result: Pick #1 ~$12-15M, pick #32 ~$3-4M, pick #33 ~$2.5-3M (rounded for game balance).

---

### Option B: Simplified Game-Scale Table (Recommended for R5b/c)

**Pros:**
- Tuned specifically to this game's salary dynamics
- Every draft round matters (no "basically free" picks)
- Simpler to understand and balance
- Can re-tune after one season of observing AI team behavior

**Cons:**
- Not anchored to real NFL data
- Needs tuning/iteration once gameplay is observed
- Requires disclosure ("Game-balance rookie scale, not real NFL")

**Example Table (to be tuned):**

| Round | Pick 1-8 | Pick 9-16 | Pick 17-24 | Pick 25-32 |
|-------|----------|----------|----------|----------|
| 1     | $8.0M    | $6.0M    | $4.5M    | $3.5M    |
| 2     | $3.0M    | $2.2M    | $1.8M    | $1.5M    |
| 3     | $1.2M    | $1.0M    | $0.9M    | $0.8M    |
| 4     | $0.7M    | $0.6M    | $0.55M   | $0.5M    |
| 5     | $0.5M    | $0.45M   | $0.4M    | $0.35M   |
| 6     | $0.35M   | $0.3M    | $0.28M   | $0.25M   |
| 7     | $0.25M   | $0.22M   | $0.2M    | $0.18M   |

**Interpretation:** A top-10 pick costs $3-8M; a mid-rounder costs $0.5-1.2M; late picks cost $0.2-0.5M. Every pick has real marginal cost on the salary cap.

---

**Brian's Choice:** Which approach for R5b implementation? (Can always switch to NFL formula later if gameplay testing favors it.)

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

**Rookie Scale AAV Formula (to be tuned):**
```
Round 1:  Pick 1-8 = $20M, Pick 9-16 = $15M, Pick 17-24 = $12M, Pick 25-32 = $10M
Round 2:  Pick 1-8 = $8M,  Pick 9-16 = $6M,  Pick 17-24 = $5M,  Pick 25-32 = $4M
Round 3+: Scaling down (to be determined, or unified minimum ~$1.5M)
```

These are **disclosed as game-balance numbers**, not real NFL figures.

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

### 9.2 Undrafted Rookies → Free Agent Pool

**Lifecycle:**

1. **At draft end:** All 235-265 prospects that were NOT drafted by any team are added to the free agent pool as `UndraftedRookie` entries
   - Status: Available, years_remaining = 3
   - Can be signed by any team (same as regular free agents)

2. **On signing:** Undrafted rookie becomes a real `Player` with:
   - contract_years_remaining = 1-2 (typically 1 year for UDFAs, can be extended)
   - salary = league minimum (or negotiated up per R4a if that system exists)
   - acquired_via = "UNDRAFTED"

3. **Annual cleanup:** Every offseason (`apply_coach_offseason()` time), delete the lowest-rated 20% of the undrafted free agent pool:
   - **Rationale:** Real UDFA pool grows unbounded without cleanup (new UDFAs every year, signed ones become rostered players, but unsign ones stay in FA pool indefinitely)
   - **Mechanism:** 
     1. Query all FA pool players with `acquired_via="UNDRAFTED"` and `years_remaining > 0`
     2. Sort by OVR descending
     3. Delete the bottom 20% (lowest OVR)
   - **Example:** 50 undrafted rookies in FA pool → delete the 10 lowest-rated

4. **Expiration:** Undrafted rookies have a hard 3-year window. If not signed after 3 offseasons, they're auto-deleted (or years_remaining decrements and hits 0).

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

## 14. Open Questions for Brian

**DECIDED (✓):**
- Prospect names: Procedurally generated (no real college player CSV needed)
- Dynamic draft class: 235-265 prospects per LEAGUE_SEED (not fixed 250)
- Position quota bands: Yes (QB: 7-9, RB: 24-28, etc.)
- QB class variance: Yes (some years elite, some weak)
- Attribute generation: Position-specific formulas (not uniform random)
- Undrafted rookies: Auto-add to FA pool, 3-year window, annual 20% cleanup

**STILL OPEN:**

1. **Rookie Scale AAV: NFL Formula vs. Simplified?**
   - Option A: Real 2025 NFL formula (~$40M pick #1, ~$1M pick #33+) adjusted for $720M cap
   - Option B: Simplified game-scale table (tuned for balance, every pick matters)
   - See §2.3 for detailed pros/cons. Recommend Option B for R5b (can switch later).

2. **Scouting Noise Level:** Is ±8 points per attribute right? Too high/low?

3. **Draft Board Limit:** 50 slots — correct, or larger/smaller?

4. **Live Draft Event Timing (R5.1):** Before/after playoffs? Separate "Draft Week" off-season?

5. **Comp Players / Scouting Narrative:** LLM-generated (future R9 feature), or disclosed stubs for now?

6. **Undrafted Cleanup Tuning:** Delete bottom 20% per offseason — is this the right percentage? (Could be 15%, 25%, configurable per season strength?)

---

**End Specification.**
