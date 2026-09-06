# Playoffs Page Documentation
**Version:** Playoffs v1 (frozen)  
**Status:** Design locked and ready for backend integration  
**Last Updated:** October 18, 2025

---

## Overview

The Playoffs page displays the NFL playoff bracket with three view modes (AFC, NFC, Super Bowl), featuring tournament tree layouts, SVG connector lines, game progression flow, and comprehensive playoff standings.

---

## Component Taxonomy

All playoff components follow this exact naming structure:

### Core Components
- **Playoff/Badge** (`/components/playoffs/PlayoffBadge.tsx`)
  - Displays conference/round badges (AFC, NFC, WC, DIV, CONF, SB)
  - Color-coded: AFC = red, NFC = blue, rounds = neutral gray

- **Playoff/MatchupRow** (`/components/playoffs/MatchupRow.tsx`)
  - Displays individual game matchup with seeds, team names, and scores
  - Shows winner highlighting in gold when game is complete

- **Playoff/RoundCard** (`/components/playoffs/RoundCard.tsx`)
  - Container for playoff round matchups (Wild Card, Divisional, Conference)
  - Used in AFC/NFC bracket views

- **Playoff/SuperBowlCard** (`/components/playoffs/SuperBowlCard.tsx`)
  - Championship game display card
  - Shows AFC vs NFC champions with scores

- **Playoff/HuntCard** (`/components/playoffs/HuntCard.tsx`)
  - Displays teams "In The Hunt" for playoff spots
  - Shows games back and projected seed

### Supporting Components
- **ConferenceBracket** (`/components/playoffs/ConferenceBracket.tsx`)
  - Full bracket layout with SVG connectors for AFC/NFC views
  
- **BracketMatchup** (`/components/playoffs/BracketMatchup.tsx`)
  - Compact matchup display for Super Bowl bracket overview

- **SuperBowlView** (`/components/playoffs/SuperBowlView.tsx`)
  - Main Super Bowl tab view with bracket overview and game details

---

## Data Hooks (Integration Layer)

All integration points use `data-layer` attributes for e2e testing and backend wiring:

### Round Cards
- `data-layer="afc-wc"` - AFC Wild Card round container
- `data-layer="afc-div"` - AFC Divisional round container
- `data-layer="afc-conf"` - AFC Conference Championship container
- `data-layer="nfc-wc"` - NFC Wild Card round container
- `data-layer="nfc-div"` - NFC Divisional round container
- `data-layer="nfc-conf"` - NFC Conference Championship container

### Special Cards
- `data-layer="sb-card"` - Super Bowl game card
- `data-layer="hunt-strip"` - "In The Hunt" teams section

### Testing Hooks
- `data-test="playoff-content"` - Main content area wrapper
- Individual matchups use index-based keys for identification

---

## Visual Contract (DO NOT ALTER)

### Color Palette
```css
/* Dark Theme Foundation */
--bg-primary: #0B0F14;        /* Main background */
--bg-card: #11161C;           /* Card backgrounds */
--stroke: #1F2A35;            /* Borders and strokes */
--text-primary: #E6EDF3;      /* Primary text */
--text-muted: #94a3b8;        /* Secondary text */

/* Conference Colors */
--afc-red: #dc2626;           /* AFC primary */
--afc-red-light: #ef4444;     /* AFC text */
--nfc-blue: #1e40af;          /* NFC primary */
--nfc-blue-light: #60a5fa;    /* NFC text */

/* Accent Colors */
--gold: #d4af37;              /* Winners, highlights */
--gold-hover: #c49a2e;        /* Interactive states */
```

### Border Radius
- Cards: `16px` (rounded-2xl)
- Buttons: `6px` (rounded-md)
- Badges: `6px` (rounded-md)

### Shadows
- Subtle shadow: `blur 16px, opacity 20%`
- Elevation: `0 4px 16px rgba(0, 0, 0, 0.2)`

### Spacing Scale
- Base unit: `4px`
- Gap between cards: `16px` (gap-4)
- Card padding: `24px` (p-6)
- Section spacing: `24px` (space-y-6)

### Typography
Font: Inter/System Stack

```css
/* Headings */
H1: 32px / 700 weight (text-3xl font-bold)
H2: 22px / 700 weight (text-xl font-bold)
H3: 18px / 600 weight (text-lg font-semibold)

/* Body & UI */
Body: 14px / 400 weight (text-sm)
Label: 12px / 600 weight (text-xs font-semibold)
```

