# Franchise Football — Roster Page Documentation (v3.1)

## Overview

The Roster page is the central hub for managing your franchise's active roster. It provides comprehensive player data visualization, depth chart management, and filtering capabilities. The page supports both attributes and statistical views, with responsive layouts for desktop, tablet, and mobile devices.

### Page Variants

- **Default**: Full roster loaded with data
- **Loading**: Skeleton states while fetching data
- **Error (demo)**: Fallback to demo data with inline banner
- **Long-list**: Optimized for rosters with 53+ players

### Target Frames

- Desktop: 1440×900
- Tablet: 1024×768
- Mobile: 390×844

---

## Design Tokens

Following Dashboard v3.1 design system:

### Colors

```css
/* Background */
--bg-primary: #0a1929;          /* Page background */
--bg-secondary: #1a2332;        /* Card backgrounds */
--bg-tertiary: #2d4a6f;         /* Borders, dividers */

/* Text */
--text-primary: #ffffff;        /* Main headings, labels */
--text-secondary: #94a3b8;      /* Secondary text, subtext */
--text-accent: #d4af37;         /* Gold accents, highlights */

/* Status Colors */
--status-healthy: #22c55e;      /* Healthy status */
--status-questionable: #f59e0b; /* Questionable (Q) */
--status-doubtful: #ef4444;     /* Doubtful (D) */
--status-out: #6b7280;          /* Out (O) */

/* Interactive */
--hover-bg: rgba(212, 175, 55, 0.1);
--active-bg: rgba(212, 175, 55, 0.2);
```

### Typography

```css
/* Headings */
h1, h2, h3: font-family: system-ui;
h1: 24px / 1.2;
h2: 20px / 1.3;
h3: 18px / 1.4;

/* Body */
body: 14px / 1.5;
.text-xs: 12px / 1.4;
.text-sm: 14px / 1.5;
```

### Spacing

```css
--padding-card: 16px;
--row-height: 44px;
--header-height: 44-48px;
--cell-padding: 8-12px;
--gap-sm: 8px;
--gap-md: 16px;
--gap-lg: 24px;
```

### Layout

```css
--table-max-height: 560px;      /* Desktop scroll container */
--name-column-width: 160px;     /* Sticky player column */
--min-numeric-width: 64px;      /* Minimum for stat columns */
```

---

## Layout Map

### Desktop (1440×900)

