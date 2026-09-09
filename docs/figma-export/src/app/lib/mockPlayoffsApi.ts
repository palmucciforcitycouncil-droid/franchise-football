// Mock API for playoffs data
// GET /api/v1/playoffs

export interface TeamSeed {
  seed: number;
  team_id: number;
  team_name?: string;
  team_abbr?: string;
  wins: number;
  losses: number;
  ties: number;
  power_rank: number;
}

export interface Matchup {
  round_name: string;
  side: 'AFC' | 'NFC' | null;
  higher_seed_team: TeamSeed;
  lower_seed_team: TeamSeed;
  home_team_id: number;
  away_team_id: number;
  winner_team_id?: number;
  higher_seed_score?: number;
  lower_seed_score?: number;
}

export interface Round {
  round_name: 'WC' | 'DIV' | 'CONF' | 'SB';
  matchups: Matchup[];
}

export interface InTheHunt {
  side: 'AFC' | 'NFC';
  team_id: number;
  team_name: string;
  seed_if_made: number;
  gb: number;
  wins: number;
  losses: number;
  ties: number;
}

export interface PlayoffBracketDTO {
  season_year: number;
  rounds: Round[];
  in_the_hunt: InTheHunt[];
}

// Team name mapping
const TEAM_NAMES: Record<number, string> = {
  101: 'Kansas City Chiefs',
  102: 'Buffalo Bills',
  103: 'Baltimore Ravens',
  104: 'Jacksonville Jaguars',
  105: 'Los Angeles Chargers',
  106: 'Miami Dolphins',
  107: 'Pittsburgh Steelers',
  108: 'Cincinnati Bengals',
  109: 'Cleveland Browns',
  110: 'Indianapolis Colts',
  201: 'San Francisco 49ers',
  202: 'Philadelphia Eagles',
  203: 'Dallas Cowboys',
  204: 'Detroit Lions',
  205: 'Tampa Bay Buccaneers',
  206: 'Minnesota Vikings',
  207: 'Green Bay Packers',
  208: 'Los Angeles Rams',
  209: 'Seattle Seahawks',
  210: 'New Orleans Saints',
};

