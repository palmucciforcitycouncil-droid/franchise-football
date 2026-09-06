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

// New interfaces for data fetching
export interface Team {
  id: number;
  name: string;
  city: string;
  abbreviation: string;
}

export interface Player {
  id: number;
  name: string;
  position: string;
  overall: number;
  age: number;
}

export interface DraftPick {
  round: number;
  slot: number;
  year: number;
}

export interface SeasonContext {
  season: number;
  week: number;
  current_user_team_id: number;
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

// New functions for data fetching

// Get all teams
export const getAllTeams = async (): Promise<Team[]> => {
  const response = await fetch(`${API_BASE}/teams/`);
  if (!response.ok) {
    throw new Error(`Failed to fetch teams: ${response.statusText}`);
  }
  return await response.json();
};

// Get team roster
export const getTeamRoster = async (teamId: number, season: number): Promise<Player[]> => {
  const response = await fetch(`${API_BASE}/teams/${teamId}/roster?season=${season}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch roster: ${response.statusText}`);
  }
  return await response.json();
};

// Get team draft picks
export const getTeamPicks = async (teamId: number, season: number): Promise<DraftPick[]> => {
  const response = await fetch(`${API_BASE}/teams/${teamId}/picks?season=${season}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch picks: ${response.statusText}`);
  }
  return await response.json();
};

// Get current season context
export const getCurrentSeason = async (): Promise<SeasonContext> => {
  const response = await fetch(`${API_BASE}/season/current`);
  if (!response.ok) {
    throw new Error(`Failed to fetch season context: ${response.statusText}`);
  }
  return await response.json();
};