```
┌─────────────────────────────────────────────────────────────────┐
│ Header Bar                                                       │
│ [Team Pill] Active Roster        [Attrs/Stats] [Depth] [Filter] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ┌─ Roster Table Card ─────────────────────────────────────────┐ │
│ │ Team Roster (53 players)                          (demo)    │ │
│ │ Filtered by: All Positions                                  │ │
│ ├──────────────────────────────────────────────────────────────┤ │
│ │ [Alert: Couldn't load roster. Showing demo data.]           │ │
│ ├──────────────────────────────────────────────────────────────┤ │
│ │ ┌────────────────────────────────────────────────────────┐  │ │
│ │ │ [Sticky Header] Name | OVR | SPD | STR | ... | TRD    │  │ │
│ │ ├──────────────────────────────────────────────────────────┤ │
│ │ │ [Sticky] Player 1   │ 84 │ 78 │ 62 │ ... │ [icon]    │  │ │
│ │ │          Player 2   │ 82 │ 90 │ 74 │ ... │           │  │ │
│ │ │          ...        │    │    │    │     │           │  │ │
│ │ │          (max-h:560px with vertical scroll)           │  │ │
│ │ └──────────────────────────────────────────────────────────┘ │
│ │ [Sticky Horizontal Scrollbar]──────────────────────────────  │ │
│ └──────────────────────────────────────────────────────────────┘ │
│ 💡 Hold Shift + scroll to move horizontally                     │
│                                                                  │
│ ┌─ Depth Chart Cards (3-column grid) ────────────────────────┐  │
│ │ [Offense]     [Defense]     [Special Teams]                │  │
│ │ QB (2 slots)  DE (2 slots)  K (1 slot)                     │  │
│ │ RB (3 slots)  DT (1 slot)   P (1 slot)                     │  │
│ │ ...           ...            KR (2 slots)                   │  │
│ │                              PR (2 slots)                   │  │
│ └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Components Stack

```
┌─ RosterPage (Container) ────────────────────────────────────┐
│                                                              │
│  ┌─ Header Bar ──────────────────────────────────────────┐  │
│  │ Team Selector | Title | View Toggle | Actions         │  │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ RosterTable ──────────────────────────────────────────┐  │
│  │  ┌─ Title & Filters ──────────────────────────────────┐ │
│  │  │ "Team Roster (53)"  |  Position Filter            │ │
│  │  └──────────────────────────────────────────────────────┘ │
│  │  ┌─ Error Banner (conditional) ──────────────────────┐  │ │
│  │  │ ⚠️ Couldn't load roster. Showing demo data.       │  │ │
│  │  └──────────────────────────────────────────────────────┘ │
│  │  ┌─ Scrollable Table Container ──────────────────────┐  │ │
│  │  │ [Sticky Header + Fixed Left Column]              │  │ │
│  │  │ [Sortable Columns]                                │  │ │
│  │  │ [Zebra Striped Rows - 44px each]                 │  │ │
│  │  │ [Click row → opens Player Drawer]                │  │ │
│  │  └──────────────────────────────────────────────────────┘ │
│  │  [Sticky Horizontal Scrollbar]                         │  │
│  │  [Shift+Scroll Hint]                                   │  │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ DepthChartCards (3 columns) ──────────────────────────┐  │
│  │ [Offense] [Defense] [Special Teams]                    │  │
│  │ Dropdown selectors for each depth position             │  │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  [PlayerDrawer] ────────────────────────── (slide-over) ──▶  │
│  [FilterPanel] ─────────────────────────── (slide-over) ──▶  │
│  [DepthChartModal] ───────────────────────── (modal) ─────▶  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Component List

### 1. RosterPage (Container)

**Purpose**: Main page container managing state for roster data, filters, and UI interactions.

**Props**: None (top-level page component)

**State**:
- `viewMode`: 'attributes' | 'stats'
- `searchQuery`: string
- `selectedPlayer`: Player | null
- `filterOpen`: boolean
- `positionFilter`: string | null
- `loading`: boolean
- `error`: boolean
- `players`: Player[]
- `stats`: PlayerStats[]

**Children**:
- Header bar
- RosterTable
- DepthChartCards
- PlayerDrawer (conditional)
- FilterPanel (conditional)

### 2. RosterTable

**Purpose**: Core data grid displaying player attributes or statistics with advanced scrolling.

**Props**:
```typescript
interface RosterTableProps {
  players: Player[];
  stats: PlayerStats[];
  viewMode: 'attributes' | 'stats';
  loading: boolean;
  error: boolean;
  searchQuery: string;
  positionFilter: string | null;
  onPlayerClick: (player: Player) => void;
}
```

**Features**:
- Sticky header (always visible)
- Fixed left column (player name/info)
- Sortable columns (single-column sort)
- Zebra striping (subtle alternating rows)
- Vertical scroll (max-height: 560px)
- Sticky horizontal scrollbar (synced)
- Shift+scroll horizontal navigation
- Tooltips on header abbreviations
- Loading skeletons
- Error state with demo data

**Column Order - Attributes View**:
1. **Name** (sticky) - Avatar, #, POS, Name, Age subtext
2. OVR, SPD, STR, AGI, TPW, TAC, CTH, TCK, AWR, POT, STA, INJ, MOR, AGE
3. CTR (AAV compact), YRS, DEP
4. HLTH (chip: H/Q/D/O)
5. TRD (trade icon)

**Column Order - Stats View**:
- Universal: G, GS, Snaps, OVR, DEP
- QB: Att, Cmp, Cmp%, Yds, TD, INT, Y/A, Sack, Rating
- RB: Rush, Yds, Y/A, TD, Fum, Tgt, Rec, RecYds, RecTD
- WR/TE: Tgt, Rec, Yds, Y/R, TD, Drop, YAC
- DEF: Tkl, TFL, Sk, QBHits, Pressures, INT, PD, FF, FR, TD
- ST: FG, FGA, FG%, XP, XPA, XP%, Punts, Avg, Net

