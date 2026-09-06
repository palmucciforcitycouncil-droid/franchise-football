// Mock API for GM Desk operations

export interface ExpiringContract {
  playerId: string;
  name: string;
  position: string;
  age: number;
  overall: number;
  currentCapHit: string;
  desiredLength: number;
  desiredTotal: string;
  desiredAPY: string;
}

export interface TopProspect {
  name: string;
  position: string;
  age: number;
  overall: number;
  potential: number;
  school: string;
  round: number;
}

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

export interface TradeOffer {
  teamOffering: string;
  teamReceiving: string;
  offeringAssets: TradeAsset[];
  receivingAssets: TradeAsset[];
}

export interface TradeResponse {
  accepted: boolean;
  message: string;
  counterOffer?: TradeOffer;
}

const NFL_TEAMS = [
  'New England Patriots', 'Buffalo Bills', 'Miami Dolphins', 'New York Jets',
  'Pittsburgh Steelers', 'Baltimore Ravens', 'Cincinnati Bengals', 'Cleveland Browns',
  'Tennessee Titans', 'Indianapolis Colts', 'Houston Texans', 'Jacksonville Jaguars',
  'Kansas City Chiefs', 'Las Vegas Raiders', 'Los Angeles Chargers', 'Denver Broncos',
  'Dallas Cowboys', 'Philadelphia Eagles', 'New York Giants', 'Washington Commanders',
  'Green Bay Packers', 'Minnesota Vikings', 'Chicago Bears', 'Detroit Lions',
  'Tampa Bay Buccaneers', 'New Orleans Saints', 'Atlanta Falcons', 'Carolina Panthers',
  'San Francisco 49ers', 'Los Angeles Rams', 'Seattle Seahawks', 'Arizona Cardinals'
];

const MOCK_EXPIRING_CONTRACTS: Record<string, ExpiringContract[]> = {
  'New England Patriots': [
    { playerId: '1', name: 'K. Benton', position: 'WR', age: 27, overall: 87, currentCapHit: '$12.0M', desiredLength: 4, desiredTotal: '$68M', desiredAPY: '$17M' },
    { playerId: '2', name: 'R. Hayes', position: 'RB', age: 29, overall: 79, currentCapHit: '$3.5M', desiredLength: 2, desiredTotal: '$8M', desiredAPY: '$4M' },
    { playerId: '3', name: 'T. Garcia', position: 'C', age: 29, overall: 81, currentCapHit: '$5.8M', desiredLength: 3, desiredTotal: '$21M', desiredAPY: '$7M' },
    { playerId: '4', name: 'K. Brown', position: 'G', age: 28, overall: 80, currentCapHit: '$5.1M', desiredLength: 2, desiredTotal: '$12M', desiredAPY: '$6M' },
  ],
  'Buffalo Bills': [
    { playerId: '10', name: 'J. Allen', position: 'QB', age: 28, overall: 95, currentCapHit: '$25.0M', desiredLength: 5, desiredTotal: '$250M', desiredAPY: '$50M' },
    { playerId: '11', name: 'S. Diggs', position: 'WR', age: 30, overall: 88, currentCapHit: '$14.0M', desiredLength: 3, desiredTotal: '$48M', desiredAPY: '$16M' },
  ],
  'Miami Dolphins': [
    { playerId: '20', name: 'T. Hill', position: 'WR', age: 29, overall: 92, currentCapHit: '$19.0M', desiredLength: 3, desiredTotal: '$72M', desiredAPY: '$24M' },
  ],
};

