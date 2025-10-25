# Draft Board Documentation
**Version:** Draft v2.1 (MVP - Roster Structure - Final)  
**Status:** Feature complete and ready for backend integration  
**Last Updated:** October 23, 2025

---

## Overview

The Draft Board has been redesigned to match the Roster page structure, providing a familiar and consistent experience for evaluating and comparing draft prospects. The page includes draft picks tracking, prospect evaluation with the same table interface as the roster, position-based filtering, comparison tools, and integration with current roster management.

---

## Page Structure

The Draft page follows this top-to-bottom layout (matching Roster page):

1. **Draft Picks Section** - Your team's current year draft picks
2. **Year Selector & Actions** - Draft class selector and compare actions
3. **Position Quotas** - Available prospects by position (clickable chips)
4. **Draft Prospects Table** - Main prospects table (same as Roster table with checkboxes)
5. **Three Quick Access Boxes** - Top Free Agents, Trading Block, Find Players
6. **Current Roster Table** - Your team's active roster

---

## Key Features

### 1. Draft Picks Display

Shows all of the user's draft picks for the current year (2025):

**Layout:**
- 7-column grid (one per round)
- Each card shows:
  - Round number
  - Pick number within round
  - Overall pick number
- Gold accent color (#d4af37)
- Hover effect for interactivity

**Example:**
```
Round 1    Round 2    Round 3    Round 4    Round 5    Round 6    Round 7
  #15        #18        #15        #22        #15        #20        #15
Overall:   Overall:   Overall:   Overall:   Overall:   Overall:   Overall:
   15         50         79        118        151        192        223
```

### 2. Draft Class Selector

**Year Dropdown:**
- 2025 (Current) - Default selected
- 2024
- 2023
- 2022

**Features:**
- Each year has 200-250 unique prospects
- Deterministic generation (same prospects each time)
- 2025 has no drafted players (current year)
- Past years (2022-2024) have ~30% drafted players
- Total prospects count displayed
- Available prospects count displayed

### 3. Position Quotas (Clickable Chips)

Displays available (undrafted) prospect count by position:

**Positions:** QB, RB, WR, TE, OL, DL, LB, CB, S, K, P

**Color Coding:**
- Green: Over quota (>= quota)
- Orange: Exact quota (== quota)
- Red: Under quota (< quota)

**Interaction:**
- Click any position chip to filter prospects table
- Active filter shows blue background with gold border
- "Clear Filter" button appears when filter is active
- Returns to "ALL" positions when cleared

**Quotas (Available Prospects):**
```
QB: min 5    RB: min 8    WR: min 10   TE: min 5    OL: min 10
DL: min 10   LB: min 8    CB: min 8    S: min 6     K: min 2    P: min 2
```

### 4. Draft Prospects Table

**Same interface as Roster Table with additions:**

**Checkbox Column (Added):**
- Fixed column on the left (absolutely positioned, 48px width)
- Checkboxes for multi-select (max 5 prospects)
- Gold fill when selected (#d4af37)
- Click checkbox to toggle selection
- 73px row height to match table rows perfectly

**View Mode:**
- **Attributes View Only:** Shows all player attributes (OVR, POT, SPD, AGI, STR, AWR, etc.)
- College Stats view removed (coming in future phase)

**Table Features:**
- Sticky header with horizontal scroll
- Sortable columns
- Same scroll architecture as Roster table (split-table with sync)
- Position badges
- Draft status in DEP column:
  - "Available" for undrafted
  - "Rd X" for drafted prospects

**Data Display:**
- Name, Position, Age, all attributes
- Contract field shows College name
- Health always "Healthy"
- Years field is 0 (rookies)

**Header Actions:**
- **Clear Button:** Shows when any prospects selected, displays count
- **Compare Button:** Always visible, enabled when 2-5 selected, replaces view toggle

### 5. Compare Drawer

**Opens from right side when Compare clicked:**

**Sections:**
1. **Top: Prospect Cards**
   - First selected = Baseline (gold border)
   - Shows: Name, Position, Overall, College
   - Remaining prospects in standard cards

2. **Middle: Percentile Bars**
   - Horizontal bars for each attribute
   - Overall, Potential, Speed, Agility, Strength, Awareness, Board Score
   - Color-coded performance:
     - Green (≥90): Elite
     - Blue (≥80): High Quality
     - Orange (≥70): Solid
     - Gray (<70): Below Average

3. **Bottom: Difference Table**
   - Shows +/- differential vs baseline
   - Green for positive, Red for negative, Gray for zero
   - All 7 attributes compared

**Behavior:**
- Closes via X button or backdrop
- Clears selection on close
- Scrollable content for many prospects

### 6. Three Quick Access Boxes

Same as Roster page - "Coming Soon" placeholders:

- **Top Free Agents:** Browse and sign available free agents
- **Trading Block:** View teams looking to trade picks and players
- **Find Players:** Search across all teams and free agents

### 7. Current Roster Table

**Exact same as Roster page:**
- Shows your team's active 53-man roster
- Attributes view (default)
- Same table interface
- **No checkboxes** (uses standard RosterTable component)

---

## Data Schema

### DraftProspect Interface
```typescript
interface DraftProspect {
  prospect_id: string;           // Format: "YYYY_PROSPECT_N"
  name: string;
  position: string;              // QB, RB, WR, TE, OL, DL, LB, CB, S, K, P
  college: string;
  overall: number;               // 60-99
  potential: number;             // 60-99
  speed: number;                 // 60-99
  agility: number;               // 60-99
  strength: number;              // 60-99
  awareness: number;             // 60-99
  board_score: number;           // Calculated: (overall * 0.6 + potential * 0.4)
  tier: number;                  // 1-5 based on overall
  drafted: boolean;              // False for 2025, ~30% for past years
  draft_round?: number;          // 1-7 (if drafted)
  draft_pick?: number;           // 1-32 (if drafted)
  team_drafted?: string;         // Team abbreviation (if drafted)
}
```

### DraftFilters Interface
```typescript
interface DraftFilters {
  year?: number;                 // 2022-2025
  position?: string;             // 'ALL' or position code
  minOverall?: number;           // 0-99
  minPotential?: number;         // 0-99
  showDrafted?: boolean;         // Show/hide drafted prospects
  sortBy?: 'board_score' | 'overall' | 'potential' | 'name';
  sortOrder?: 'asc' | 'desc';
}
```

### API Endpoint
```
GET /api/v1/draft/prospects?year=2025&position=QB
```

---

## Draft Classes

**4 Years of Classes:**
- 2025 (Current): 200-250 prospects, 0% drafted
- 2024: 200-250 prospects, ~30% drafted
- 2023: 200-250 prospects, ~30% drafted
- 2022: 200-250 prospects, ~30% drafted

**Generation:**
- Deterministic (same seed per year)
- Unique names, colleges, attributes per year
- Realistic attribute distributions (60-99 range)
- Balanced position distribution
- Board score calculated from OVR + POT
- Tier assignments (1-5) based on overall rating

**Positions Included:**
- QB, RB, WR, TE - Offensive skill
- OL - Offensive line
- DL, LB - Defensive front seven
- CB, S - Defensive backs
- K, P - Special teams (kicker, punter)

---

## Visual Design

### Color Palette
```css
/* Backgrounds */
--bg-primary: #0a1929;
--bg-card: #11161C;
--bg-secondary: #0B0F14;
--bg-hover: #1a2332;
--bg-table-dark: #1F2A35;

/* Borders */
--border-primary: #1F2A35;
--border-secondary: #2d4a6f;

/* Text */
--text-primary: #E6EDF3;
--text-secondary: #94a3b8;
--text-muted: #64748b;

/* Accent Colors */
--gold: #d4af37;           /* Selections, highlights */
--gold-hover: #c49a2e;     /* Hover states */
--blue-active: #1e3a5f;    /* Active filters/buttons */

/* Status Colors */
--available: #27ae60;      /* Undrafted */
--drafted: #e74c3c;        /* Drafted */
--warning: #f39c12;        /* Exact quota */
```

### Checkbox Design
```
Unselected: 20px square, 2px border, #2d4a6f color
Selected:   20px square, gold fill (#d4af37), white checkmark
Hover:      Slight opacity change
```

### Table Styling
- Same as Roster table
- 41px row height
- Sticky header at top
- Horizontal scroll with sync rails
- Alternating row hover states

---

## User Interactions

### Multi-Select Workflow

1. **Select Prospects:**
   - Click anywhere in table row to toggle
   - Checkbox updates immediately
   - Row background highlights (blue tint)
   - Max 5 selections enforced
   - Counter shows in buttons

2. **Compare Action:**
   - "Compare (N)" button enabled at 2+ selections
   - Click to open drawer from right
   - Drawer shows all selected prospects
   - First selected = Baseline

3. **Clear Selection:**
   - "Clear (N)" button shows when any selected
   - One-click to deselect all
   - Selection persists during scrolling

### Position Filtering

1. **Click any position chip** in quota bar
2. Table filters to show only that position
3. Chip shows active state (blue + gold border)
4. "Clear Filter" button appears
5. Click "Clear Filter" or active chip to reset

### Year Selection

1. Select year from dropdown (2022-2025)
2. Table reloads with new draft class
3. Selection cleared
4. Position filter maintained
5. Loading state shown during fetch

---

## Loading & Empty States

### Loading States
- Skeleton rows (10 placeholders) during data fetch
- "Loading..." state for drawer
- Maintains table structure

### Empty States
- No prospects: "No prospects found matching your filters"
- No selections: Compare button disabled
- No draft picks: Would show empty state (currently hardcoded)

---

## Comparison to Roster Page

### Same Features
✅ Table layout and structure  
✅ Attributes/Stats view toggle  
✅ Position quota chips  
✅ Sortable columns  
✅ Sticky header  
✅ Horizontal scroll architecture  
✅ Three quick access boxes  
✅ Current roster display  

### New Features
✅ Checkboxes for multi-select  
✅ Compare drawer  
✅ Draft class year selector  
✅ Draft picks display  
✅ Draft status badges  
✅ College names in contract field  

### Removed Features
❌ Player drawer (not needed for prospects)  
❌ Depth chart integration  
❌ Salary cap information  
❌ Trade toggle  
❌ Search bar (coming later)  

---

## Integration Checklist

- [ ] Backend implements `GET /api/v1/draft/prospects`
- [ ] Year parameter filters draft classes
- [ ] Position parameter filters by position
- [ ] Response matches `DraftProspect` schema
- [ ] Draft picks endpoint created (GET /api/v1/draft/picks)
- [ ] Current roster endpoint integrated
- [ ] Proper error handling
- [ ] Loading states work correctly
- [ ] Pagination implemented if >200 prospects
- [ ] Compare drawer saves selections

---

## Future Enhancements

### Phase 2
- [ ] Player detail drawer for prospects
- [ ] College stats view (replace placeholder)
- [ ] Search/filter bar above table
- [ ] Export prospects to CSV
- [ ] Draft pick trading interface
- [ ] Mock draft simulator

### Phase 3
- [ ] Scouting reports
- [ ] Combine data integration
- [ ] Video highlights
- [ ] AI draft recommendations
- [ ] Historical draft analysis
- [ ] Multi-year planning tools

---

## Technical Notes

### Performance
- 200-250 prospects per year = manageable without virtualization
- Future: Virtual scrolling for large datasets
- Memoize conversions and calculations
- Debounced filtering

### Accessibility
- Keyboard navigation for table
- ARIA labels on checkboxes
- Focus management in drawer
- Screen reader announcements
- High contrast support

### Mobile Responsiveness
- Stack layout on mobile
- Horizontal scroll for table
- Touch-friendly checkboxes (44px hit target)
- Simplified chip layout
- Drawer becomes full-screen

---

## File Locations

```
/components/DraftPage.tsx                   - Main page (redesigned)
/components/RosterTable.tsx                 - Shared table component
/components/draft/DraftProspectsTable.tsx   - Wrapper with checkboxes
/components/draft/CompareDrawer.tsx         - Comparison drawer
/lib/mockDraftApi.ts                        - Mock API with 4 years
```

**Removed Files:**
```
/components/draft/DraftBoard.tsx       - Replaced by new DraftPage
/components/draft/TiersView.tsx        - Removed (may return later)
```

**Key Implementation:**
- `DraftProspectsTable` wraps `RosterTable` and adds checkbox column
- Checkbox height (73px) matches table row height exactly
- Uses index-based selection for proper prospect tracking
- Current roster uses plain `RosterTable` without checkboxes

---

## Mock Data

**Current Implementation:**
- 4 years of draft classes (2022-2025)
- 200-250 prospects per year (random count in range)
- 11 positions including K and P
- Deterministic generation (repeatable)
- 18 colleges
- 20 first names, 20 last names
- Realistic attribute distributions

**Draft Pick Mock:**
- 7 rounds hardcoded for user's team
- Picks vary per round (trades simulated)
- Overall pick numbers calculated

---

**Status:** ✅ MVP Complete - Matches Roster page structure  
**Version:** Draft v2  
**Next Steps:** Backend API implementation and college stats integration

---