### 3. PlayerDrawer

**Purpose**: Right-side slide-over panel showing detailed player information.

**Props**:
```typescript
interface PlayerDrawerProps {
  player: Player | null;
  open: boolean;
  onClose: () => void;
}
```

**Tabs**:
1. **Overview** - Photo, bio, quick stats
2. **Ratings** - Full attribute breakdown with visual bars
3. **Stats** - Season and career statistics
4. **Contract** - Salary, years, bonuses, cap hit
5. **Injuries** - Injury history and current status

**Behaviors**:
- Opens from right side
- Overlay darkens background
- Close via X button, ESC key, or overlay click
- Scrollable content

### 4. DepthChartModal

**Purpose**: Full-screen modal for managing position depth charts with drag-and-drop.

**Props**:
```typescript
interface DepthChartModalProps {
  open: boolean;
  onClose: () => void;
  players: Player[];
}
```

**Features**:
- Draggable player slots
- Position groups (Offense, Defense, Special Teams)
- Auto-Assign button (tie-breaks: OVR → AWR → STA)
- Save/Cancel actions
- Visual feedback for drag operations

### 5. DepthChartCards

**Purpose**: Quick-view depth chart editors using dropdown selectors.

**Props**:
```typescript
interface DepthChartCardsProps {
  players: Player[];
  positionQuotas: Record<string, { current: number; min: number }>;
}
```

**Layout**: 3-column grid (Offense, Defense, Special Teams)

**Position Slots** (from quotas):
- **Offense**: QB (2), RB (3), WR (5), TE (2), C (1), G (2), T (2)
- **Defense**: DE (2), DT (1), LB (6), CB (4), S (4)
- **Special Teams**: K (1), P (1), KR (2), PR (2)

**Features**:
- Dropdown selection per slot
- Players sorted by OVR
- Shows player #, name, OVR
- Empty slot option
- Slot count display

### 6. FilterPanel

**Purpose**: Side panel for advanced roster filtering.

**Props**:
```typescript
interface FilterPanelProps {
  open: boolean;
  onClose: () => void;
}
```

**Controls**:
- Position chips (multi-select)
- Attribute sliders (OVR, SPD, CTH, TCK)
- Toggles (Injured, Trade Block, Rookie)
- Generated query preview (read-only)
- Apply/Clear buttons

---

## Behaviors

### Sticky Header

The table header remains visible at all times during vertical scroll. Implemented with:
- `position: sticky`
- `top: 0`
- `z-index: 10`
- Background color to prevent content bleed-through

### Fixed First Column

The player name column stays visible during horizontal scroll:
- `position: sticky`
- `left: 0`
- `z-index: 5` (below header)
- Width: 160px (optimized)
- Contains: avatar (24px), number, position badge, name, age

### Scrolling Mechanisms

**Vertical Scroll**:
- Container max-height: 560px
- Overflow-y: auto
- Scrollbar gutter: stable (prevents layout shift)

**Horizontal Scroll**:
- Sticky scrollbar at bottom of table (always accessible)
- Synced with main table scroll
- Shift+mousewheel for horizontal navigation
- Visual hint displayed below table

### Column Sorting

**Single-column sort**:
- Click header to sort
- First click: descending (default)
- Second click: ascending
- Third click: back to descending
- Visual indicator: ↑ ↓ arrows
- Default sort: OVR descending

**Sort Priority**:
- Numeric columns: natural number sort
- String columns: alphabetical (case-insensitive)

### Row Interactions

**Click**: Opens PlayerDrawer with full details
**Hover**: Subtle background highlight (rgba(212, 175, 55, 0.1))
**Active**: Pressed state (rgba(212, 175, 55, 0.2))

### Tooltips

All abbreviated column headers show full label on hover:
- OVR → Overall Rating
- SPD → Speed
- STR → Strength
- AGI → Agility
- TPW → Throw Power
- TAC → Throw Accuracy
- CTH → Catching
- TCK → Tackling
- AWR → Awareness
- POT → Potential
- STA → Stamina
- INJ → Injury Rating
- MOR → Morale
- DEP → Depth Chart Position
- HLTH → Health Status
- TRD → Trade Block