### Grid Layout

#### Desktop (AFC/NFC Views)
```
┌─────────────────────────────────────────┐
│  [AFC/NFC Badge]  Conference Name       │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐   │
│  │ WC  │→ │ DIV │→ │CONF │→ │CHAMP│   │
│  │ x3  │  │ x2  │  │ x1  │  │Seed │   │
│  └─────┘  └─────┘  └─────┘  └─────┘   │
│                                         │
└─────────────────────────────────────────┘
```

#### Desktop (Super Bowl View)
```
┌─────────────────────────────────────────┐
│  ┌────────┐   ┌──────┐   ┌────────┐    │
│  │  AFC   │   │  🏆  │   │  NFC   │    │
│  │Bracket │ → │  SB  │ ← │Bracket │    │
│  │Summary │   │ Game │   │Summary │    │
│  └────────┘   └──────┘   └────────┘    │
├─────────────────────────────────────────┤
│  Box Score (no week navigation)         │
│  Play-by-Play                          │
└─────────────────────────────────────────┘
```

### In The Hunt Section
- Layout: Horizontal scroll with scroll-snap
- Cards: 6 compact cards visible
- Behavior: Smooth scrolling, snap to card edges
- Mobile: Single column stack

---

## Data Mapping

### API Endpoint
```
GET /api/v1/playoffs
```

**DO NOT CHANGE** the endpoint path or field names.

### Response Schema

```typescript
interface PlayoffBracketDTO {
  rounds: PlayoffRound[];
  in_the_hunt: HuntTeam[];
}

interface PlayoffRound {
  round_id: string;
  round_name: 'WC' | 'DIV' | 'CONF' | 'SB';
  matchups: PlayoffMatchup[];
}

interface PlayoffMatchup {
  matchup_id: string;
  round: 'WC' | 'DIV' | 'CONF' | 'SB';
  side: 'AFC' | 'NFC' | null;
  higher_seed_team: TeamPlayoffInfo;
  lower_seed_team: TeamPlayoffInfo;
  higher_seed_score: number | null;
  lower_seed_score: number | null;
  is_complete: boolean;
  winner_team_id: string | null;
}

interface TeamPlayoffInfo {
  team_id: string;
  team_name: string;
  team_abbr: string;
  seed: number;
  logo_url: string | null;  // Optional
  conference: 'AFC' | 'NFC';
}

interface HuntTeam {
  team_id: string;
  team_name: string;
  team_abbr: string;
  side: 'AFC' | 'NFC';
  games_back: number;
  seed_if_made: number;
  current_record: string;
}
```

### Field Requirements

#### MatchupRow Component
Expects these fields on both `higher_seed_team` and `lower_seed_team`:
- `seed` (int) - Playoff seed number (1-7)
- `team_name` (string) - Full team name
- `team_abbr` (string) - 2-3 letter abbreviation
- `logo_url` (string|null) - Optional team logo URL

#### Super Bowl Card
- Uses: `rounds[SB].matchups[0]`
- AFC champion: `higher_seed_team`
- NFC champion: `lower_seed_team`

#### Round Filtering
**Wild Card:**
```javascript
const afcWC = rounds.find(r => r.round_name === 'WC')
  ?.matchups.filter(m => m.side === 'AFC') || [];
```

**Divisional:**
```javascript
const afcDIV = rounds.find(r => r.round_name === 'DIV')
  ?.matchups.filter(m => m.side === 'AFC') || [];
```

**Conference:**
```javascript
const afcCONF = rounds.find(r => r.round_name === 'CONF')
  ?.matchups.filter(m => m.side === 'AFC') || [];
```

#### In The Hunt
Maps `in_the_hunt[]` array to HuntCard:
- `side` - Conference filter ("AFC"/"NFC")
- `team_name` / `team_abbr` - Display names
- `games_back` - Games behind playoff spot
- `seed_if_made` - Projected seed if playoffs started today

---

## Loading & Error States

### Loading State
```tsx
// Skeleton rows (3 in WC, 2 in DIV, 1 in CONF)
<Skeleton className="h-[120px] bg-[#11161C]" />
<Skeleton className="h-[600px] bg-[#11161C]" />
```

