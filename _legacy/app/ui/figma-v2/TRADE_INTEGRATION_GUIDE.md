# Trade Engine Frontend Integration Guide

## Overview
The Trade Engine backend is fully implemented and ready. This guide explains how to connect the Figma UI to the backend.

## Current Status

### ✅ Backend (COMPLETE)
- **Trade Models**: `app/models/trade.py`, `app/models/trade_block.py`
- **Valuation Service**: `app/services/trade_value.py`
- **Trade Engine**: `app/services/trade_engine.py`
- **API Endpoints**: `app/ui/api_trades.py` (FastAPI routes)
- **API Client**: `app/ui/figma-v2/src/lib/tradeApi.ts` (TypeScript client)

### 🔄 Frontend (NEEDS WIRING)
- **TradeBox Component**: `app/ui/figma-v2/src/components/gm/TradeBox.tsx`
  - Currently uses mock data (`mockGMApi.ts`)
  - Needs to call real backend API (`tradeApi.ts`)

## Integration Steps

### Step 1: Replace Mock API Calls

In `TradeBox.tsx`, replace:
```typescript
import { getAllTeams, submitTradeOffer, TradeAsset, TradeOffer, TradeResponse } from '../../lib/mockGMApi';
```

With:
```typescript
import { proposeTrade, getTradeValuePreview, TradeAsset, TradeProposalRequest, TradeProposalResponse } from '../../lib/tradeApi';
```

### Step 2: Update Trade Submission Logic

Replace the `handleSubmitTrade` function to use the real API:

```typescript
const handleSubmitTrade = async () => {
  if (!selectedTeam) {
    toast.error('Please select a team to trade with');
    return;
  }
  if (offeringAssets.length === 0 || receivingAssets.length === 0) {
    toast.error('Please add assets to both sides of the trade');
    return;
  }

  setSubmitting(true);
  try {
    // Map frontend assets to backend format
    const fromPlayers = offeringAssets
      .filter(a => a.type === 'player')
      .map(a => parseInt(a.id.replace('p', ''))); // Convert 'p1' -> 1
    
    const fromPicks = offeringAssets
      .filter(a => a.type === 'pick')
      .map(a => ({ round: a.round!, slot: a.pickNumber || 1 })); // Adapt to pickNumber mapping

    const toPlayers = receivingAssets
      .filter(a => a.type === 'player')
      .map(a => parseInt(a.id.replace('o', '')));

    const toPicks = receivingAssets
      .filter(a => a.type === 'pick')
      .map(a => ({ round: a.round!, slot: a.pickNumber || 1 }));

    const request: TradeProposalRequest = {
      season: 2025, // Get from current season context
      from_team_id: 1, // Get current user's team ID
      to_team_id: 2, // Get selected team ID from teamName -> id mapping
      from_assets: {
        players: fromPlayers,
        picks: fromPicks
      },
      to_assets: {
        players: toPlayers,
        picks: toPicks
      }
    };

    const response = await proposeTrade(request);
    
    if (response.error) {
      toast.error(response.error);
    } else if (response.status === 'ACCEPTED') {
      toast.success('Trade accepted!');
      // Clear the trade
      setOfferingAssets([]);
      setReceivingAssets([]);
      setSelectedTeam('');
    } else if (response.status === 'COUNTER') {
      toast.info('Counter-offer suggested: ' + response.message);
      // Show counter offer UI
    } else {
      toast.warning('Trade rejected: ' + response.message);
    }
  } catch (err) {
    console.error('Failed to submit trade:', err);
    toast.error('Failed to submit trade offer');
  } finally {
    setSubmitting(false);
  }
};
```

### Step 3: Add Real-Time Value Preview

Update the component to show live trade value as assets are added:

