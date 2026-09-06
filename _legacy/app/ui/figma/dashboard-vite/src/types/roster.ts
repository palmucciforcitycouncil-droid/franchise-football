// DTOs for Roster and Depth Chart functionality per GDD v3.2 §9.2.2

export interface PlayerRow {
  player_id: string;
  name: string;
  pos: string;
  age: number;
  ovr: number;
  pot: number;
  contract: {
    years: number;
    aav: number;
    exp: number; // expiration year
  };
  status: {
    injury?: string;
    eta?: string;
  };
}

export interface DepthSlot {
  unit: string; // "OFF", "DEF", "ST"
  pos: string; // "QB", "RB", "WR", etc.
  slot: number; // 1, 2, 3, etc.
  player_id: string;
}

export interface ContractSummary {
  cap_space: number;
  top_contracts: Array<{
    player_id: string;
    name: string;
    pos: string;
    aav: number;
  }>;
  expiring: Array<{
    player_id: string;
    name: string;
    pos: string;
    aav: number;
    exp_year: number;
  }>;
}

export interface InjuryRow {
  player_id: string;
  type: string;
  severity: string;
  weeks_remaining: number;
  rtp_penalty: number; // 0-1 penalty multiplier
}

// Position buckets and depth targets per GDD v3.2 §3.1.8.1
export interface PositionBucket {
  position: string;
  unit: 'OFF' | 'DEF' | 'ST';
  depth_target: number;
  secondary_positions?: string[];
}

export const POSITION_BUCKETS: PositionBucket[] = [
  // Offense
  { position: 'QB', unit: 'OFF', depth_target: 2 },
  { position: 'RB', unit: 'OFF', depth_target: 3 },
  { position: 'WR', unit: 'OFF', depth_target: 5 },
  { position: 'TE', unit: 'OFF', depth_target: 2 },
  { position: 'C', unit: 'OFF', depth_target: 1 },
  { position: 'LG', unit: 'OFF', depth_target: 1 },
  { position: 'RG', unit: 'OFF', depth_target: 1 },
  { position: 'LT', unit: 'OFF', depth_target: 1 },
  { position: 'RT', unit: 'OFF', depth_target: 1 },
  
  // Defense
  { position: 'DE', unit: 'DEF', depth_target: 2 },
  { position: 'DT', unit: 'DEF', depth_target: 2 },
  { position: 'MLB', unit: 'DEF', depth_target: 1 },
  { position: 'OLB', unit: 'DEF', depth_target: 2 },
  { position: 'CB', unit: 'DEF', depth_target: 4 },
  { position: 'FS', unit: 'DEF', depth_target: 1 },
  { position: 'SS', unit: 'DEF', depth_target: 1 },
  
  // Special Teams
  { position: 'K', unit: 'ST', depth_target: 1 },
  { position: 'P', unit: 'ST', depth_target: 1 },
  { position: 'KR', unit: 'ST', depth_target: 1 },
  { position: 'PR', unit: 'ST', depth_target: 1 },
  { position: 'LS', unit: 'ST', depth_target: 1 },
];

// Depth chart auto-fill rules per GDD v3.2 §5.2
export interface AutoFillRule {
  sortBy: 'OVR' | 'STA' | 'AGE' | 'PLAYER_ID';
  order: 'ASC' | 'DESC';
}

export const AUTO_FILL_RULES: AutoFillRule[] = [
  { sortBy: 'OVR', order: 'DESC' },
  { sortBy: 'STA', order: 'DESC' },
  { sortBy: 'AGE', order: 'ASC' },
  { sortBy: 'PLAYER_ID', order: 'ASC' },
];

// Eligibility rules per GDD v3.2 §5.2
export interface EligibilityRule {
  mustMatchPosition: boolean;
  injuryGating: boolean;
  allowQuestionable: boolean;
  excludeOutOfSeason: boolean;
}

export const ELIGIBILITY_RULES: EligibilityRule = {
  mustMatchPosition: true,
  injuryGating: true,
  allowQuestionable: true,
  excludeOutOfSeason: true,
};