### Error State
If response contains `{error: {code, message}}`:

```tsx
<div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-12 text-center">
  <AlertCircle className="h-12 w-12 text-[#e74c3c] mx-auto mb-4" />
  <h3 className="text-white mb-2">Data Unavailable</h3>
  <p className="text-[#94a3b8] mb-4">{error.message}</p>
  <Button onClick={retry}>Retry</Button>
</div>
```

### Empty States
- No matchups: Show placeholder text "Advances after games"
- No hunt teams: Hide section entirely

---

## View Modes

### AFC View
- Shows full AFC bracket (WC → DIV → CONF → Champion)
- SVG connectors flow left-to-right
- In The Hunt section at bottom
- Division Standings at bottom

### NFC View
- Shows full NFC bracket (WC → DIV → CONF → Champion)
- SVG connectors flow right-to-left (mirrored)
- In The Hunt section at bottom
- Division Standings at bottom

### Super Bowl View
- Compact 2-team bracket overview (AFC vs NFC)
- Super Bowl game card with scores
- Box Score (no week navigation)
- Play-by-Play
- NO Division Standings
- NO In The Hunt section

---

## Navigation Tabs

Three-button toggle at top:
1. **AFC Bracket** - Red theme when active
2. **Super Bowl** - Gold theme when active
3. **NFC Bracket** - Blue theme when active

```tsx
// Active state styling
AFC active: bg-[#dc2626] text-white
NFC active: bg-[#1e40af] text-white
SB active: bg-[#d4af37] text-[#0a1929]
```

---

## Integration Checklist

- [ ] Backend implements `GET /api/v1/playoffs` endpoint
- [ ] Response matches `PlayoffBracketDTO` schema exactly
- [ ] All team logos are served from CDN (logo_url)
- [ ] Scores are nullable until games complete
- [ ] `is_complete` flag properly set after games finish
- [ ] `winner_team_id` matches winning team's `team_id`
- [ ] Conference filtering works correctly (side field)
- [ ] In The Hunt teams properly sorted
- [ ] Error responses include `{error: {code, message}}`
- [ ] Loading states show during data fetch
- [ ] E2E tests use `data-layer` attributes for selectors

---

## Known Behaviors

### Winner Highlighting
- Winning team shown in gold border (`border-[#d4af37]`)
- Winning score shown in gold text (`text-[#d4af37]`)
- Only applies when `is_complete === true`

### Score Display
- Shows actual scores when game is complete
- Shows `"-"` when scores are null
- Format: Large score number, small team abbreviation

### SVG Connectors
- Auto-positioned based on round layout
- AFC flows left-to-right
- NFC flows right-to-left (mirrored)
- Paths adjust based on matchup count

### Responsive Behavior
- Desktop: Side-by-side bracket layout
- Tablet: Stacked rounds with scroll
- Mobile: Full vertical stack

---

## File Locations

```
/components/PlayoffsPage.tsx          - Main page wrapper
/components/playoffs/
  ├── PlayoffBadge.tsx                - Conference/round badges
  ├── MatchupRow.tsx                  - Individual game matchup
  ├── RoundCard.tsx                   - Round container
  ├── SuperBowlCard.tsx               - Championship card
  ├── HuntCard.tsx                    - In The Hunt team card
  ├── ConferenceBracket.tsx           - Full bracket view
  ├── BracketMatchup.tsx              - Compact bracket matchup
  └── SuperBowlView.tsx               - Super Bowl tab view
/lib/mockPlayoffsApi.ts               - Mock API (replace with real)
```

---

## Next Steps

1. **Backend Team:**
   - Implement `GET /api/v1/playoffs` endpoint
   - Match exact schema from this document
   - Add proper error handling
   - Set up CDN for team logos

2. **Frontend Team:**
   - Replace `mockPlayoffsApi.ts` with real API calls
   - Add authentication headers if needed
   - Test error states with real backend
   - Verify loading states timing

3. **QA Team:**
   - Test all three view modes
   - Verify winner highlighting
   - Check responsive behavior
   - Test error/retry flow
   - Validate data-layer attributes

---

**Design Status:** ✅ LOCKED - Do not modify visual design without version bump  
**API Status:** 📋 Ready for implementation  
**Integration Status:** 🔌 Hooks in place, awaiting backend  

---