### Truncation & Overflow

**Long Names**: Ellipsis after 120px with tooltip showing full name
**Contract Values**: Formatted as $X.XM (e.g., $8.5M)
**Alignment**: 
  - Numeric columns: right-aligned, tabular-nums
  - Labels/text: left-aligned
  - Headers: center-aligned

---

## Redlines & Specifications

### Table Dimensions

```
Row Height:          44px
Header Height:       44-48px
Cell Padding:        py-2.5 (10px) | px-3 (12px)
Name Column Width:   160px (fixed, sticky)
Min Numeric Width:   64px
Table Max Height:    560px
```

### Spacing

```
Card Padding:        16px
Gap Between Cards:   24px
Header to Content:   16px border separator
```

### Typography

```
Headers:             14px, font-medium, text-[#94a3b8]
Cell Values:         14px, text-white
Subtext (age):       12px, text-[#94a3b8]
Position Badge:      12px, uppercase
```

### Colors & States

```css
/* Row States */
.row-default {
  background: transparent;
}
.row-even {
  background: rgba(255, 255, 255, 0.02); /* Zebra stripe */
}
.row-hover {
  background: rgba(212, 175, 55, 0.1);
  cursor: pointer;
}

/* Health Status Chips */
.health-healthy {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}
.health-questionable {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}
.health-doubtful {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}
.health-out {
  background: rgba(107, 114, 128, 0.2);
  color: #6b7280;
}
```

---

## API Contracts

### Roster — Attributes View

**Endpoint**: `GET /api/v1/teams/{team_id}/roster?view=attributes`

**Response**:
```json
{
  "team_id": "NE",
  "view": "attributes",
  "players": [
    {
      "name": "J. Kingsley",
      "num": 12,
      "pos": "QB",
      "age": 28,
      "ovr": 84,
      "spd": 78,
      "str": 62,
      "agi": 82,
      "tpw": 91,
      "tac": 86,
      "cth": 48,
      "tck": 22,
      "awr": 85,
      "pot": 88,
      "sta": 92,
      "inj": 18,
      "mor": 74,
      "ctr_aav": 8500000,
      "yrs": 2,
      "dep": "QB1",
      "health": "Q",
      "trade_block": false
    }
  ]
}
```

### Roster — Stats View

**Endpoint**: `GET /api/v1/teams/{team_id}/roster?view=stats&season=2025&scope=season`

**Response**:
```json
{
  "team_id": "NE",
  "season": 2025,
  "scope": "season",
  "players": [
    {
      "name": "J. Kingsley",
      "pos": "QB",
      "G": 5,
      "GS": 5,
      "Snaps": 320,
      "OVR": 84,
      "DEP": "QB1",
      "Att": 172,
      "Cmp": 118,
      "CmpPct": 68.6,
      "Yds": 1420,
      "TD": 10,
      "INT": 4,
      "YA": 8.3,
      "Sack": 9,
      "Rate": 101.4
    }
  ]
}
```

### Depth Chart — Read

**Endpoint**: `GET /api/v1/teams/{team_id}/depth_chart`

**Response**:
```json
{
  "QB": ["J. Kingsley", "B. Ortega"],
  "RB": ["T. Morrow", "K. Price", "R. Hall"],
  "WR": ["K. Benton", "D. Knox", "S. Ayers"],
  "TE": ["C. Matthews"],
  "DE": ["A. Johnson", "M. Williams"],
  "DT": ["B. Thompson"],
  "LB": ["D. Rodriguez", "J. Garcia", "K. Martinez", "L. Davis", "N. Wilson", "P. Anderson"],
  "CB": ["R. Taylor", "S. Thomas", "T. Moore", "V. Jackson"],
  "S": ["W. White", "X. Harris", "Y. Martin", "Z. Lee"],
  "K": ["E. Brooks"],
  "P": ["F. Clark"],
  "KR": ["K. Benton", "T. Morrow"],
  "PR": ["D. Knox", "S. Ayers"]
}
```

### Depth Chart — Write

**Endpoint**: `PUT /api/v1/teams/{team_id}/depth_chart`

