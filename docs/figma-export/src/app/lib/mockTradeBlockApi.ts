// Mock Trade Block API for NFL simulation game

export interface TradeAsset {
  id: string;
  type: 'player' | 'pick';
  
  // Player info
  name?: string;
  position?: string;
  overall?: number;
  age?: number;
  contract?: string;
  
  // Pick info
  round?: number;
  year?: number;
  team?: string;
  pickNumber?: number;
}

export interface TradeOffer {
  id: string;
  fromTeam: string;
  toTeam: string;
  offeredAssets: TradeAsset[];
  requestedAssets: TradeAsset[];
  status: 'pending' | 'accepted' | 'rejected' | 'countered';
  timestamp: string;
  aiResponse?: string;
  interest: 'high' | 'medium' | 'low';
}

export interface AvailablePlayer {
  id: string;
  name: string;
  position: string;
  team: string;
  overall: number;
  age: number;
  contract: string;
  type: 'prospect' | 'veteran';
  askingPrice: string;
  interest: 'high' | 'medium' | 'low';
}

export type TradePreference = 'any' | 'position' | 'prospect' | 'veteran' | 'picks';

// Your roster for trade offers
const YOUR_ROSTER: TradeAsset[] = [
  {
    id: 'p1',
    type: 'player',
    name: 'Mac Jones',
    position: 'QB',
    overall: 76,
    age: 25,
    contract: '2yr/$15M',
  },
  {
    id: 'p2',
    type: 'player',
    name: 'Rhamondre Stevenson',
    position: 'RB',
    overall: 81,
    age: 25,
    contract: '3yr/$12M',
  },
  {
    id: 'p3',
    type: 'player',
    name: 'DeVante Parker',
    position: 'WR',
    overall: 78,
    age: 30,
    contract: '1yr/$6M',
  },
  {
    id: 'p4',
    type: 'player',
    name: 'Hunter Henry',
    position: 'TE',
    overall: 80,
    age: 28,
    contract: '2yr/$10M',
  },
  {
    id: 'p5',
    type: 'player',
    name: 'Matthew Judon',
    position: 'LB',
    overall: 87,
    age: 31,
    contract: '1yr/$14M',
  },
  {
    id: 'p6',
    type: 'player',
    name: 'Kyle Dugger',
    position: 'S',
    overall: 84,
    age: 27,
    contract: '4yr/$16M',
  },
  {
    id: 'p7',
    type: 'player',
    name: 'Christian Barmore',
    position: 'DT',
    overall: 79,
    age: 24,
    contract: '2yr/$8M',
  },
  {
    id: 'p8',
    type: 'player',
    name: 'Ja\'Whaun Bentley',
    position: 'LB',
    overall: 75,
    age: 27,
    contract: '2yr/$5M',
  },
  {
    id: 'p9',
    type: 'player',
    name: 'Kendrick Bourne',
    position: 'WR',
    overall: 77,
    age: 28,
    contract: '1yr/$4M',
  },
  {
    id: 'p10',
    type: 'player',
    name: 'Mike Onwenu',
    position: 'OL',
    overall: 82,
    age: 26,
    contract: '3yr/$18M',
  },
];

// Your draft picks
const YOUR_PICKS: TradeAsset[] = [
  {
    id: 'pick1',
    type: 'pick',
    round: 1,
    year: 2028,
    team: 'NE',
    pickNumber: 18,
  },
  {
    id: 'pick2',
    type: 'pick',
    round: 2,
    year: 2028,
    team: 'NE',
    pickNumber: 50,
  },
  {
    id: 'pick3',
    type: 'pick',
    round: 3,
    year: 2028,
    team: 'NE',
    pickNumber: 82,
  },
  {
    id: 'pick4',
    type: 'pick',
    round: 1,
    year: 2029,
    team: 'NE',
    pickNumber: null as any,
  },
  {
    id: 'pick5',
    type: 'pick',
    round: 2,
    year: 2029,
    team: 'NE',
    pickNumber: null as any,
  },
];