const MOCK_TOP_PROSPECTS: Record<string, TopProspect[]> = {
  QB: [
    { name: 'C. Williams', position: 'QB', age: 22, overall: 78, potential: 94, school: 'USC', round: 1 },
    { name: 'D. Maye', position: 'QB', age: 21, overall: 76, potential: 92, school: 'North Carolina', round: 1 },
    { name: 'J. Daniels', position: 'QB', age: 23, overall: 74, potential: 89, school: 'LSU', round: 2 },
    { name: 'M. Penix Jr.', position: 'QB', age: 24, overall: 73, potential: 87, school: 'Washington', round: 2 },
    { name: 'B. Nix', position: 'QB', age: 24, overall: 71, potential: 85, school: 'Oregon', round: 3 },
  ],
  RB: [
    { name: 'J. Brooks', position: 'RB', age: 21, overall: 76, potential: 88, school: 'Texas', round: 2 },
    { name: 'T. Benson', position: 'RB', age: 22, overall: 75, potential: 87, school: 'FSU', round: 2 },
    { name: 'B. Irving', position: 'RB', age: 23, overall: 73, potential: 85, school: 'Oregon', round: 3 },
    { name: 'R. Johnson', position: 'RB', age: 21, overall: 72, potential: 84, school: 'Michigan', round: 3 },
    { name: 'J. Wright', position: 'RB', age: 22, overall: 70, potential: 82, school: 'Tennessee', round: 4 },
  ],
  WR: [
    { name: 'M. Harrison Jr.', position: 'WR', age: 21, overall: 81, potential: 95, school: 'Ohio State', round: 1 },
    { name: 'R. Odunze', position: 'WR', age: 21, overall: 79, potential: 93, school: 'Washington', round: 1 },
    { name: 'M. Nabers', position: 'WR', age: 21, overall: 78, potential: 92, school: 'LSU', round: 1 },
    { name: 'A. Mitchell', position: 'WR', age: 22, overall: 76, potential: 89, school: 'Texas', round: 1 },
    { name: 'B. Thomas Jr.', position: 'WR', age: 22, overall: 74, potential: 87, school: 'LSU', round: 2 },
  ],
  TE: [
    { name: 'B. Bowers', position: 'TE', age: 21, overall: 79, potential: 93, school: 'Georgia', round: 1 },
    { name: 'J. Sanders', position: 'TE', age: 22, overall: 74, potential: 87, school: 'Texas', round: 2 },
    { name: 'T. Warren', position: 'TE', age: 23, overall: 72, potential: 85, school: 'Penn State', round: 3 },
    { name: 'E. All', position: 'TE', age: 24, overall: 71, potential: 83, school: 'Iowa', round: 3 },
    { name: 'C. Kolar', position: 'TE', age: 23, overall: 69, potential: 81, school: 'Iowa State', round: 4 },
  ],
  OL: [
    { name: 'J. Alt', position: 'T', age: 21, overall: 80, potential: 94, school: 'Notre Dame', round: 1 },
    { name: 'O. Fashanu', position: 'T', age: 21, overall: 79, potential: 93, school: 'Penn State', round: 1 },
    { name: 'T. Fuaga', position: 'G', age: 22, overall: 77, potential: 90, school: 'Oregon State', round: 1 },
    { name: 'J. Morgan', position: 'C', age: 23, overall: 75, potential: 88, school: 'Arizona', round: 2 },
    { name: 'T. Guyton', position: 'T', age: 22, overall: 74, potential: 86, school: 'Oklahoma', round: 2 },
  ],
  DL: [
    { name: 'J. Verse', position: 'DE', age: 23, overall: 80, potential: 92, school: 'FSU', round: 1 },
    { name: 'L. Latu', position: 'DE', age: 24, overall: 78, potential: 90, school: 'UCLA', round: 1 },
    { name: 'C. Murphy', position: 'DT', age: 22, overall: 77, potential: 89, school: 'Texas', round: 2 },
    { name: 'B. Newton', position: 'DT', age: 23, overall: 76, potential: 87, school: 'Illinois', round: 2 },
    { name: 'J. Hall', position: 'DE', age: 22, overall: 75, potential: 86, school: 'Ohio State', round: 2 },
  ],
  LB: [
    { name: 'D. White', position: 'LB', age: 22, overall: 77, potential: 90, school: 'Georgia', round: 1 },
    { name: 'E. Cooper', position: 'LB', age: 23, overall: 76, potential: 89, school: 'Texas A&M', round: 2 },
    { name: 'P. Wilson', position: 'LB', age: 22, overall: 74, potential: 87, school: 'NC State', round: 2 },
    { name: 'J. Trotter', position: 'LB', age: 23, overall: 73, potential: 85, school: 'Clemson', round: 3 },
    { name: 'T. Burns', position: 'LB', age: 22, overall: 72, potential: 84, school: 'Kansas', round: 3 },
  ],
  DB: [
    { name: 'Q. Mitchell', position: 'CB', age: 21, overall: 79, potential: 92, school: 'Toledo', round: 1 },
    { name: 'T. Arnold', position: 'CB', age: 22, overall: 78, potential: 91, school: 'Alabama', round: 1 },
    { name: 'C. DeJean', position: 'S', age: 22, overall: 77, potential: 89, school: 'Iowa', round: 2 },
    { name: 'K. Jackson', position: 'CB', age: 23, overall: 76, potential: 88, school: 'Oregon', round: 2 },
    { name: 'M. Santos', position: 'S', age: 22, overall: 75, potential: 87, school: 'TCU', round: 2 },
  ],
};

// Simulate getting expiring contracts for a team
export const getExpiringContracts = async (teamName: string): Promise<ExpiringContract[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return MOCK_EXPIRING_CONTRACTS[teamName] || [];
};

// Simulate getting all NFL teams (alphabetically sorted)
export const getAllTeams = async (): Promise<string[]> => {
  await new Promise(resolve => setTimeout(resolve, 100));
  return [...NFL_TEAMS].sort();
};

// Simulate getting top prospects by position
export const getTopProspects = async (position: string): Promise<TopProspect[]> => {
  await new Promise(resolve => setTimeout(resolve, 200));
  return MOCK_TOP_PROSPECTS[position] || [];
};

// Simulate submitting a trade offer
export const submitTradeOffer = async (offer: TradeOffer): Promise<TradeResponse> => {
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Simple logic: 70% chance of rejection, 30% acceptance
  const accepted = Math.random() > 0.7;
  
  if (accepted) {
    return {
      accepted: true,
      message: `${offer.teamReceiving} has accepted your trade offer!`
    };
  } else {
    // 50% chance of counter offer
    const hasCounter = Math.random() > 0.5;
    
    if (hasCounter) {
      return {
        accepted: false,
        message: `${offer.teamReceiving} has rejected your offer and sent a counter-proposal.`,
        counterOffer: {
          ...offer,
          // Swap the teams and assets for counter
          teamOffering: offer.teamReceiving,
          teamReceiving: offer.teamOffering,
          offeringAssets: offer.receivingAssets,
          receivingAssets: offer.offeringAssets,
        }
      };
    }
    
    return {
      accepted: false,
      message: `${offer.teamReceiving} has rejected your trade offer. They are not interested at this time.`
    };
  }
};
