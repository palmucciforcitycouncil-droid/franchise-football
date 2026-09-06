// Mock API layer for depth chart operations
// Matches the API contract specified in requirements

export interface PlayerData {
  player_id: number;
  team_id: number;
  first_name: string;
  last_name: string;
  position: string;
  age: number;
  ratings: {
    ovr: number;
    spd: number;
    str: number;
    agi: number;
    awr: number;
    sta: number;
    thp: number;
    tha: number;
    cth: number;
    tkl: number;
  };
  status: 'Active' | 'OUT' | 'Doubtful' | 'IR' | 'PUP';
  secondary_positions: string[];
  jersey_number: number;
  injury_proneness?: number;
}

export interface DepthChartAssignment {
  slot: string;
  position_group: string;
  player_id: number | null;
  ovr_at_slot: number;
  notes: string[];
}

export interface DepthChartPayload {
  team_id: number;
  assignments: DepthChartAssignment[];
  warnings: string[];
}

export interface AutoFillOptions {
  respect_injuries: boolean;
  respect_fatigue: boolean;
  lock_starters: boolean;
  allow_cross_training: boolean;
}

// Mock roster data (45-53 players covering all positions)
const MOCK_ROSTER: PlayerData[] = [
  // QBs
  { player_id: 1, team_id: 1, first_name: 'Mac', last_name: 'Jones', position: 'QB', age: 25, jersey_number: 10, ratings: { ovr: 83, spd: 65, str: 70, agi: 68, awr: 82, sta: 85, thp: 85, tha: 84, cth: 40, tkl: 30 }, status: 'Active', secondary_positions: [], injury_proneness: 20 },
  { player_id: 2, team_id: 1, first_name: 'Bailey', last_name: 'Zappe', position: 'QB', age: 24, jersey_number: 4, ratings: { ovr: 74, spd: 70, str: 68, agi: 70, awr: 73, sta: 80, thp: 78, tha: 72, cth: 40, tkl: 30 }, status: 'Active', secondary_positions: [], injury_proneness: 15 },
  { player_id: 3, team_id: 1, first_name: 'Malik', last_name: 'Cunningham', position: 'QB', age: 23, jersey_number: 14, ratings: { ovr: 69, spd: 88, str: 65, agi: 85, awr: 68, sta: 78, thp: 72, tha: 68, cth: 45, tkl: 35 }, status: 'Active', secondary_positions: ['WR'], injury_proneness: 18 },
  
  // RBs
  { player_id: 11, team_id: 1, first_name: 'Rhamondre', last_name: 'Stevenson', position: 'RB', age: 25, jersey_number: 38, ratings: { ovr: 84, spd: 82, str: 88, agi: 80, awr: 78, sta: 86, thp: 40, tha: 40, cth: 75, tkl: 50 }, status: 'Active', secondary_positions: [], injury_proneness: 25 },
  { player_id: 12, team_id: 1, first_name: 'Ezekiel', last_name: 'Elliott', position: 'RB', age: 29, jersey_number: 15, ratings: { ovr: 79, spd: 78, str: 86, agi: 77, awr: 82, sta: 82, thp: 40, tha: 40, cth: 78, tkl: 48 }, status: 'Active', secondary_positions: [], injury_proneness: 35 },
  { player_id: 13, team_id: 1, first_name: 'Kevin', last_name: 'Harris', position: 'RB', age: 23, jersey_number: 34, ratings: { ovr: 72, spd: 84, str: 80, agi: 82, awr: 70, sta: 80, thp: 40, tha: 40, cth: 68, tkl: 45 }, status: 'Active', secondary_positions: [], injury_proneness: 20 },
  
  // WRs
  { player_id: 21, team_id: 1, first_name: 'DeVante', last_name: 'Parker', position: 'WR', age: 30, jersey_number: 1, ratings: { ovr: 80, spd: 85, str: 78, agi: 83, awr: 79, sta: 78, thp: 40, tha: 40, cth: 86, tkl: 40 }, status: 'Active', secondary_positions: [], injury_proneness: 40 },
  { player_id: 22, team_id: 1, first_name: 'Kendrick', last_name: 'Bourne', position: 'WR', age: 28, jersey_number: 84, ratings: { ovr: 77, spd: 86, str: 72, agi: 84, awr: 76, sta: 82, thp: 40, tha: 40, cth: 82, tkl: 42 }, status: 'OUT', secondary_positions: [], injury_proneness: 30 },
  { player_id: 23, team_id: 1, first_name: 'Demario', last_name: 'Douglas', position: 'WR', age: 22, jersey_number: 81, ratings: { ovr: 75, spd: 90, str: 65, agi: 88, awr: 74, sta: 85, thp: 40, tha: 40, cth: 80, tkl: 38 }, status: 'Active', secondary_positions: [], injury_proneness: 15 },
  { player_id: 24, team_id: 1, first_name: 'JuJu', last_name: 'Smith-Schuster', position: 'WR', age: 27, jersey_number: 7, ratings: { ovr: 78, spd: 84, str: 76, agi: 82, awr: 80, sta: 80, thp: 40, tha: 40, cth: 84, tkl: 40 }, status: 'Active', secondary_positions: [], injury_proneness: 28 },
  { player_id: 25, team_id: 1, first_name: 'Kayshon', last_name: 'Boutte', position: 'WR', age: 21, jersey_number: 19, ratings: { ovr: 71, spd: 87, str: 68, agi: 85, awr: 70, sta: 82, thp: 40, tha: 40, cth: 76, tkl: 38 }, status: 'Active', secondary_positions: [], injury_proneness: 18 },
  { player_id: 26, team_id: 1, first_name: 'Tyquan', last_name: 'Thornton', position: 'WR', age: 24, jersey_number: 11, ratings: { ovr: 69, spd: 95, str: 62, agi: 86, awr: 68, sta: 78, thp: 40, tha: 40, cth: 72, tkl: 35 }, status: 'Active', secondary_positions: [], injury_proneness: 22 },
  
  // TEs
  { player_id: 31, team_id: 1, first_name: 'Hunter', last_name: 'Henry', position: 'TE', age: 29, jersey_number: 85, ratings: { ovr: 82, spd: 74, str: 80, agi: 72, awr: 84, sta: 80, thp: 40, tha: 40, cth: 85, tkl: 55 }, status: 'Active', secondary_positions: [], injury_proneness: 32 },
  { player_id: 32, team_id: 1, first_name: 'Mike', last_name: 'Gesicki', position: 'TE', age: 28, jersey_number: 88, ratings: { ovr: 78, spd: 76, str: 75, agi: 74, awr: 76, sta: 82, thp: 40, tha: 40, cth: 82, tkl: 50 }, status: 'Active', secondary_positions: ['WR'], injury_proneness: 25 },
  { player_id: 33, team_id: 1, first_name: 'Pharaoh', last_name: 'Brown', position: 'TE', age: 30, jersey_number: 87, ratings: { ovr: 74, spd: 70, str: 82, agi: 68, awr: 78, sta: 78, thp: 40, tha: 40, cth: 76, tkl: 60 }, status: 'Active', secondary_positions: [], injury_proneness: 28 },
  
  // Offensive Line
  { player_id: 41, team_id: 1, first_name: 'Trent', last_name: 'Brown', position: 'T', age: 31, jersey_number: 77, ratings: { ovr: 85, spd: 60, str: 92, agi: 65, awr: 82, sta: 75, thp: 40, tha: 40, cth: 40, tkl: 70 }, status: 'Active', secondary_positions: [], injury_proneness: 38 },
  { player_id: 42, team_id: 1, first_name: 'Conor', last_name: 'McDermott', position: 'T', age: 31, jersey_number: 71, ratings: { ovr: 76, spd: 62, str: 88, agi: 64, awr: 75, sta: 78, thp: 40, tha: 40, cth: 40, tkl: 68 }, status: 'Active', secondary_positions: ['G'], injury_proneness: 30 },
  { player_id: 43, team_id: 1, first_name: 'Cole', last_name: 'Strange', position: 'G', age: 25, jersey_number: 69, ratings: { ovr: 80, spd: 65, str: 90, agi: 70, awr: 78, sta: 48, thp: 40, tha: 40, cth: 40, tkl: 72 }, status: 'Active', secondary_positions: ['C'], injury_proneness: 20 },
  { player_id: 44, team_id: 1, first_name: 'Sidy', last_name: 'Sow', position: 'G', age: 25, jersey_number: 76, ratings: { ovr: 78, spd: 64, str: 89, agi: 68, awr: 76, sta: 80, thp: 40, tha: 40, cth: 40, tkl: 70 }, status: 'Active', secondary_positions: ['T'], injury_proneness: 22 },
  { player_id: 45, team_id: 1, first_name: 'Mike', last_name: 'Onwenu', position: 'G', age: 26, jersey_number: 71, ratings: { ovr: 83, spd: 63, str: 91, agi: 67, awr: 80, sta: 82, thp: 40, tha: 40, cth: 40, tkl: 74 }, status: 'Active', secondary_positions: ['T', 'C'], injury_proneness: 18 },
  { player_id: 46, team_id: 1, first_name: 'David', last_name: 'Andrews', position: 'C', age: 32, jersey_number: 60, ratings: { ovr: 87, spd: 64, str: 88, agi: 70, awr: 88, sta: 84, thp: 40, tha: 40, cth: 40, tkl: 75 }, status: 'Active', secondary_positions: [], injury_proneness: 25 },
  { player_id: 47, team_id: 1, first_name: 'Jake', last_name: 'Andrews', position: 'C', age: 26, jersey_number: 61, ratings: { ovr: 75, spd: 65, str: 86, agi: 68, awr: 74, sta: 78, thp: 40, tha: 40, cth: 40, tkl: 70 }, status: 'Active', secondary_positions: ['G'], injury_proneness: 20 },
  
  // Defensive Line
  { player_id: 51, team_id: 1, first_name: 'Christian', last_name: 'Barmore', position: 'DT', age: 24, jersey_number: 90, ratings: { ovr: 84, spd: 72, str: 92, agi: 70, awr: 80, sta: 80, thp: 40, tha: 40, cth: 40, tkl: 82 }, status: 'Active', secondary_positions: [], injury_proneness: 22 },
  { player_id: 52, team_id: 1, first_name: 'Davon', last_name: 'Godchaux', position: 'DT', age: 29, jersey_number: 92, ratings: { ovr: 79, spd: 68, str: 90, agi: 66, awr: 78, sta: 82, thp: 40, tha: 40, cth: 40, tkl: 80 }, status: 'Active', secondary_positions: [], injury_proneness: 28 },
  { player_id: 53, team_id: 1, first_name: 'Matthew', last_name: 'Judon', position: 'DE', age: 31, jersey_number: 9, ratings: { ovr: 88, spd: 78, str: 88, agi: 76, awr: 85, sta: 84, thp: 40, tha: 40, cth: 40, tkl: 86 }, status: 'Active', secondary_positions: ['LB'], injury_proneness: 30 },
  { player_id: 54, team_id: 1, first_name: 'Josh', last_name: 'Uche', position: 'DE', age: 26, jersey_number: 53, ratings: { ovr: 81, spd: 82, str: 82, agi: 80, awr: 78, sta: 80, thp: 40, tha: 40, cth: 40, tkl: 80 }, status: 'Active', secondary_positions: ['LB'], injury_proneness: 20 },
  { player_id: 55, team_id: 1, first_name: 'Deatrich', last_name: 'Wise Jr', position: 'DE', age: 29, jersey_number: 91, ratings: { ovr: 78, spd: 75, str: 86, agi: 74, awr: 76, sta: 82, thp: 40, tha: 40, cth: 40, tkl: 78 }, status: 'Active', secondary_positions: [], injury_proneness: 26 },
  
  // Linebackers
  { player_id: 61, team_id: 1, first_name: 'Ja\'Whaun', last_name: 'Bentley', position: 'LB', age: 28, jersey_number: 8, ratings: { ovr: 82, spd: 76, str: 84, agi: 74, awr: 84, sta: 82, thp: 40, tha: 40, cth: 50, tkl: 85 }, status: 'Active', secondary_positions: [], injury_proneness: 24 },
  { player_id: 62, team_id: 1, first_name: 'Raekwon', last_name: 'McMillan', position: 'LB', age: 28, jersey_number: 52, ratings: { ovr: 76, spd: 74, str: 82, agi: 72, awr: 78, sta: 80, thp: 40, tha: 40, cth: 48, tkl: 82 }, status: 'Active', secondary_positions: [], injury_proneness: 28 },
  { player_id: 63, team_id: 1, first_name: 'Jahlani', last_name: 'Tavai', position: 'LB', age: 27, jersey_number: 48, ratings: { ovr: 74, spd: 72, str: 80, agi: 70, awr: 76, sta: 78, thp: 40, tha: 40, cth: 46, tkl: 80 }, status: 'Active', secondary_positions: [], injury_proneness: 22 },
  { player_id: 64, team_id: 1, first_name: 'Anfernee', last_name: 'Jennings', position: 'LB', age: 26, jersey_number: 58, ratings: { ovr: 72, spd: 70, str: 82, agi: 68, awr: 72, sta: 76, thp: 40, tha: 40, cth: 45, tkl: 78 }, status: 'Active', secondary_positions: ['DE'], injury_proneness: 25 },
  
  // Cornerbacks
  { player_id: 71, team_id: 1, first_name: 'Christian', last_name: 'Gonzalez', position: 'CB', age: 22, jersey_number: 6, ratings: { ovr: 86, spd: 92, str: 75, agi: 90, awr: 82, sta: 88, thp: 40, tha: 40, cth: 78, tkl: 74 }, status: 'Active', secondary_positions: [], injury_proneness: 15 },
  { player_id: 72, team_id: 1, first_name: 'Jonathan', last_name: 'Jones', position: 'CB', age: 30, jersey_number: 31, ratings: { ovr: 81, spd: 90, str: 68, agi: 88, awr: 82, sta: 84, thp: 40, tha: 40, cth: 75, tkl: 72 }, status: 'Active', secondary_positions: [], injury_proneness: 32 },
  { player_id: 73, team_id: 1, first_name: 'Marcus', last_name: 'Jones', position: 'CB', age: 25, jersey_number: 25, ratings: { ovr: 77, spd: 91, str: 65, agi: 89, awr: 76, sta: 82, thp: 40, tha: 40, cth: 72, tkl: 70 }, status: 'Active', secondary_positions: ['WR'], injury_proneness: 20 },
  { player_id: 74, team_id: 1, first_name: 'Jack', last_name: 'Jones', position: 'CB', age: 26, jersey_number: 13, ratings: { ovr: 78, spd: 89, str: 67, agi: 87, awr: 74, sta: 80, thp: 40, tha: 40, cth: 74, tkl: 71 }, status: 'Active', secondary_positions: [], injury_proneness: 24 },
  { player_id: 75, team_id: 1, first_name: 'Myles', last_name: 'Bryant', position: 'CB', age: 26, jersey_number: 41, ratings: { ovr: 73, spd: 88, str: 64, agi: 86, awr: 72, sta: 78, thp: 40, tha: 40, cth: 70, tkl: 68 }, status: 'Active', secondary_positions: ['S'], injury_proneness: 18 },
  
  // Safeties
  { player_id: 81, team_id: 1, first_name: 'Kyle', last_name: 'Dugger', position: 'S', age: 28, jersey_number: 23, ratings: { ovr: 85, spd: 86, str: 82, agi: 84, awr: 84, sta: 86, thp: 40, tha: 40, cth: 76, tkl: 82 }, status: 'Active', secondary_positions: [], injury_proneness: 22 },
  { player_id: 82, team_id: 1, first_name: 'Jabrill', last_name: 'Peppers', position: 'S', age: 29, jersey_number: 3, ratings: { ovr: 80, spd: 88, str: 78, agi: 86, awr: 80, sta: 82, thp: 40, tha: 40, cth: 74, tkl: 80 }, status: 'Active', secondary_positions: ['LB'], injury_proneness: 28 },
  { player_id: 83, team_id: 1, first_name: 'Adrian', last_name: 'Phillips', position: 'S', age: 32, jersey_number: 21, ratings: { ovr: 78, spd: 82, str: 76, agi: 80, awr: 82, sta: 80, thp: 40, tha: 40, cth: 72, tkl: 78 }, status: 'Active', secondary_positions: ['LB'], injury_proneness: 35 },
  { player_id: 84, team_id: 1, first_name: 'Jalen', last_name: 'Mills', position: 'S', age: 30, jersey_number: 2, ratings: { ovr: 76, spd: 84, str: 74, agi: 82, awr: 78, sta: 78, thp: 40, tha: 40, cth: 70, tkl: 76 }, status: 'Active', secondary_positions: ['CB'], injury_proneness: 30 },
  
  // Special Teams
  { player_id: 91, team_id: 1, first_name: 'Chad', last_name: 'Ryland', position: 'K', age: 24, jersey_number: 37, ratings: { ovr: 76, spd: 50, str: 60, agi: 55, awr: 75, sta: 90, thp: 92, tha: 88, cth: 40, tkl: 30 }, status: 'Active', secondary_positions: [], injury_proneness: 10 },
  { player_id: 92, team_id: 1, first_name: 'Bryce', last_name: 'Baringer', position: 'P', age: 23, jersey_number: 17, ratings: { ovr: 74, spd: 52, str: 62, agi: 56, awr: 72, sta: 92, thp: 90, tha: 85, cth: 40, tkl: 32 }, status: 'Active', secondary_positions: [], injury_proneness: 8 },
];

