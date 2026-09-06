# Trade Engine Integration Progress

## Current Status: 75% Complete ✅

### ✅ Completed (Step 1 & 2)

#### Backend API Endpoints
- ✅ `GET /api/v1/teams` - List all teams
- ✅ `GET /api/v1/teams/{id}/roster` - Get team roster
- ✅ `GET /api/v1/teams/{id}/picks` - Get team draft picks
- ✅ `GET /api/v1/season/current` - Get season context
- ✅ All endpoints registered in `app/ui/api.py`

#### Frontend API Client
- ✅ TypeScript interfaces added (`Team`, `Player`, `DraftPick`, `SeasonContext`)
- ✅ Function implementations:
  - `getAllTeams()`
  - `getTeamRoster(teamId, season)`
  - `getTeamPicks(teamId, season)`
  - `getCurrentSeason()`
- ✅ Error handling implemented

### ⏳ Remaining (Step 3)

#### Wire TradeBox Component
The component needs updates in `app/ui/figma-v2/src/components/gm/TradeBox.tsx`:

1. **Update imports** (Line 4):
   ```typescript
   // Replace:
   import { getAllTeams, submitTradeOffer, TradeAsset, TradeOffer, TradeResponse } from '../../lib/mockGMApi';
   
   // With:
   import { 
     proposeTrade, 
     getTradeValuePreview,
     getAllTeams as getAllTeamsAPI,
     getTeamRoster,
     getTeamPicks,
     getCurrentSeason,
     TradeAsset,
     Team,
     Player as APIPlayer,
     DraftPick as APIDraftPick
   } from '../../lib/tradeApi';
   ```

2. **Add new state variables**:
   ```typescript
   const [currentSeason, setCurrentSeason] = useState<number>(2025);
   const [userTeamId, setUserTeamId] = useState<number>(1);
   const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
   const [teamMap, setTeamMap] = useState<Team[]>([]);
   const [userPlayers, setUserPlayers] = useState<any[]>([]);
   const [userPicks, setUserPicks] = useState<any[]>([]);
   const [otherTeamPlayers, setOtherTeamPlayers] = useState<any[]>([]);
   const [otherTeamPicks, setOtherTeamPicks] = useState<any[]>([]);
   ```

3. **Update loadTeams()**:
   ```typescript
   const loadTeams = async () => {
     try {
       const context = await getCurrentSeason();
       setCurrentSeason(context.season);
       setUserTeamId(context.current_user_team_id);
       
       const teamList = await getAllTeamsAPI();
       setTeamMap(teamList);
       setTeams(teamList.map(t => t.name));
       
       // Load user's roster and picks
       const [roster, picks] = await Promise.all([
         getTeamRoster(context.current_user_team_id, context.season),
         getTeamPicks(context.current_user_team_id, context.season)
       ]);
       setUserPlayers(roster);
       setUserPicks(picks);
     } catch (err) {
       console.error('Failed to load teams:', err);
       toast.error('Failed to load team data');
     }
   };
   ```

4. **Add team selection handler**:
   ```typescript
   const handleTeamChange = async (teamName: string) => {
     setSelectedTeam(teamName);
     const team = teamMap.find(t => t.name === teamName);
     if (team) {
       setSelectedTeamId(team.id);
       
       try {
         const [roster, picks] = await Promise.all([
           getTeamRoster(team.id, currentSeason),
           getTeamPicks(team.id, currentSeason)
         ]);
         setOtherTeamPlayers(roster);
         setOtherTeamPicks(picks);
       } catch (err) {
         console.error('Failed to load team data:', err);
         toast.error('Failed to load team roster');
       }
     }
   };
   ```

5. **Update handleSubmitTrade()** to use real API

6. **Add value preview** via useEffect

7. **Update UI** to use real data instead of MOCK_*

### 📝 Files Modified So Far
- ✅ `app/ui/api_trades.py` - Added 4 new endpoints
- ✅ `app/ui/api.py` - Registered new routers
- ✅ `app/ui/figma-v2/src/lib/tradeApi.ts` - Added data fetching functions

### 📝 Files to Modify
- ⏳ `app/ui/figma-v2/src/components/gm/TradeBox.tsx` - Wire to real API

## Next Steps

1. Update TradeBox.tsx imports
2. Add new state management
3. Replace mock data with API calls
4. Update event handlers
5. Add real-time value preview
6. Test end-to-end

**Estimated Time Remaining**: 2-3 hours

## Testing Checklist

Once wired:
- [ ] Teams load correctly
- [ ] Roster loads when team selected
- [ ] Picks load when team selected
- [ ] Trade proposal works
- [ ] Value preview shows
- [ ] Error handling works
- [ ] UI updates correctly

## Notes

The component structure is already good - we just need to:
1. Replace mock API calls with real ones
2. Map the data properly
3. Handle loading/error states
4. Connect to the valuation API

The hardest part is done (backend is complete)!
