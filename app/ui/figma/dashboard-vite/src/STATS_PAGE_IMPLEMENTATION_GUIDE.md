# Professional Football Stats Platform - Stats Page Redesign

## 🎯 Overview

This is a comprehensive redesign of the Stats Page for the Professional Football Stats Platform, specifically designed for **Sports Analysts, Scouts, and Power Users** who require precise, granular control over statistical views and advanced metrics.

## 🏗️ Architecture

### Phase 1: Main Stats Page Structure
- **Tab-based Navigation**: Team, Player, Coach tabs with dynamic filtering
- **Adaptive Control Bar**: Changes based on selected tab
- **Sticky Column Table**: First column remains visible during horizontal scroll
- **Real-time Filtering**: Search and dropdown filters for each tab type

### Phase 2: Customize Stats Modal
- **Three-Column Layout**: Categories, Stat List, Selected Stats
- **Real-time Search**: Filters across all stats and categories
- **Drag-and-Drop Reordering**: Intuitive column management
- **Tab-Specific Categories**: Different stat hierarchies for each tab

## 📊 Key Features

### 1. Tab-Specific Filtering
Each tab provides contextually relevant filters:

**Team Tab:**
- Conference (AFC/NFC)
- Division (All 8 divisions)
- Team name search

**Player Tab (Default):**
- Team selection
- Position (QB, RB, WR, DB, K, etc.)
- Player name search

**Coach Tab:**
- Team selection
- Role (HC/OC/DC)
- Coach name search

### 2. Customize Stats Modal

#### Column A: Stat Categories
- **Hierarchical Organization**: Two-level category structure
- **Real-time Search**: Searches across categories and stats
- **Tab-Specific Categories**: Different hierarchies for Team/Player/Coach

#### Column B: Stat List
- **Dynamic Content**: Shows stats for selected category
- **Grouped Display**: Base stats and derived stats separated
- **Checkbox Selection**: Easy stat selection/deselection

#### Column C: Selected Stats & Reorder
- **Drag-and-Drop**: Reorder columns with visual feedback
- **Quick Remove**: X button for easy deselection
- **Visual Indicators**: Clear drag handles and hover states

## 🎨 Design Specifications

### Visual Design
- **Clean, Professional Interface**: Optimized for data analysis
- **High Contrast**: Easy reading for long sessions
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Accessibility**: Keyboard navigation and screen reader support

### User Experience
- **Intuitive Navigation**: Clear visual hierarchy
- **Efficient Workflows**: Minimal clicks for common tasks
- **Visual Feedback**: Clear selection states and hover effects
- **Performance**: Smooth animations and responsive interactions

## 📁 File Structure

```
components/
├── StatsPage.tsx              # Main stats page component
├── CustomizeStatsModal.tsx    # Modal for stat customization
└── ui/
    ├── button.tsx            # Button component
    ├── input.tsx             # Input component
    ├── select.tsx            # Select dropdown component
    ├── checkbox.tsx          # Checkbox component
    └── utils.ts              # Utility functions
```

## 🔧 Technical Implementation

### React Components
- **Functional Components**: Modern React with hooks
- **TypeScript**: Full type safety
- **State Management**: Local state with React hooks
- **Drag-and-Drop**: @hello-pangea/dnd for smooth interactions

### Styling
- **Tailwind CSS**: Utility-first CSS framework
- **Responsive Design**: Mobile-first approach
- **Component Library**: Reusable UI components
- **Custom Utilities**: Tailwind merge for class management

### Data Structure
```typescript
interface StatItem {
  id: string;
  name: string;
  description: string;
  category: string;
  subcategory?: string;
}

interface Category {
  id: string;
  name: string;
  subcategories: Subcategory[];
}
```

## 🎯 Tab-Specific Category Variations

### Player Tab Categories
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

### Team Tab Categories
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

### Coach Tab Categories
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

## 🚀 Usage Examples

### Basic Usage
```tsx
import { StatsPage } from './components/StatsPage';

function App() {
  return <StatsPage />;
}
```

### Custom Configuration
```tsx
<StatsPage
  defaultTab="player"
  initialStats={['player_name', 'team', 'position', 'overall']}
  onStatsChange={(stats) => console.log('Stats changed:', stats)}
/>
```

## 🎨 Design Mockups

### Main Stats Page
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FRANCHISE FOOTBALL STATS                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  [Team]  [Player] ← Active  [Coach]                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Team (All) ▼  Position (All) ▼  [Search player name...]  [Customize Player Stats] ⚙️ │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Player Name* │ Team │ Pos │ OVR │ Pass Yds │ Rush Yds │ Rec Yds │ Tackles │ ... │ │
│  (Sticky)     │      │     │     │          │          │         │         │     │ │
│  Josh Allen   │ BUF  │ QB  │ 89  │ 4,407    │ 524      │ 0       │ 0       │ ... │ │
│  Derrick Henry│ TEN  │ RB  │ 87  │ 0        │ 1,538    │ 0       │ 0       │ ... │ │
│  Davante Adams│ LV   │ WR  │ 91  │ 0        │ 0        │ 1,553   │ 0       │ ... │ │
│  Aaron Donald │ LAR  │ DT  │ 95  │ 0        │ 0        │ 0       │ 68      │ ... │ │
│  ...          │ ...  │ ... │ ... │ ...      │ ...      │ ...     │ ...     │ ... │ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Customize Stats Modal
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

## 🔍 Key Design Features

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

## 🎯 Target User Benefits

### Sports Analysts
- **Granular Control**: Select exactly the stats needed for analysis
- **Efficient Workflows**: Quick access to relevant data
- **Custom Views**: Save and reuse stat combinations
- **Advanced Metrics**: Access to derived and situational stats

### Scouts
- **Position-Specific Views**: Focus on relevant stats for each position
- **Comparative Analysis**: Easy comparison across players
- **Trend Analysis**: Access to historical and situational data
- **Export Capabilities**: Save custom views for reports

### Power Users
- **Customization**: Complete control over data display
- **Efficiency**: Minimal clicks for maximum functionality
- **Integration**: Works with existing workflows
- **Scalability**: Handles large datasets efficiently

## 🚀 Future Enhancements

### Phase 3: Advanced Features
- **Saved Views**: Save and share custom stat combinations
- **Export Options**: CSV, PDF, and API export capabilities
- **Advanced Filtering**: Date ranges, performance thresholds
- **Visualizations**: Charts and graphs for selected stats

### Phase 4: Integration
- **API Integration**: Real-time data updates
- **User Preferences**: Persistent customization settings
- **Collaboration**: Share views with team members
- **Mobile App**: Native mobile experience

This design provides the granular control that sports analysts and scouts need while maintaining an intuitive interface for power users. The modular architecture allows for easy extension and customization as requirements evolve.
