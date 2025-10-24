# Professional Football Stats Platform - Stats Page Redesign

## Phase 1: Main Stats Page Structure

### Overall Layout
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FRANCHISE FOOTBALL STATS                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  [Team]  [Player] ← Active  [Coach]                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Control Bar (Filter Section)                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ Team (All) ▼  Position (All) ▼  [Search player name...]  [Customize Player Stats] ⚙️ │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Data Table (Scrollable)                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ Player Name* │ Team │ Pos │ OVR │ Pass Yds │ Rush Yds │ Rec Yds │ Tackles │ ... │ │
│  │ (Sticky)     │      │     │     │          │          │         │         │     │ │
│  │ Josh Allen   │ BUF  │ QB  │ 89  │ 4,407    │ 524      │ 0       │ 0       │ ... │ │
│  │ Derrick Henry│ TEN  │ RB  │ 87  │ 0        │ 1,538    │ 0       │ 0       │ ... │ │
│  │ Davante Adams│ LV   │ WR  │ 91  │ 0        │ 0        │ 1,553   │ 0       │ ... │ │
│  │ Aaron Donald │ LAR  │ DT  │ 95  │ 0        │ 0        │ 0       │ 68      │ ... │ │
│  │ ...          │ ...  │ ... │ ... │ ...      │ ...      │ ...     │ ...     │ ... │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│  * Sticky column - remains visible during horizontal scroll                      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Tab-Specific Filter Controls

#### Team Tab Controls:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Conference (All) ▼  Division (All) ▼  [Search team name...]  [Customize Team Stats] ⚙️ │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Player Tab Controls (Default):
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Team (All) ▼  Position (All) ▼  [Search player name...]  [Customize Player Stats] ⚙️ │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Coach Tab Controls:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Team (All) ▼  Role (HC/OC/DC) ▼  [Search coach name...]  [Customize Coach Stats] ⚙️ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 2: "Customize Stats" Modal Design

### Modal Structure
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Customize Stats                                                              ✕ │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   Column A      │  │   Column B      │  │   Column C      │                │
│  │ Stat Categories │  │   Stat List      │  │ Selected Stats  │                │
│  │                 │  │                 │  │ & Reorder       │                │
│  │ [Search all     │  │ QB — Passing    │  │ Selected Stats  │                │
│  │  player stats...]│  │ (Selected)     │  │                 │                │
│  │                 │  │                 │  │ Drag and drop   │                │
│  │ ▼ Core Identity │  │ Base:           │  │ to reorder      │                │
│  │   & Participation│  │ ☑ qb_pass_att   │  │ columns in      │                │
│  │   • QB — passing │  │   Pass Attempts │  │ main table      │                │
│  │   • QB — rushing │  │ ☑ qb_pass_cmp   │  │                 │                │
│  │   • RB — rushing │  │   Completions   │  │ ☑ Player Name   │                │
│  │   • WR — receiving│  │ ☑ qb_pass_yds   │  │ ☑ Team          │                │
│  │   • TE — receiving│  │   Pass Yards    │  │ ☑ Position      │                │
│  │                   │  │ ☑ qb_pass_td   │  │ ☑ Overall       │                │
│  │ ▼ Defense        │  │   Pass TDs      │  │ ☑ Pass Attempts │                │
│  │   • Coverage     │  │ ☑ qb_pass_int   │  │ ☑ Completions   │                │
│  │   • Pass Rush    │  │   Interceptions │  │ ☑ Pass Yards    │                │
│  │   • Run Defense  │  │                 │  │ ☑ Pass TDs      │                │
│  │                   │  │ Derived:       │  │ ☑ Interceptions │                │
│  │ ▼ Special Teams  │  │ ☑ qb_cmp_pct   │  │ ☑ Completion %  │                │
│  │   • Kicking      │  │   Completion %  │  │ ☑ Passer Rating │                │
│  │   • Punting      │  │ ☑ qb_pass_rtg  │  │ ☑ Rush Attempts │                │
│  │   • Returns      │  │   Passer Rating │  │ ☑ Rush Yards    │                │
│  │                   │  │ ☑ qb_yds_att   │  │ ☑ Rush TDs      │                │
│  │ ▼ Advanced       │  │   Yds/Attempt  │  │ ☑ Receiving TDs │                │
│  │   • Situational  │  │ ☑ qb_td_pct    │  │ ☑ Tackles       │                │
│  │   • Red Zone     │  │   TD %          │  │ ☑ Sacks          │                │
│  │   • Third Down   │  │                 │  │ ☑ Interceptions │                │
│  │                   │  │                 │  │                 │                │
│  │ ▼ Team Context   │  │                 │  │                 │                │
│  │   • Snap Counts  │  │                 │  │                 │                │
│  │   • Usage Rates  │  │                 │  │                 │                │
│  │                   │  │                 │  │                 │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                    [Cancel]  [Apply]                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Column Breakdowns

