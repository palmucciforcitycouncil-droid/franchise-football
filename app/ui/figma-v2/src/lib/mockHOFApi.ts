// Mock Hall of Fame API for NFL simulation game

export interface HOFMember {
  id: string;
  name: string;
  type: 'player' | 'coach';
  position?: string; // For players
  yearsActive: string;
  inductionYear: number;
  teamsPrimary: string; // Main team(s) they're associated with
  achievements: string[];
  
  // Player stats
  passing?: {
    attempts: number;
    completions: number;
    yards: number;
    touchdowns: number;
    interceptions: number;
    qbRating: number;
  };
  rushing?: {
    attempts: number;
    yards: number;
    touchdowns: number;
    average: number;
  };
  receiving?: {
    receptions: number;
    yards: number;
    touchdowns: number;
    average: number;
  };
  defense?: {
    tackles: number;
    sacks: number;
    interceptions: number;
    touchdowns: number;
  };
  kicking?: {
    fgMade: number;
    fgAttempts: number;
    fgPct: number;
    points: number;
  };
  
  // Coach stats
  coaching?: {
    wins: number;
    losses: number;
    winPct: number;
    playoffAppearances: number;
    championships: number;
  };
}

export interface HOFCandidate extends Omit<HOFMember, 'inductionYear'> {
  eligibleYear: number;
  votingPct?: number; // Percentage of votes received
}

// Current year inductees
const CURRENT_INDUCTEES: HOFMember[] = [
  {
    id: 'inductee-1',
    name: 'Tom Brady',
    type: 'player',
    position: 'QB',
    yearsActive: '2000-2022',
    inductionYear: 2028,
    teamsPrimary: 'NE, TB',
    achievements: [
      '7x Super Bowl Champion',
      '5x Super Bowl MVP',
      '3x NFL MVP',
      '15x Pro Bowl',
      'All-time passing yards leader',
      'All-time passing TDs leader',
    ],
    passing: {
      attempts: 12050,
      completions: 7753,
      yards: 89214,
      touchdowns: 649,
      interceptions: 212,
      qbRating: 97.2,
    },
    rushing: {
      attempts: 623,
      yards: 1037,
      touchdowns: 25,
      average: 1.7,
    },
  },
  {
    id: 'inductee-2',
    name: 'Bill Belichick',
    type: 'coach',
    yearsActive: '2000-2023',
    inductionYear: 2028,
    teamsPrimary: 'NE',
    achievements: [
      '6x Super Bowl Champion',
      '3x AP Coach of the Year',
      'Most playoff wins all-time',
      '333 career wins',
      '24 playoff appearances',
    ],
    coaching: {
      wins: 333,
      losses: 178,
      winPct: 65.2,
      playoffAppearances: 24,
      championships: 6,
    },
  },
];