**Request Body**:
```json
{
  "QB": ["J. Kingsley", "B. Ortega"],
  "RB": ["T. Morrow", "K. Price", "R. Hall"]
}
```

**Response**:
```json
{
  "ok": true,
  "updated_positions": ["QB", "RB"]
}
```

### Search (Optional)

**Endpoint**: `GET /api/v1/players/search?q=POS in (WR,TE) AND OVR>=75 AND CTH>=80`

**Response**:
```json
{
  "count": 12,
  "players": [
    {
      "name": "K. Benton",
      "team_id": "NE",
      "pos": "WR",
      "ovr": 87,
      "cth": 90
    }
  ]
}
```

---

## Fallback Policy

**When any API call fails or returns empty data**:

1. **Display inline banner** inside the card:
   ```
   ⚠️ Couldn't load roster. Showing demo data.
   ```
   - Background: `rgba(153, 27, 27, 0.2)`
   - Border: `#dc2626`
   - Text: white

2. **Add (demo) tag** in card title:
   ```
   Team Roster (53 players)                    (demo)
   ```

3. **Populate table** with full demo data (no blank cells)

4. **Set error state**: `error = true`

**Implementation**:
```typescript
useEffect(() => {
  fetch('/api/v1/teams/NE/roster?view=attributes')
    .then(res => res.json())
    .then(data => {
      setPlayers(data.players);
      setError(false);
    })
    .catch(() => {
      setPlayers(DEMO_ROSTER);
      setError(true);
    })
    .finally(() => setLoading(false));
}, []);
```

---

## Demo JSON

### Full Demo Dataset

```json
{
  "attributes": [
    {
      "name": "J. Kingsley",
      "num": 12,
      "pos": "QB",
      "age": 28,
      "ovr": 84,
      "spd": 78,
      "str": 62,
      "agi": 82,
      "tpw": 91,
      "tac": 86,
      "cth": 48,
      "tck": 22,
      "awr": 85,
      "pot": 88,
      "sta": 92,
      "inj": 18,
      "mor": 74,
      "ctr_aav": 8500000,
      "yrs": 2,
      "dep": "QB1",
      "health": "Q",
      "trade_block": false
    },
    {
      "name": "T. Morrow",
      "num": 22,
      "pos": "RB",
      "age": 26,
      "ovr": 82,
      "spd": 90,
      "str": 74,
      "agi": 88,
      "tpw": 40,
      "tac": 42,
      "cth": 76,
      "tck": 35,
      "awr": 78,
      "pot": 85,
      "sta": 88,
      "inj": 12,
      "mor": 79,
      "ctr_aav": 4200000,
      "yrs": 3,
      "dep": "RB1",
      "health": "Healthy",
      "trade_block": false
    },
    {
      "name": "K. Benton",
      "num": 11,
      "pos": "WR",
      "age": 27,
      "ovr": 87,
      "spd": 93,
      "str": 68,
      "agi": 91,
      "tpw": 36,
      "tac": 44,
      "cth": 90,
      "tck": 28,
      "awr": 83,
      "pot": 90,
      "sta": 90,
      "inj": 22,
      "mor": 81,
      "ctr_aav": 12000000,
      "yrs": 4,
      "dep": "WR1",
      "health": "Healthy",
      "trade_block": true
    },
    {
      "name": "M. Sanders",
      "num": 7,
      "pos": "QB",
      "age": 24,
      "ovr": 71,
      "spd": 81,
      "str": 58,
      "agi": 79,
      "tpw": 84,
      "tac": 78,
      "cth": 42,
      "tck": 18,
      "awr": 72,
      "pot": 82,
      "sta": 88,
      "inj": 15,
      "mor": 76,
      "ctr_aav": 1800000,
      "yrs": 1,
      "dep": "QB2",
      "health": "Healthy",
      "trade_block": false
    },
    {
      "name": "D. Wright",
      "num": 33,
      "pos": "RB",
      "age": 23,
      "ovr": 76,
      "spd": 88,
      "str": 69,
      "agi": 84,
      "tpw": 38,
      "tac": 40,
      "cth": 72,
      "tck": 32,
      "awr": 74,
      "pot": 83,
      "sta": 85,
      "inj": 20,
      "mor": 82,
      "ctr_aav": 2100000,
      "yrs": 2,
      "dep": "RB2",
      "health": "Healthy",
      "trade_block": false
    }
  ],
  "stats": [
    {
      "name": "J. Kingsley",
      "pos": "QB",
      "G": 5,
      "GS": 5,
      "Snaps": 320,
      "OVR": 84,
      "DEP": "QB1",
      "Att": 172,
      "Cmp": 118,
      "CmpPct": 68.6,
      "Yds": 1420,
      "TD": 10,
      "INT": 4,
      "YA": 8.3,
      "Sack": 9,
      "Rate": 101.4
    },
    {
      "name": "T. Morrow",
      "pos": "RB",
      "G": 5,
      "GS": 5,
      "Snaps": 285,
      "OVR": 82,
      "DEP": "RB1",
      "Rush": 102,
      "Yds": 486,
      "YA": 4.8,
      "TD": 4,
      "Fum": 1,
      "Tgt": 18,
      "Rec": 14,
      "RecYds": 128,
      "RecTD": 1
    },
    {
      "name": "K. Benton",
      "pos": "WR",
      "G": 5,
      "GS": 5,
      "Snaps": 298,
      "OVR": 87,
      "DEP": "WR1",
      "Tgt": 42,
      "Rec": 28,
      "Yds": 418,
      "YR": 14.9,
      "TD": 4,
      "Drop": 2,
      "YAC": 124
    }
  ],
  "depth_chart": {
    "QB": ["J. Kingsley", "M. Sanders"],
    "RB": ["T. Morrow", "D. Wright", "R. Hayes"],
    "WR": ["K. Benton", "L. Carter", "J. Thomas", "D. Knox", "S. Ayers"],
    "TE": ["C. Matthews", "P. Robinson"],
    "C": ["A. Johnson"],
    "G": ["B. Thompson", "C. Davis"],
    "T": ["D. Rodriguez", "E. Garcia"],
    "DE": ["F. Martinez", "G. Wilson"],
    "DT": ["H. Anderson"],
    "LB": ["I. Taylor", "J. Thomas", "K. Moore", "L. Jackson", "M. White", "N. Harris"],
    "CB": ["O. Martin", "P. Lee", "Q. Clark", "R. Lewis"],
    "S": ["S. Walker", "T. Hall", "U. Allen", "V. Young"],
    "K": ["W. King"],
    "P": ["X. Wright"],
    "KR": ["K. Benton", "T. Morrow"],
    "PR": ["L. Carter", "J. Thomas"]
  }
}
```