// Position slot definitions
export const POSITION_SLOTS = {
  QB: ['QB1', 'QB2', 'QB3'],
  RB: ['RB1', 'RB2', 'RB3'],
  WR: ['WR1', 'WR2', 'WR3', 'WR4', 'WR5'],
  TE: ['TE1', 'TE2', 'TE3'],
  LT: ['LT1', 'LT2'],
  LG: ['LG1', 'LG2'],
  C: ['C1', 'C2'],
  RG: ['RG1', 'RG2'],
  RT: ['RT1', 'RT2'],
  'DE-L': ['DEL1', 'DEL2'],
  DT: ['DT1', 'DT2'],
  'DE-R': ['DER1', 'DER2'],
  'OLB-L': ['OLBL1', 'OLBL2'],
  MLB: ['MLB1', 'MLB2'],
  'OLB-R': ['OLBR1', 'OLBR2'],
  CB: ['CB1', 'CB2', 'CB3', 'CB4'],
  FS: ['FS1', 'FS2'],
  SS: ['SS1', 'SS2'],
  K: ['K1'],
  P: ['P1'],
};

// Current depth chart state (in-memory)
let currentDepthChart: DepthChartPayload = {
  team_id: 1,
  assignments: [],
  warnings: [],
};

// Initialize empty depth chart
const initializeEmptyDepthChart = (): void => {
  const assignments: DepthChartAssignment[] = [];
  
  Object.entries(POSITION_SLOTS).forEach(([posGroup, slots]) => {
    slots.forEach(slot => {
      assignments.push({
        slot,
        position_group: posGroup,
        player_id: null,
        ovr_at_slot: 0,
        notes: [],
      });
    });
  });
  
  currentDepthChart = {
    team_id: 1,
    assignments,
    warnings: [],
  };
};