// Eligible candidates
const ELIGIBLE_CANDIDATES: HOFCandidate[] = [
  {
    id: 'candidate-1',
    name: 'Eli Manning',
    type: 'player',
    position: 'QB',
    yearsActive: '2004-2019',
    eligibleYear: 2025,
    teamsPrimary: 'NYG',
    votingPct: 72.3,
    achievements: [
      '2x Super Bowl Champion',
      '2x Super Bowl MVP',
      '4x Pro Bowl',
      '57,023 passing yards',
      '366 passing TDs',
    ],
    passing: {
      attempts: 8119,
      completions: 4895,
      yards: 57023,
      touchdowns: 366,
      interceptions: 244,
      qbRating: 84.1,
    },
    rushing: {
      attempts: 339,
      yards: 227,
      touchdowns: 4,
      average: 0.7,
    },
  },
  {
    id: 'candidate-2',
    name: 'Luke Kuechly',
    type: 'player',
    position: 'LB',
    yearsActive: '2012-2019',
    eligibleYear: 2025,
    teamsPrimary: 'CAR',
    votingPct: 88.5,
    achievements: [
      'NFL Defensive Player of the Year (2013)',
      '7x Pro Bowl',
      '5x First-team All-Pro',
      '1,092 career tackles',
      '18 interceptions',
    ],
    defense: {
      tackles: 1092,
      sacks: 12.5,
      interceptions: 18,
      touchdowns: 3,
    },
  },
  {
    id: 'candidate-3',
    name: 'Terrell Suggs',
    type: 'player',
    position: 'LB',
    yearsActive: '2003-2019',
    eligibleYear: 2025,
    teamsPrimary: 'BAL',
    votingPct: 65.8,
    achievements: [
      'Super Bowl Champion (XLVII)',
      'NFL Defensive Player of the Year (2011)',
      '7x Pro Bowl',
      '139 career sacks',
    ],
    defense: {
      tackles: 869,
      sacks: 139.0,
      interceptions: 7,
      touchdowns: 1,
    },
  },
  {
    id: 'candidate-4',
    name: 'Adam Vinatieri',
    type: 'player',
    position: 'K',
    yearsActive: '1996-2019',
    eligibleYear: 2025,
    teamsPrimary: 'NE, IND',
    votingPct: 91.2,
    achievements: [
      '4x Super Bowl Champion',
      '3x Pro Bowl',
      'NFL all-time leading scorer',
      '599 field goals made',
      '2,673 career points',
    ],
    kicking: {
      fgMade: 599,
      fgAttempts: 715,
      fgPct: 83.8,
      points: 2673,
    },
  },
  {
    id: 'candidate-5',
    name: 'Julian Edelman',
    type: 'player',
    position: 'WR',
    yearsActive: '2009-2020',
    eligibleYear: 2026,
    teamsPrimary: 'NE',
    votingPct: 42.1,
    achievements: [
      '3x Super Bowl Champion',
      'Super Bowl LIII MVP',
      '6,822 receiving yards',
      '36 receiving TDs',
    ],
    receiving: {
      receptions: 620,
      yards: 6822,
      touchdowns: 36,
      average: 11.0,
    },
    rushing: {
      attempts: 87,
      yards: 413,
      touchdowns: 5,
      average: 4.7,
    },
  },
  {
    id: 'candidate-6',
    name: 'John Fox',
    type: 'coach',
    yearsActive: '2002-2018',
    eligibleYear: 2024,
    teamsPrimary: 'CAR, DEN, CHI',
    votingPct: 38.4,
    achievements: [
      '2x Super Bowl appearance',
      '133 career wins',
      '3x Division championships',
    ],
    coaching: {
      wins: 133,
      losses: 123,
      winPct: 52.0,
      playoffAppearances: 6,
      championships: 0,
    },
  },
];