---

## React Code Samples

### RosterTable.tsx (Key Features)

```typescript
import { useState, useEffect, useRef } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

export function RosterTable({ 
  players, 
  stats, 
  viewMode, 
  loading, 
  error, 
  searchQuery, 
  positionFilter,
  onPlayerClick 
}: RosterTableProps) {
  const [sortField, setSortField] = useState<string>('ovr');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const stickyScrollRef = useRef<HTMLDivElement>(null);

  // Sync horizontal scrollbars
  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    const stickyScroll = stickyScrollRef.current;
    if (!scrollContainer || !stickyScroll) return;

    const handleMainScroll = () => {
      stickyScroll.scrollLeft = scrollContainer.scrollLeft;
    };

    const handleStickyScroll = () => {
      scrollContainer.scrollLeft = stickyScroll.scrollLeft;
    };

    scrollContainer.addEventListener('scroll', handleMainScroll);
    stickyScroll.addEventListener('scroll', handleStickyScroll);

    return () => {
      scrollContainer.removeEventListener('scroll', handleMainScroll);
      stickyScroll.removeEventListener('scroll', handleStickyScroll);
    };
  }, []);

  // Enable shift+scroll for horizontal navigation
  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (!scrollContainer) return;

    const handleWheel = (e: WheelEvent) => {
      if (e.shiftKey) {
        e.preventDefault();
        scrollContainer.scrollLeft += e.deltaY;
      }
    };

    scrollContainer.addEventListener('wheel', handleWheel, { passive: false });
    return () => scrollContainer.removeEventListener('wheel', handleWheel);
  }, []);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Filter and sort logic
  const filteredPlayers = players.filter(player => {
    if (positionFilter && player.pos !== positionFilter) return false;
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      player.name.toLowerCase().includes(query) ||
      player.pos.toLowerCase().includes(query) ||
      player.num.toString().includes(query)
    );
  });

  const sortedPlayers = [...filteredPlayers].sort((a, b) => {
    const aVal = a[sortField as keyof Player];
    const bVal = b[sortField as keyof Player];
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    }
    
    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return sortDirection === 'asc' ? 
      aStr.localeCompare(bStr) : 
      bStr.localeCompare(aStr);
  });

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white">Team Roster ({sortedPlayers.length} players)</h3>
          {error && <span className="text-[#94a3b8] text-xs">(demo)</span>}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 border-b border-[#2d4a6f]">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              Couldn't load roster. Showing demo data.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Scrollable Table */}
      <div className="relative">
        <div 
          ref={scrollContainerRef}
          className="overflow-x-auto overflow-y-auto max-h-[560px]" 
          style={{ scrollbarGutter: 'stable' }}
        >
          <table className="text-sm border-collapse" style={{ width: viewMode === 'attributes' ? '2500px' : '1400px' }}>
            {/* Sticky Header */}
            <thead className="sticky top-0 bg-[#1a2332] z-10 border-b border-[#2d4a6f]">
              <tr>
                {/* Sticky Name Column */}
                <th className="sticky left-0 bg-[#1a2332] z-20 text-left py-3 px-3 border-r border-[#2d4a6f]">
                  <button onClick={() => handleSort('name')}>
                    Player {getSortIcon('name')}
                  </button>
                </th>
                {/* Other sortable headers... */}
              </tr>
            </thead>
            
            <tbody>
              {sortedPlayers.map((player, idx) => (
                <tr 
                  key={player.name}
                  onClick={() => onPlayerClick(player)}
                  className={`
                    cursor-pointer hover:bg-[rgba(212,175,55,0.1)] transition-colors
                    ${idx % 2 === 1 ? 'bg-[rgba(255,255,255,0.02)]' : ''}
                  `}
                >
                  {/* Sticky Name Cell */}
                  <td className="sticky left-0 bg-inherit z-5 py-2.5 px-3 border-r border-[#2d4a6f]">
                    <div className="flex items-center gap-2">
                      <Avatar className="h-6 w-6">
                        <AvatarFallback className="text-xs">
                          {player.name.split(' ').map(n => n[0]).join('')}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[#94a3b8] text-xs">#{player.num}</span>
                          <span className="text-[#d4af37] text-xs uppercase px-1 py-0.5 bg-[#d4af37]/10 rounded">
                            {player.pos}
                          </span>
                          <span className="text-white truncate max-w-[80px]">{player.name}</span>
                        </div>
                        <div className="text-[#94a3b8] text-xs">{player.age} yrs</div>
                      </div>
                    </div>
                  </td>
                  {/* Other cells... */}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Sticky Horizontal Scrollbar */}
        {!loading && sortedPlayers.length > 0 && (
          <div 
            ref={stickyScrollRef}
            className="sticky bottom-0 overflow-x-auto border-t border-[#2d4a6f] bg-[#1a2332]"
            style={{ height: '20px', zIndex: 20 }}
          >
            <div style={{ width: viewMode === 'attributes' ? '2500px' : '1400px', height: '1px' }} />
          </div>
        )}
      </div>

      {/* Hint */}
      {!loading && sortedPlayers.length > 0 && (
        <div className="px-4 py-2 border-t border-[#2d4a6f] bg-[#0a1929]/50">
          <p className="text-[#94a3b8] text-xs text-center">
            💡 Hold <kbd className="px-1.5 py-0.5 bg-[#2d4a6f] rounded text-[10px] mx-1">Shift</kbd> + scroll to move horizontally, or use the scrollbar below
          </p>
        </div>
      )}
    </div>
  );
}
```

