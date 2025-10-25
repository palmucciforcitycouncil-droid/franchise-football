// Real API for Trade operations - connects to backend

export interface TradeAsset {
  type: 'player' | 'pick';
  id: string;
  name: string;
  position?: string;
  overall?: number;
  year?: number;
  round?: number;
  pickNumber?: number;
}

export interface TradeProposalRequest {
  season: number;
  from_team_id: number;
  to_team_id: number;
  from_assets: {
    players: number[];
    picks: { round: number; slot: number }[];
  };
  to_assets: {
    players: number[];
    picks: { round: number; slot: number }[];
  };
}

export interface TradeProposalResponse {
  ok?: boolean;
  proposal_id?: number;
  status?: string;
  message?: string;
  from_value?: number;
  to_value?: number;
  ratio?: number;
  error?: string;
}

export interface TradeAcceptRequest {
  proposal_id: number;
}

export interface TradeValuePreviewResponse {
  from_value: number;
  to_value: number;
  ratio: number;
  error?: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

// Propose a trade
export const proposeTrade = async (request: TradeProposalRequest): Promise<TradeProposalResponse> => {
  const response = await fetch(`${API_BASE}/trades/propose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return await response.json();
};

// Accept a trade proposal
export const acceptTrade = async (request: TradeAcceptRequest): Promise<any> => {
  const response = await fetch(`${API_BASE}/trades/accept`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return await response.json();
};

// Get value preview for a potential trade
export const getTradeValuePreview = async (
  season: number,
  fromTeamId: number,
  toTeamId: number,
  fromPlayers: number[] = [],
  toPlayers: number[] = [],
  fromPicks: { round: number; slot: number }[] = [],
  toPicks: { round: number; slot: number }[] = []
): Promise<TradeValuePreviewResponse> => {
  const params = new URLSearchParams({
    season: season.toString(),
    from_team_id: fromTeamId.toString(),
    to_team_id: toTeamId.toString(),
    from_players: fromPlayers.join(','),
    to_players: toPlayers.join(','),
    from_picks: fromPicks.map(p => `${p.round}-${p.slot}`).join(','),
    to_picks: toPicks.map(p => `${p.round}-${p.slot}`).join(','),
  });

  const response = await fetch(`${API_BASE}/trades/value_preview?${params}`);
  return await response.json();
};

// Get trade block items
export const getTradeBlock = async (season: number): Promise<any> => {
  const response = await fetch(`${API_BASE}/trades/block?season=${season}`);
  return await response.json();
};