// Existing HOF members
const HOF_MEMBERS: HOFMember[] = [
  {
    id: 'hof-1',
    name: 'Jerry Rice',
    type: 'player',
    position: 'WR',
    yearsActive: '1985-2004',
    inductionYear: 2010,
    teamsPrimary: 'SF',
    achievements: [
      '3x Super Bowl Champion',
      'Super Bowl XXIII MVP',
      '13x Pro Bowl',
      'All-time receiving yards leader',
      'All-time receiving TDs leader',
    ],
    receiving: {
      receptions: 1549,
      yards: 22895,
      touchdowns: 197,
      average: 14.8,
    },
    rushing: {
      attempts: 87,
      yards: 645,
      touchdowns: 10,
      average: 7.4,
    },
  },
  {
    id: 'hof-2',
    name: 'Lawrence Taylor',
    type: 'player',
    position: 'LB',
    yearsActive: '1981-1993',
    inductionYear: 1999,
    teamsPrimary: 'NYG',
    achievements: [
      '2x Super Bowl Champion',
      '3x NFL Defensive Player of the Year',
      '10x Pro Bowl',
      '8x First-team All-Pro',
      '132.5 career sacks',
    ],
    defense: {
      tackles: 1088,
      sacks: 132.5,
      interceptions: 9,
      touchdowns: 2,
    },
  },
  {
    id: 'hof-3',
    name: 'Joe Montana',
    type: 'player',
    position: 'QB',
    yearsActive: '1979-1994',
    inductionYear: 2000,
    teamsPrimary: 'SF',
    achievements: [
      '4x Super Bowl Champion',
      '3x Super Bowl MVP',
      '2x NFL MVP',
      '8x Pro Bowl',
      '40,551 passing yards',
    ],
    passing: {
      attempts: 5391,
      completions: 3409,
      yards: 40551,
      touchdowns: 273,
      interceptions: 139,
      qbRating: 92.3,
    },
    rushing: {
      attempts: 457,
      yards: 1676,
      touchdowns: 20,
      average: 3.7,
    },
  },
  {
    id: 'hof-4',
    name: 'Emmitt Smith',
    type: 'player',
    position: 'RB',
    yearsActive: '1990-2004',
    inductionYear: 2010,
    teamsPrimary: 'DAL',
    achievements: [
      '3x Super Bowl Champion',
      'NFL MVP (1993)',
      '8x Pro Bowl',
      'All-time rushing leader',
      '18,355 rushing yards',
    ],
    rushing: {
      attempts: 4409,
      yards: 18355,
      touchdowns: 164,
      average: 4.2,
    },
    receiving: {
      receptions: 515,
      yards: 3224,
      touchdowns: 11,
      average: 6.3,
    },
  },
  {
    id: 'hof-5',
    name: 'Reggie White',
    type: 'player',
    position: 'LB',
    yearsActive: '1985-2000',
    inductionYear: 2006,
    teamsPrimary: 'PHI, GB',
    achievements: [
      'Super Bowl XXXI Champion',
      '2x NFL Defensive Player of the Year',
      '13x Pro Bowl',
      '198 career sacks',
    ],
    defense: {
      tackles: 1104,
      sacks: 198.0,
      interceptions: 3,
      touchdowns: 3,
    },
  },
  {
    id: 'hof-6',
    name: 'Randy Moss',
    type: 'player',
    position: 'WR',
    yearsActive: '1998-2012',
    inductionYear: 2018,
    teamsPrimary: 'MIN, NE',
    achievements: [
      '6x Pro Bowl',
      '4x First-team All-Pro',
      '15,292 receiving yards',
      '156 receiving TDs',
      'NFL single-season TD record (23)',
    ],
    receiving: {
      receptions: 982,
      yards: 15292,
      touchdowns: 156,
      average: 15.6,
    },
  },
  {
    id: 'hof-7',
    name: 'Peyton Manning',
    type: 'player',
    position: 'QB',
    yearsActive: '1998-2015',
    inductionYear: 2021,
    teamsPrimary: 'IND, DEN',
    achievements: [
      '2x Super Bowl Champion',
      '5x NFL MVP',
      '14x Pro Bowl',
      '71,940 passing yards',
      '539 passing TDs',
    ],
    passing: {
      attempts: 9380,
      completions: 6125,
      yards: 71940,
      touchdowns: 539,
      interceptions: 251,
      qbRating: 96.5,
    },
    rushing: {
      attempts: 667,
      yards: 667,
      touchdowns: 18,
      average: 1.0,
    },
  },
  {
    id: 'hof-8',
    name: 'Morten Andersen',
    type: 'player',
    position: 'K',
    yearsActive: '1982-2007',
    inductionYear: 2017,
    teamsPrimary: 'NO, ATL',
    achievements: [
      '7x Pro Bowl',
      '2,544 career points',
      '565 field goals made',
      '25 NFL seasons',
    ],
    kicking: {
      fgMade: 565,
      fgAttempts: 709,
      fgPct: 79.7,
      points: 2544,
    },
  },
  {
    id: 'hof-9',
    name: 'Bill Parcells',
    type: 'coach',
    yearsActive: '1983-2006',
    inductionYear: 2013,
    teamsPrimary: 'NYG, NE, DAL',
    achievements: [
      '2x Super Bowl Champion',
      '3x AP Coach of the Year',
      '183 career wins',
      '4 Super Bowl appearances',
    ],
    coaching: {
      wins: 183,
      losses: 138,
      winPct: 57.0,
      playoffAppearances: 10,
      championships: 2,
    },
  },
  {
    id: 'hof-10',
    name: 'Tony Dungy',
    type: 'coach',
    yearsActive: '1996-2008',
    inductionYear: 2016,
    teamsPrimary: 'TB, IND',
    achievements: [
      'Super Bowl XLI Champion',
      'AP Coach of the Year (1997)',
      '148 career wins',
      '10 consecutive playoff appearances',
    ],
    coaching: {
      wins: 148,
      losses: 79,
      winPct: 65.2,
      playoffAppearances: 11,
      championships: 1,
    },
  },
];

export const getCurrentInductees = async (): Promise<HOFMember[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return CURRENT_INDUCTEES;
};

export const getEligibleCandidates = async (): Promise<HOFCandidate[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return ELIGIBLE_CANDIDATES;
};

export const getHOFMembers = async (): Promise<HOFMember[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return HOF_MEMBERS;
};

export const searchHOF = async (query: string): Promise<HOFMember[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  const lowerQuery = query.toLowerCase();
  
  return HOF_MEMBERS.filter(member =>
    member.name.toLowerCase().includes(lowerQuery) ||
    member.teamsPrimary.toLowerCase().includes(lowerQuery) ||
    (member.position && member.position.toLowerCase().includes(lowerQuery))
  );
};