### PlayerDrawer.tsx (Structure)

```typescript
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

export function PlayerDrawer({ player, open, onClose }: PlayerDrawerProps) {
  if (!player) return null;

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[400px] bg-[#1a2332] border-[#2d4a6f] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-white">
            <div className="flex items-center gap-3">
              <Avatar className="h-16 w-16">
                <AvatarFallback>
                  {player.name.split(' ').map(n => n[0]).join('')}
                </AvatarFallback>
              </Avatar>
              <div>
                <div className="text-xl">{player.name}</div>
                <div className="text-sm text-[#94a3b8]">
                  #{player.num} · {player.pos} · {player.age} years old
                </div>
              </div>
            </div>
          </SheetTitle>
        </SheetHeader>

        <Tabs defaultValue="overview" className="mt-6">
          <TabsList className="grid w-full grid-cols-5 bg-[#0a1929]">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="ratings">Ratings</TabsTrigger>
            <TabsTrigger value="stats">Stats</TabsTrigger>
            <TabsTrigger value="contract">Contract</TabsTrigger>
            <TabsTrigger value="injuries">Injuries</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            {/* Quick stats overview */}
          </TabsContent>

          <TabsContent value="ratings" className="space-y-4">
            {/* Full attribute breakdown with progress bars */}
          </TabsContent>

          <TabsContent value="stats" className="space-y-4">
            {/* Season and career statistics */}
          </TabsContent>

          <TabsContent value="contract" className="space-y-4">
            {/* Salary details, years, bonuses */}
          </TabsContent>

          <TabsContent value="injuries" className="space-y-4">
            {/* Injury history and current status */}
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}
```