// Available players from other teams
const AVAILABLE_PLAYERS: AvailablePlayer[] = [
  {
    id: 'ap1',
    name: 'Lamar Jackson',
    position: 'QB',
    team: 'BAL',
    overall: 93,
    age: 27,
    contract: '2yr/$52M',
    type: 'veteran',
    askingPrice: 'Two 1st round picks + starter',
    interest: 'high',
  },
  {
    id: 'ap2',
    name: 'Derrick Henry',
    position: 'RB',
    team: 'TEN',
    overall: 89,
    age: 30,
    contract: '1yr/$8M',
    type: 'veteran',
    askingPrice: '2nd round pick',
    interest: 'medium',
  },
  {
    id: 'ap3',
    name: 'Tyreek Hill',
    position: 'WR',
    team: 'MIA',
    overall: 94,
    age: 29,
    contract: '3yr/$90M',
    type: 'veteran',
    askingPrice: 'Two 1st round picks',
    interest: 'high',
  },
  {
    id: 'ap4',
    name: 'T.J. Hockenson',
    position: 'TE',
    team: 'MIN',
    overall: 86,
    age: 26,
    contract: '4yr/$36M',
    type: 'veteran',
    askingPrice: '1st round pick',
    interest: 'high',
  },
  {
    id: 'ap5',
    name: 'Micah Parsons',
    position: 'LB',
    team: 'DAL',
    overall: 96,
    age: 25,
    contract: '1yr/$21M',
    type: 'veteran',
    askingPrice: 'Not actively shopping',
    interest: 'low',
  },
  {
    id: 'ap6',
    name: 'Jalen Ramsey',
    position: 'CB',
    team: 'MIA',
    overall: 91,
    age: 29,
    contract: '2yr/$40M',
    type: 'veteran',
    askingPrice: '1st + 3rd round picks',
    interest: 'medium',
  },
  {
    id: 'ap7',
    name: 'Quentin Johnston',
    position: 'WR',
    team: 'LAC',
    overall: 72,
    age: 22,
    contract: '3yr/$6M',
    type: 'prospect',
    askingPrice: '3rd round pick',
    interest: 'low',
  },
  {
    id: 'ap8',
    name: 'Devon Witherspoon',
    position: 'CB',
    team: 'SEA',
    overall: 85,
    age: 23,
    contract: '4yr/$12M',
    type: 'prospect',
    askingPrice: '1st round pick + player',
    interest: 'high',
  },
  {
    id: 'ap9',
    name: 'Bijan Robinson',
    position: 'RB',
    team: 'ATL',
    overall: 83,
    age: 22,
    contract: '4yr/$14M',
    type: 'prospect',
    askingPrice: '1st round pick',
    interest: 'high',
  },
  {
    id: 'ap10',
    name: 'Chris Olave',
    position: 'WR',
    team: 'NO',
    overall: 88,
    age: 24,
    contract: '2yr/$16M',
    type: 'prospect',
    askingPrice: '1st + 2nd round picks',
    interest: 'high',
  },
  {
    id: 'ap11',
    name: 'George Karlaftis',
    position: 'LB',
    team: 'KC',
    overall: 81,
    age: 23,
    contract: '3yr/$10M',
    type: 'prospect',
    askingPrice: '2nd round pick',
    interest: 'medium',
  },
  {
    id: 'ap12',
    name: 'Garrett Wilson',
    position: 'WR',
    team: 'NYJ',
    overall: 89,
    age: 24,
    contract: '2yr/$18M',
    type: 'prospect',
    askingPrice: '1st round pick + starter',
    interest: 'high',
  },
];