#### Column A: Stat Categories (Left Panel)
**Search Functionality:**
- Real-time filtering across all stats in Columns A and B
- Searches both category names and individual stat names

**Category Hierarchy (Player Stats):**
```
Core Identity & Participation
├── QB — passing
├── QB — rushing/scramble  
├── RB — rushing
├── WR — receiving
├── TE — receiving
└── OL — blocking

Defense
├── Coverage (DB/LB)
├── Pass Rush (DL/LB)
└── Run Defense (DL/LB)

Special Teams
├── Kicking (K)
├── Punting (P)
└── Returns (KR/PR)

Advanced Metrics
├── Situational
├── Red Zone
└── Third Down

Team Context
├── Snap Counts
└── Usage Rates
```

#### Column B: Stat List (Middle Panel)
**Dynamic Content Based on Selected Category:**

**QB — Passing Example (Selected):**
```
Base Stats:
☑ qb_pass_att     Pass Attempts
☑ qb_pass_cmp     Completions  
☑ qb_pass_yds     Pass Yards
☑ qb_pass_td      Pass TDs
☑ qb_pass_int     Interceptions
☐ qb_sacks_taken  Sacks Taken

Derived Stats:
☑ qb_cmp_pct      Completion Percentage
☑ qb_pass_rtg     Passer Rating
☑ qb_yds_att      Yards per Attempt
☑ qb_td_pct       TD Percentage
☐ qb_int_pct      INT Percentage
```

#### Column C: Selected Stats & Reorder (Right Panel)
**Draggable Interface:**
```
Selected Stats (15 items shown)

☑ Player Name     [≡] [✕]
☑ Team           [≡] [✕]  
☑ Position       [≡] [✕]
☑ Overall        [≡] [✕]
☑ Pass Attempts  [≡] [✕]
☑ Completions    [≡] [✕]
☑ Pass Yards     [≡] [✕]
☑ Pass TDs       [≡] [✕]
☑ Interceptions  [≡] [✕]
☑ Completion %   [≡] [✕]
☑ Passer Rating  [≡] [✕]
☑ Rush Attempts  [≡] [✕]
☑ Rush Yards     [≡] [✕]
☑ Rush TDs       [≡] [✕]
☑ Receiving TDs  [≡] [✕]

[≡] = Drag handle
[✕] = Remove button
```

---

## Tab-Specific Category Variations

### Team Tab Categories:
```
Identity & Record
├── Basic Info
├── Win/Loss Record
└── Division Standing

Team Offense
├── Passing Offense
├── Rushing Offense
├── Scoring Offense
└── Efficiency Metrics

Team Defense  
├── Pass Defense
├── Run Defense
├── Scoring Defense
└── Turnover Defense

Special Teams
├── Kicking Game
├── Punting Game
└── Return Game

Situational
├── Red Zone
├── Third Down
└── Fourth Down
```

### Coach Tab Categories:
```
Identity & Record
├── Basic Info
├── Career Record
└── Current Season

Coaching Performance
├── Win Percentage
├── Playoff Record
└── Championship Record

Team Management
├── Player Development
├── Roster Decisions
└── Game Management

Advanced Metrics
├── Situational Coaching
├── Clock Management
└── Challenge Success
```

---

## Key Design Features

### 1. Responsive Design
- Modal scales appropriately for different screen sizes
- Horizontal scrolling indicators on main table
- Sticky first column for easy reference

### 2. User Experience
- Real-time search across all stats
- Visual feedback for selections
- Clear drag-and-drop indicators
- Intuitive category organization

### 3. Performance Considerations
- Lazy loading of stat categories
- Efficient search filtering
- Smooth drag-and-drop animations
- Minimal re-renders during interactions

### 4. Accessibility
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support
- Clear focus indicators

This design provides the granular control that sports analysts and scouts need while maintaining an intuitive interface for power users.