```typescript
useEffect(() => {
  if (selectedTeam && (offeringAssets.length > 0 || receivingAssets.length > 0)) {
    const fetchValue = async () => {
      const preview = await getTradeValuePreview(
        2025, // season
        1,    // from_team_id  
        2,    // to_team_id
        offeringAssets.filter(a => a.type === 'player').map(a => parseInt(a.id.replace('p', ''))),
        receivingAssets.filter(a => a.type === 'player').map(a => parseInt(a.id.replace('o', ''))),
        offeringAssets.filter(a => a.type === 'pick').map(a => ({ round: a.round!, slot: a.pickNumber || 1 })),
        receivingAssets.filter(a => a.type === 'pick').map(a => ({ round: a.round!, slot: a.pickNumber || 1 }))
      );
      
      // Display preview.from_value, preview.to_value, preview.ratio in UI
    };
    fetchValue();
  }
}, [offeringAssets, receivingAssets, selectedTeam]);
```

### Step 4: Data Mapping

You'll need to:
1. Load real player data from your API
2. Load real draft picks from your API
3. Map team names to team IDs
4. Get current season from context

Example API endpoints to add:
- `GET /api/v1/teams` - List all teams
- `GET /api/v1/teams/{id}/roster` - Get team roster
- `GET /api/v1/teams/{id}/picks` - Get team draft picks
- `GET /api/v1/season/current` - Get current season info

## Backend API Reference

### POST `/api/v1/trades/propose`
Propose a new trade.

**Request:**
```json
{
  "season": 2025,
  "from_team_id": 1,
  "to_team_id": 2,
  "from_assets": {
    "players": [1, 2, 3],
    "picks": [{"round": 1, "slot": 5}]
  },
  "to_assets": {
    "players": [4],
    "picks": []
  }
}
```

**Response:**
```json
{
  "ok": true,
  "proposal_id": 123,
  "status": "PENDING",
  "message": "Offer within fair band. Counterparty likely to accept.",
  "from_value": 850.5,
  "to_value": 920.3,
  "ratio": 0.924
}
```

### POST `/api/v1/trades/accept`
Accept a trade proposal.

**Request:**
```json
{
  "proposal_id": 123
}
```

**Response:**
```json
{
  "ok": true,
  "proposal_id": 123,
  "status": "ACCEPTED"
}
```

### GET `/api/v1/trades/value_preview`
Get instant trade value analysis.

**Query Params:**
- `season`: 2025
- `from_team_id`: 1
- `to_team_id`: 2
- `from_players`: "1,2,3"
- `to_players`: "4"
- `from_picks`: "1-5"
- `to_picks`: ""

**Response:**
```json
{
  "from_value": 850.5,
  "to_value": 920.3,
  "ratio": 0.924
}
```

### GET `/api/v1/trades/block`
List all items on the trade block.

**Response:**
```json
{
  "players": [
    {"team_id": 1, "player_id": 5, "note": "Looking for picks"}
  ],
  "picks": [
    {"team_id": 2, "round": 3, "slot": 10, "note": "For sale"}
  ]
}
```

## Testing

1. Start the backend server:
   ```bash
   uvicorn app.ui.api:app --reload
   ```

2. Test the API directly:
   ```bash
   curl -X POST http://localhost:8000/api/v1/trades/propose \
     -H "Content-Type: application/json" \
     -d '{"season":2025,"from_team_id":1,"to_team_id":2,"from_assets":{"players":[],"picks":[]},"to_assets":{"players":[],"picks":[]}}'
   ```

3. Start the frontend:
   ```bash
   cd app/ui/figma-v2
   npm run dev
   ```

4. Navigate to GM Desk and test the Trade Box UI

## Next Steps

1. **Immediate**: Wire TradeBox.tsx to use `tradeApi.ts` instead of `mockGMApi.ts`
2. **Then**: Add API endpoints for fetching teams, rosters, and picks
3. **Then**: Add value preview in real-time as assets are selected
4. **Finally**: Test end-to-end trade flow with real data

## Architecture

```
Frontend (React/Vite)           Backend (FastAPI)
━━━━━━━━━━━━━━━━━━━           ━━━━━━━━━━━━━━━━━━━

TradeBox.tsx ──────(fetch)──> API Endpoints
  ↓                            ↓
tradeApi.ts              trade_engine.py
  ↓                            ↓
                           trade_value.py
                              ↓
                          SQLModel DB
```

The backend is ready and fully functional. The frontend just needs to call the real API instead of mocks!