// AI trade response generator - generates a single offer
function generateSingleTradeResponse(
  offeredAssets: TradeAsset[],
  preference: TradePreference,
  specificPosition?: string,
  index: number
): TradeOffer {
  const responses = [
    {
      interest: 'high' as const,
      message: 'We\'re very interested in this package. Here\'s our counter-offer:',
      assets: 2,
    },
    {
      interest: 'medium' as const,
      message: 'We see potential here, but need more value. Counter-offer:',
      assets: 1,
    },
    {
      interest: 'low' as const,
      message: 'This doesn\'t quite work for us, but we\'re willing to negotiate:',
      assets: 3,
    },
  ];

  const response = responses[index % responses.length];
  
  // Generate counter assets based on preference
  const requestedAssets: TradeAsset[] = [];
  
  if (preference === 'picks' || Math.random() > 0.6) {
    requestedAssets.push({
      id: 'counter-pick-' + Date.now(),
      type: 'pick',
      round: Math.floor(Math.random() * 3) + 1,
      year: 2028 + Math.floor(Math.random() * 2),
      team: 'Various',
    });
  }
  
  if (preference === 'position' && specificPosition) {
    requestedAssets.push({
      id: 'counter-player-' + Date.now(),
      type: 'player',
      name: `${specificPosition} Starter`,
      position: specificPosition,
      overall: 75 + Math.floor(Math.random() * 15),
      age: 24 + Math.floor(Math.random() * 6),
      contract: '2-3yr contract',
    });
  } else if (preference === 'veteran' || preference === 'prospect') {
    const positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'LB', 'CB', 'S'];
    const pos = positions[Math.floor(Math.random() * positions.length)];
    requestedAssets.push({
      id: 'counter-player-' + Date.now(),
      type: 'player',
      name: `${preference === 'veteran' ? 'Veteran' : 'Young'} ${pos}`,
      position: pos,
      overall: preference === 'veteran' ? 80 + Math.floor(Math.random() * 10) : 70 + Math.floor(Math.random() * 15),
      age: preference === 'veteran' ? 28 + Math.floor(Math.random() * 5) : 22 + Math.floor(Math.random() * 4),
      contract: '1-3yr contract',
    });
  }
  
  // Add more assets based on interest
  for (let i = requestedAssets.length; i < response.assets; i++) {
    if (Math.random() > 0.5) {
      requestedAssets.push({
        id: 'counter-pick-' + Date.now() + '-' + i,
        type: 'pick',
        round: Math.floor(Math.random() * 5) + 1,
        year: 2028 + Math.floor(Math.random() * 2),
        team: 'Various',
      });
    } else {
      const positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S'];
      const pos = positions[Math.floor(Math.random() * positions.length)];
      requestedAssets.push({
        id: 'counter-player-' + Date.now() + '-' + i,
        type: 'player',
        name: `${pos} Depth`,
        position: pos,
        overall: 65 + Math.floor(Math.random() * 15),
        age: 23 + Math.floor(Math.random() * 6),
        contract: '1-2yr contract',
      });
    }
  }

  return {
    id: 'offer-' + Date.now() + '-' + index,
    fromTeam: ['Baltimore Ravens', 'Kansas City Chiefs', 'Dallas Cowboys', 'Miami Dolphins'][index % 4],
    toTeam: 'NE',
    offeredAssets,
    requestedAssets,
    status: 'pending',
    timestamp: new Date().toISOString(),
    aiResponse: response.message,
    interest: response.interest,
  };
}

// Generate multiple trade offers
function generateMultipleTradeResponses(
  offeredAssets: TradeAsset[],
  preference: TradePreference,
  specificPosition?: string
): TradeOffer[] {
  const numOffers = Math.floor(Math.random() * 3) + 2; // 2-4 offers
  const offers: TradeOffer[] = [];
  
  for (let i = 0; i < numOffers; i++) {
    offers.push(generateSingleTradeResponse(offeredAssets, preference, specificPosition, i));
  }
  
  return offers;
}

export const getYourRoster = async (): Promise<TradeAsset[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return YOUR_ROSTER;
};

export const getYourPicks = async (): Promise<TradeAsset[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return YOUR_PICKS;
};

export const getAvailablePlayers = async (): Promise<AvailablePlayer[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return AVAILABLE_PLAYERS;
};

export const submitTradeOffer = async (
  offeredAssets: TradeAsset[],
  preference: TradePreference,
  specificPosition?: string
): Promise<TradeOffer[]> => {
  await new Promise(resolve => setTimeout(resolve, 800));
  return generateMultipleTradeResponses(offeredAssets, preference, specificPosition);
};

export const filterAvailablePlayers = async (
  position?: string,
  team?: string,
  type?: 'prospect' | 'veteran'
): Promise<AvailablePlayer[]> => {
  await new Promise(resolve => setTimeout(resolve, 200));
  
  let filtered = [...AVAILABLE_PLAYERS];
  
  if (position && position !== 'all') {
    filtered = filtered.filter(p => p.position === position);
  }
  
  if (team && team !== 'all') {
    filtered = filtered.filter(p => p.team === team);
  }
  
  if (type) {
    filtered = filtered.filter(p => p.type === type);
  }
  
  return filtered;
};

export const getAvailableTeams = (): string[] => {
  return Array.from(new Set(AVAILABLE_PLAYERS.map(p => p.team))).sort();
};

export const getAvailablePositions = (): string[] => {
  return Array.from(new Set(AVAILABLE_PLAYERS.map(p => p.position))).sort();
};