initializeEmptyDepthChart();

// GET /api/teams/{team_id}/roster
export const getRoster = async (teamId: number): Promise<PlayerData[]> => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return MOCK_ROSTER;
};

// GET /api/teams/{team_id}/depthchart
export const getDepthChart = async (teamId: number): Promise<DepthChartPayload> => {
  await new Promise(resolve => setTimeout(resolve, 200));
  return { ...currentDepthChart };
};

// POST /api/teams/{team_id}/depthchart:auto
export const autoFillDepthChart = async (
  teamId: number,
  options: AutoFillOptions
): Promise<DepthChartPayload> => {
  await new Promise(resolve => setTimeout(resolve, 800));
  
  const warnings: string[] = [];
  const assignments: DepthChartAssignment[] = [];
  
  // Helper: Map backend position to roster position
  const mapPositionToRoster = (posGroup: string): string[] => {
    if (posGroup === 'DE-L' || posGroup === 'DE-R') return ['DE'];
    if (posGroup === 'OLB-L' || posGroup === 'OLB-R' || posGroup === 'MLB') return ['LB'];
    if (posGroup === 'FS' || posGroup === 'SS') return ['S'];
    if (posGroup === 'LT' || posGroup === 'RT') return ['T'];
    if (posGroup === 'LG' || posGroup === 'RG') return ['G'];
    return [posGroup];
  };
  
  // Helper: Check if player is eligible
  const isEligible = (player: PlayerData, primaryPositions: string[], allowCrossTrain: boolean): boolean => {
    if (options.respect_injuries && (player.status === 'OUT' || player.status === 'Doubtful')) {
      return false;
    }
    
    // Check primary position
    if (primaryPositions.includes(player.position)) return true;
    
    // Check secondary positions if cross-training allowed
    if (allowCrossTrain) {
      return player.secondary_positions.some(sp => primaryPositions.includes(sp));
    }
    
    return false;
  };
  
  // Helper: Calculate effective OVR with penalties
  const getEffectiveOvr = (player: PlayerData, primaryPositions: string[]): number => {
    let ovr = player.ratings.ovr;
    
    // Cross-train penalty
    if (!primaryPositions.includes(player.position)) {
      ovr -= 2;
    }
    
    return ovr;
  };
  
  // Helper: Sort players for a position
  const sortPlayers = (players: PlayerData[], primaryPositions: string[]): PlayerData[] => {
    return players.slice().sort((a, b) => {
      const aOvr = getEffectiveOvr(a, primaryPositions);
      const bOvr = getEffectiveOvr(b, primaryPositions);
      
      // Fatigue preference (within ±2 OVR)
      if (options.respect_fatigue && Math.abs(aOvr - bOvr) <= 2) {
        if (a.ratings.sta !== b.ratings.sta) {
          return b.ratings.sta - a.ratings.sta;
        }
      }
      
      // Primary sort: OVR
      if (aOvr !== bOvr) return bOvr - aOvr;
      
      // Tie-breakers
      if (a.ratings.awr !== b.ratings.awr) return b.ratings.awr - a.ratings.awr;
      if (a.ratings.sta !== b.ratings.sta) return b.ratings.sta - a.ratings.sta;
      
      const aInj = a.injury_proneness || 50;
      const bInj = b.injury_proneness || 50;
      if (aInj !== bInj) return aInj - bInj;
      
      return a.last_name.localeCompare(b.last_name);
    });
  };
  
  // Track assigned players
  const assignedPlayerIds = new Set<number>();
  
  // Get existing assignments from current depth chart (preserve all user selections)
  const existingAssignments = new Map<string, number>();
  currentDepthChart.assignments.forEach(assignment => {
    if (assignment.player_id) {
      existingAssignments.set(assignment.slot, assignment.player_id);
      assignedPlayerIds.add(assignment.player_id);
    }
  });
  
  // Additional: Get locked assignments if lock_starters is enabled
  const lockedAssignments = new Map<string, number>();
  if (options.lock_starters) {
    currentDepthChart.assignments.forEach(assignment => {
      if (assignment.player_id && assignment.slot.endsWith('1')) {
        lockedAssignments.set(assignment.slot, assignment.player_id);
      }
    });
  }
  
  // Fill each position group
  Object.entries(POSITION_SLOTS).forEach(([posGroup, slots]) => {
    const primaryPositions = mapPositionToRoster(posGroup);
    
    // Get eligible players
    let eligiblePlayers = MOCK_ROSTER.filter(p => 
      isEligible(p, primaryPositions, options.allow_cross_training) &&
      !assignedPlayerIds.has(p.player_id)
    );
    
    // Sort by criteria
    const sortedPlayers = sortPlayers(eligiblePlayers, primaryPositions);
    
    // Assign to slots
    let playerIndex = 0;
    slots.forEach(slot => {
      // Check if slot already has an assignment (preserve user selections)
      if (existingAssignments.has(slot)) {
        const existingPlayerId = existingAssignments.get(slot)!;
        const existingPlayer = MOCK_ROSTER.find(p => p.player_id === existingPlayerId);
        if (existingPlayer) {
          const ovrAtSlot = getEffectiveOvr(existingPlayer, primaryPositions);
          const notes: string[] = ['user-selected'];
          
          if (!primaryPositions.includes(existingPlayer.position)) {
            notes.push('xtrain:-2');
          }
          
          assignments.push({
            slot,
            position_group: posGroup,
            player_id: existingPlayerId,
            ovr_at_slot: ovrAtSlot,
            notes,
          });
        }
        return;
      }
      
      // Check if slot is locked (for lock_starters option)
      if (lockedAssignments.has(slot) && !existingAssignments.has(slot)) {
        const lockedPlayerId = lockedAssignments.get(slot)!;
        const lockedPlayer = MOCK_ROSTER.find(p => p.player_id === lockedPlayerId);
        if (lockedPlayer) {
          const ovrAtSlot = getEffectiveOvr(lockedPlayer, primaryPositions);
          const notes: string[] = [];
          
          if (!primaryPositions.includes(lockedPlayer.position)) {
            notes.push('xtrain:-2');
          }
          
          assignments.push({
            slot,
            position_group: posGroup,
            player_id: lockedPlayerId,
            ovr_at_slot: ovrAtSlot,
            notes,
          });
        }
        return;
      }
      
      // Find next available player
      while (playerIndex < sortedPlayers.length && assignedPlayerIds.has(sortedPlayers[playerIndex].player_id)) {
        playerIndex++;
      }
      
      if (playerIndex < sortedPlayers.length) {
        const player = sortedPlayers[playerIndex];
        assignedPlayerIds.add(player.player_id);
        
        const ovrAtSlot = getEffectiveOvr(player, primaryPositions);
        const notes: string[] = [];
        
        // Add cross-train note
        if (!primaryPositions.includes(player.position)) {
          notes.push('xtrain:-2');
          warnings.push(`${slot} cross-trained from ${player.position} (-2 OVR)`);
        }
        
        // Add fatigue warning
        if (player.ratings.sta < 50) {
          warnings.push(`${slot}: ${player.first_name} ${player.last_name} has low stamina (${player.ratings.sta})`);
        }
        
        // Add injury warning if not respecting injuries
        if (!options.respect_injuries && (player.status === 'OUT' || player.status === 'Doubtful')) {
          warnings.push(`${slot}: ${player.first_name} ${player.last_name} is ${player.status}`);
        }
        
        assignments.push({
          slot,
          position_group: posGroup,
          player_id: player.player_id,
          ovr_at_slot: ovrAtSlot,
          notes,
        });
        
        playerIndex++;
      } else {
        // No more eligible players
        assignments.push({
          slot,
          position_group: posGroup,
          player_id: null,
          ovr_at_slot: 0,
          notes: [],
        });
        warnings.push(`${slot} unfilled: insufficient eligible players`);
      }
    });
  });
  
  currentDepthChart = {
    team_id: teamId,
    assignments,
    warnings,
  };
  
  return { ...currentDepthChart };
};

// PUT /api/teams/{team_id}/depthchart
export const updateDepthChart = async (
  teamId: number,
  payload: DepthChartPayload
): Promise<DepthChartPayload> => {
  await new Promise(resolve => setTimeout(resolve, 400));
  
  // Validate and save
  currentDepthChart = { ...payload };
  
  return { ...currentDepthChart };
};

// Helper: Get player by ID
export const getPlayerById = (playerId: number): PlayerData | undefined => {
  return MOCK_ROSTER.find(p => p.player_id === playerId);
};