### DepthChartModal.tsx (Stub)

```typescript
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';

export function DepthChartModal({ open, onClose, players }: DepthChartModalProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl bg-[#1a2332] border-[#2d4a6f] text-white">
        <DialogHeader>
          <DialogTitle>Manage Depth Chart</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-6">
          {/* Left: Position selector */}
          <div>
            <h4>Positions</h4>
            {/* Position list */}
          </div>

          {/* Right: Draggable slots */}
          <div>
            <div className="flex justify-between mb-4">
              <h4>Depth Order</h4>
              <Button size="sm" variant="outline">
                Auto-Assign
              </Button>
            </div>
            {/* Drag-and-drop slots */}
            <p className="text-xs text-[#94a3b8] mt-2">
              Tie-breaks: OVR → AWR → STA
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button className="bg-[#d4af37] text-[#0a1929] hover:bg-[#c49f2f]">
            Save Changes
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

## Responsive Breakpoints

### Desktop (1440×900)
- Full 3-column layout for depth chart
- Table shows all columns
- Sidebar drawers at 400px width

### Tablet (1024×768)
- 2-column depth chart layout (Offense + Defense in row 1, Special Teams in row 2)
- Table horizontal scroll more prominent
- Sidebar drawers at 360px width

### Mobile (390×844)
- Single column depth chart (stacked)
- Table shows Name + OVR + 2-3 key stats only
- Sidebar drawers full-width
- Position filters as horizontal scroll chips
- Filter panel as bottom sheet instead of side panel

---

## Accessibility

- **Keyboard Navigation**: All interactive elements accessible via Tab
- **ARIA Labels**: Proper labels on buttons, inputs, selects
- **Focus States**: Visible focus rings on all interactive elements
- **Screen Reader**: Descriptive text for icons and abbreviated headers
- **Color Contrast**: WCAG AA compliant (4.5:1 minimum)

---

## Performance Considerations

- **Virtualization**: Consider react-window for rosters > 100 players
- **Memoization**: Memo expensive sort/filter operations
- **Lazy Loading**: Drawer/modal content loaded on demand
- **Debouncing**: Search input debounced at 300ms

---

## Future Enhancements

1. **Multi-column sort** (e.g., sort by OVR, then POT)
2. **Column visibility toggle** (show/hide specific columns)
3. **Export to CSV/Excel**
4. **Comparison mode** (select 2-4 players to compare side-by-side)
5. **Advanced filters** (natural language queries)
6. **Bulk actions** (multi-select for trades, cuts)
7. **Historical stats** (career, previous seasons)
8. **Injury simulator** (what-if scenarios)

---

**Document Version**: 3.1  
**Last Updated**: 2025-10-16  
**Maintained By**: Franchise Football Development Team