const MOCK_PLAYOFF_DATA: PlayoffBracketDTO = {
  season_year: 2025,
  rounds: [
    {
      round_name: 'WC',
      matchups: [
        {
          round_name: 'WC',
          side: 'AFC',
          higher_seed_team: {
            seed: 2,
            team_id: 102,
            team_name: 'Buffalo Bills',
            team_abbr: 'BUF',
            wins: 13,
            losses: 4,
            ties: 0,
            power_rank: 1580,
          },
          lower_seed_team: {
            seed: 7,
            team_id: 107,
            team_name: 'Pittsburgh Steelers',
            team_abbr: 'PIT',
            wins: 10,
            losses: 7,
            ties: 0,
            power_rank: 1420,
          },
          home_team_id: 102,
          away_team_id: 107,
          higher_seed_score: 31,
          lower_seed_score: 17,
          winner_team_id: 102,
        },
        {
          round_name: 'WC',
          side: 'AFC',
          higher_seed_team: {
            seed: 3,
            team_id: 103,
            team_name: 'Baltimore Ravens',
            wins: 12,
            losses: 5,
            ties: 0,
            power_rank: 1545,
          },
          lower_seed_team: {
            seed: 6,
            team_id: 106,
            team_name: 'Miami Dolphins',
            wins: 11,
            losses: 6,
            ties: 0,
            power_rank: 1460,
          },
          home_team_id: 103,
          away_team_id: 106,
          higher_seed_score: 28,
          lower_seed_score: 24,
          winner_team_id: 103,
        },
        {
          round_name: 'WC',
          side: 'AFC',
          higher_seed_team: {
            seed: 4,
            team_id: 104,
            team_name: 'Jacksonville Jaguars',
            wins: 11,
            losses: 6,
            ties: 0,
            power_rank: 1490,
          },
          lower_seed_team: {
            seed: 5,
            team_id: 105,
            team_name: 'Los Angeles Chargers',
            wins: 11,
            losses: 6,
            ties: 0,
            power_rank: 1510,
          },
          home_team_id: 104,
          away_team_id: 105,
          higher_seed_score: 20,
          lower_seed_score: 27,
          winner_team_id: 105,
        },
        {
          round_name: 'WC',
          side: 'NFC',
          higher_seed_team: {
            seed: 2,
            team_id: 202,
            team_name: 'Philadelphia Eagles',
            wins: 14,
            losses: 3,
            ties: 0,
            power_rank: 1610,
          },
          lower_seed_team: {
            seed: 7,
            team_id: 207,
            team_name: 'Green Bay Packers',
            wins: 9,
            losses: 8,
            ties: 0,
            power_rank: 1380,
          },
          home_team_id: 202,
          away_team_id: 207,
          higher_seed_score: 34,
          lower_seed_score: 23,
          winner_team_id: 202,
        },
        {
          round_name: 'WC',
          side: 'NFC',
          higher_seed_team: {
            seed: 3,
            team_id: 203,
            team_name: 'Dallas Cowboys',
            wins: 12,
            losses: 5,
            ties: 0,
            power_rank: 1550,
          },
          lower_seed_team: {
            seed: 6,
            team_id: 206,
            team_name: 'Minnesota Vikings',
            wins: 10,
            losses: 7,
            ties: 0,
            power_rank: 1450,
          },
          home_team_id: 203,
          away_team_id: 206,
          higher_seed_score: 27,
          lower_seed_score: 30,
          winner_team_id: 206,
        },
        {
          round_name: 'WC',
          side: 'NFC',
          higher_seed_team: {
            seed: 4,
            team_id: 204,
            team_name: 'Detroit Lions',
            wins: 12,
            losses: 5,
            ties: 0,
            power_rank: 1560,
          },
          lower_seed_team: {
            seed: 5,
            team_id: 205,
            team_name: 'Tampa Bay Buccaneers',
            wins: 10,
            losses: 7,
            ties: 0,
            power_rank: 1470,
          },
          home_team_id: 204,
          away_team_id: 205,
          higher_seed_score: 31,
          lower_seed_score: 24,
          winner_team_id: 204,
        },
      ],
    },
    {
      round_name: 'DIV',
      matchups: [
        // AFC Divisional Round
        {
          round_name: 'DIV',
          side: 'AFC',
          higher_seed_team: {
            seed: 1,
            team_id: 101,
            team_name: 'Kansas City Chiefs',
            wins: 14,
            losses: 3,
            ties: 0,
            power_rank: 1620,
          },
          lower_seed_team: {
            seed: 5,
            team_id: 105,
            team_name: 'Los Angeles Chargers',
            wins: 11,
            losses: 6,
            ties: 0,
            power_rank: 1510,
          },
          home_team_id: 101,
          away_team_id: 105,
          higher_seed_score: 27,
          lower_seed_score: 24,
          winner_team_id: 101,
        },
        {
          round_name: 'DIV',
          side: 'AFC',
          higher_seed_team: {
            seed: 2,
            team_id: 102,
            team_name: 'Buffalo Bills',
            wins: 13,
            losses: 4,
            ties: 0,
            power_rank: 1580,
          },
          lower_seed_team: {
            seed: 3,
            team_id: 103,
            team_name: 'Baltimore Ravens',
            wins: 12,
            losses: 5,
            ties: 0,
            power_rank: 1545,
          },
          home_team_id: 102,
          away_team_id: 103,
          higher_seed_score: 31,
          lower_seed_score: 28,
          winner_team_id: 102,
        },
        // NFC Divisional Round
        {
          round_name: 'DIV',
          side: 'NFC',
          higher_seed_team: {
            seed: 1,
            team_id: 201,
            team_name: 'San Francisco 49ers',
            wins: 14,
            losses: 3,
            ties: 0,
            power_rank: 1630,
          },
          lower_seed_team: {
            seed: 6,
            team_id: 206,
            team_name: 'Minnesota Vikings',
            wins: 10,
            losses: 7,
            ties: 0,
            power_rank: 1450,
          },
          home_team_id: 201,
          away_team_id: 206,
          higher_seed_score: 34,
          lower_seed_score: 17,
          winner_team_id: 201,
        },
        {
          round_name: 'DIV',
          side: 'NFC',
          higher_seed_team: {
            seed: 2,
            team_id: 202,
            team_name: 'Philadelphia Eagles',
            wins: 14,
            losses: 3,
            ties: 0,
            power_rank: 1610,
          },
          lower_seed_team: {
            seed: 4,
            team_id: 204,
            team_name: 'Detroit Lions',
            wins: 12,
            losses: 5,
            ties: 0,
            power_rank: 1560,
          },
          home_team_id: 202,
          away_team_id: 204,
          higher_seed_score: 24,
          lower_seed_score: 31,
          winner_team_id: 204,
        },
      ],
    },
    {
      round_name: 'CONF',
      matchups: [
        // AFC Championship
        {
          round_name: 'CONF',
          side: 'AFC',
          higher_seed_team: {
            seed: 1,
            team_id: 101,
            team_name: 'Kansas City Chiefs',
            wins: 14,
            losses: 3,
            ties: 0,
            power_rank: 1620,
          },
          lower_seed_team: {
            seed: 2,
            team_id: 102,
            team_name: 'Buffalo Bills',
            wins: 13,
            losses: 4,
            ties: 0,
            power_rank: 1580,
          },
          home_team_id: 101,
          away_team_id: 102,
          higher_seed_score: 38,
          lower_seed_score: 35,
          winner_team_id: 101,
        },
        // NFC Championship
        {
          round_name: 'CONF',
          side: 'NFC',
          higher_seed_team: {
            seed: 1,
            team_id: 201,
            team_name: 'San Francisco 49ers',
            wins: 14,
            losses: 3,
            ties: 0,
            power_rank: 1630,
          },
          lower_seed_team: {
            seed: 4,
            team_id: 204,
            team_name: 'Detroit Lions',
            wins: 12,
            losses: 5,
            ties: 0,
            power_rank: 1560,
          },
          home_team_id: 201,
          away_team_id: 204,
          higher_seed_score: 31,
          lower_seed_score: 27,
          winner_team_id: 201,
        },
      ],
    },
    {
      round_name: 'SB',
      matchups: [
        {
          round_name: 'SB',
          side: null,
          higher_seed_team: {
            seed: 1,
            team_id: 101,
            team_name: 'Kansas City Chiefs',
            wins: 14,
            losses: 3,
            ties: 0,
            power_rank: 1620,
          },
          lower_seed_team: {
            seed: 1,
            team_id: 201,
            team_name: 'San Francisco 49ers',
            wins: 14,
            losses: 3,
            ties: 0,
            power_rank: 1630,
          },
          home_team_id: 0, // Neutral site
          away_team_id: 0,
          higher_seed_score: 38,
          lower_seed_score: 35,
          winner_team_id: 101,
        },
      ],
    },
  ],
  in_the_hunt: [
    {
      side: 'AFC',
      team_id: 108,
      team_name: 'Cincinnati Bengals',
      seed_if_made: 7,
      gb: 1.0,
      wins: 9,
      losses: 8,
      ties: 0,
    },
    {
      side: 'AFC',
      team_id: 109,
      team_name: 'Cleveland Browns',
      seed_if_made: 8,
      gb: 1.5,
      wins: 8,
      losses: 9,
      ties: 0,
    },
    {
      side: 'AFC',
      team_id: 110,
      team_name: 'Indianapolis Colts',
      seed_if_made: 9,
      gb: 2.0,
      wins: 8,
      losses: 9,
      ties: 0,
    },
    {
      side: 'AFC',
      team_id: 111,
      team_name: 'Houston Texans',
      seed_if_made: 10,
      gb: 2.5,
      wins: 7,
      losses: 10,
      ties: 0,
    },
    {
      side: 'AFC',
      team_id: 112,
      team_name: 'Denver Broncos',
      seed_if_made: 11,
      gb: 3.0,
      wins: 7,
      losses: 10,
      ties: 0,
    },
    {
      side: 'NFC',
      team_id: 208,
      team_name: 'Los Angeles Rams',
      seed_if_made: 7,
      gb: 0.5,
      wins: 9,
      losses: 8,
      ties: 0,
    },
    {
      side: 'NFC',
      team_id: 209,
      team_name: 'Seattle Seahawks',
      seed_if_made: 8,
      gb: 1.5,
      wins: 8,
      losses: 9,
      ties: 0,
    },
    {
      side: 'NFC',
      team_id: 210,
      team_name: 'New Orleans Saints',
      seed_if_made: 9,
      gb: 2.0,
      wins: 7,
      losses: 10,
      ties: 0,
    },
    {
      side: 'NFC',
      team_id: 211,
      team_name: 'Atlanta Falcons',
      seed_if_made: 10,
      gb: 2.5,
      wins: 7,
      losses: 10,
      ties: 0,
    },
    {
      side: 'NFC',
      team_id: 212,
      team_name: 'Arizona Cardinals',
      seed_if_made: 11,
      gb: 3.0,
      wins: 6,
      losses: 11,
      ties: 0,
    },
  ],
};

export const getPlayoffBracket = async (): Promise<PlayoffBracketDTO> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 400));
  return MOCK_PLAYOFF_DATA;
};