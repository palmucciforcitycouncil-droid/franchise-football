# Next Steps for Trade Engine Integration

## Current Status
✅ Backend Trade Engine is complete and fully functional  
✅ TypeScript API client (`tradeApi.ts`) is ready  
✅ Frontend UI structure is in place  
⏳ Frontend-to-Backend wiring needs completion

## Required Next Steps

### 1. Create API Endpoints for Data Fetching (Backend)

The frontend needs these endpoints to populate the Trade Box UI:

#### A. Get All Teams
```python
# In app/ui/api_trades.py or new file
GET /api/v1/teams
Response: [
  {"id": 1, "name": "New England Patriots", "city": "New England", ...},
  {"id": 2, "name": "Buffalo Bills", "city": "Buffalo", ...},
  ...
]
```

#### B. Get Team Roster
```python
GET /api/v1/teams/{team_id}/roster?season=2025
Response: [
  {"id": 1, "name": "K. Benton", "position": "WR", "overall": 87, ...},
  {"id": 2, "name": "T. Morrow", "position": "RB", "overall": 82, ...},
  ...
]
```

#### C. Get Team Draft Picks
```python
GET /api/v1/teams/{team_id}/picks?season=2025
Response: [
  {"round": 1, "slot": 18, "year": 2025},
  {"round": 2, "slot": 50, "year": 2025},
  ...
]
```

#### D. Get Current Season Context
```python
GET /api/v1/season/current
Response: {"season": 2025, "week": 5, "current_user_team_id": 1}
```

### 2. Update Frontend API Client (`tradeApi.ts`)

Add functions for fetching data:
```typescript
export const getAllTeams = async (): Promise<Team[]> => {
  const response = await fetch(`${API_BASE}/teams`);
  return await response.json();
};

export const getTeamRoster = async (teamId: number, season: number): Promise<Player[]> => {
  const response = await fetch(`${API_BASE}/teams/${teamId}/roster?season=${season}`);
  return await response.json();
};

export const getTeamPicks = async (teamId: number, season: number): Promise<DraftPick[]> => {
  const response = await fetch(`${API_BASE}/teams/${teamId}/picks?season=${season}`);
  return await response.json();
};

export const getCurrentSeason = async (): Promise<SeasonContext> => {
  const response = await fetch(`${API_BASE}/season/current`);
  return await response.json();
};
```

### 3. Wire TradeBox Component to Real API

Update `TradeBox.tsx`:

```typescript
// Replace import
import { proposeTrade, getTradeValuePreview, getAllTeams, getTeamRoster, getTeamPicks, getCurrentSeason } from '../../lib/tradeApi';

// In component:
const [currentSeason, setCurrentSeason] = useState<number>(2025);
const [userTeamId, setUserTeamId] = useState<number>(1);
const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);

useEffect(() => {
  loadSeasonContext();
  loadTeams();
}, []);

const loadSeasonContext = async () => {
  const context = await getCurrentSeason();
  setCurrentSeason(context.season);
  setUserTeamId(context.current_user_team_id);
};

const loadTeams = async () => {
  const teamList = await getAllTeams();
  setTeams(teamList.map(t => t.name));
  setTeamMap(teamList); // Store name -> id mapping
};

// When team selected:
const handleTeamChange = (teamName: string) => {
  setSelectedTeam(teamName);
  const team = teamMap.find(t => t.name === teamName);
  if (team) {
    setSelectedTeamId(team.id);
    loadTeamData(team.id);
  }
};

const loadTeamData = async (teamId: number) => {
  // Load roster and picks for the selected team
  const roster = await getTeamRoster(teamId, currentSeason);
  const picks = await getTeamPicks(teamId, currentSeason);
  // Update state with real data
};

// Update handleSubmitTrade to use real API
const handleSubmitTrade = async () => {
  // ... existing validation ...
  
  const request: TradeProposalRequest = {
    season: currentSeason,
    from_team_id: userTeamId,
    to_team_id: selectedTeamId!,
    from_assets: {
      players: offeringAssets.filter(a => a.type === 'player').map(a => parseInt(a.id)),
      picks: offeringAssets.filter(a => a.type === 'pick').map(a => ({ 
        round: a.round!, 
        slot: a.pickNumber || 1 
      }))
    },
    to_assets: {
      players: receivingAssets.filter(a => a.type === 'player').map(a => parseInt(a.id)),
      picks: receivingAssets.filter(a => a.type === 'pick').map(a => ({ 
        round: a.round!, 
        slot: a.pickNumber || 1 
      }))
    }
  };

  const response = await proposeTrade(request);
  // Handle response...
};
```

### 4. Add Real-Time Value Preview

Show trade values as assets are added:

```typescript
const [tradeValue, setTradeValue] = useState<{from: number, to: number, ratio: number} | null>(null);

useEffect(() => {
  if (selectedTeamId && (offeringAssets.length > 0 || receivingAssets.length > 0)) {
    loadValuePreview();
  }
}, [offeringAssets, receivingAssets, selectedTeamId]);

const loadValuePreview = async () => {
  const preview = await getTradeValuePreview(
    currentSeason,
    userTeamId,
    selectedTeamId!,
    offeringAssets.filter(a => a.type === 'player').map(a => parseInt(a.id)),
    receivingAssets.filter(a => a.type === 'player').map(a => parseInt(a.id)),
    offeringAssets.filter(a => a.type === 'pick').map(a => ({ round: a.round!, slot: a.pickNumber || 1 })),
    receivingAssets.filter(a => a.type === 'pick').map(a => ({ round: a.round!, slot: a.pickNumber || 1 }))
  );
  
  setTradeValue({
    from: preview.from_value,
    to: preview.to_value,
    ratio: preview.ratio
  });
};
```

## Implementation Order

1. **Backend API Endpoints** (1-2 hours)
   - Create endpoints for teams, roster, picks, season context
   - Add tests for new endpoints

2. **Update Frontend API Client** (30 min)
   - Add functions to `tradeApi.ts`
   - Export TypeScript interfaces

3. **Wire TradeBox Component** (2-3 hours)
   - Replace mock data with real API calls
   - Add loading states
   - Handle errors gracefully

4. **Add Value Preview** (1 hour)
   - Implement real-time value calculation
   - Display in UI

5. **Testing** (1 hour)
   - Test complete trade flow
   - Test edge cases (empty trades, invalid teams, etc.)

## Estimated Time: 5-7 hours

## Quick Start

Once the backend endpoints are created, the integration should be straightforward:

1. Import new API functions
2. Replace mock data with real data
3. Update event handlers to use real API
4. Test end-to-end

The architecture is sound - we just need to connect the pieces!
