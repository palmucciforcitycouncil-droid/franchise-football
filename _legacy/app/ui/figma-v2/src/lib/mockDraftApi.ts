/**
 * Mock Draft API
 * Provides draft prospect data for the Draft Board
 */

export interface DraftProspect {
  prospect_id: string;
  name: string;
  position: string;
  college: string;
  overall: number;
  potential: number;
  speed: number;
  agility: number;
  strength: number;
  awareness: number;
  board_score: number;
  tier: number;
  drafted: boolean;
  draft_round?: number;
  draft_pick?: number;
  team_drafted?: string;
  watchlist?: boolean;
}

export interface DraftFilters {
  year?: number;
  position?: string;
  minOverall?: number;
  minPotential?: number;
  showDrafted?: boolean;
  sortBy?: 'board_score' | 'overall' | 'potential' | 'name';
  sortOrder?: 'asc' | 'desc';
}

// Generate mock prospects
const positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K', 'P'];
const colleges = [
  'Alabama', 'Ohio State', 'Georgia', 'Michigan', 'LSU', 'Clemson',
  'Texas', 'USC', 'Florida', 'Penn State', 'Oklahoma', 'Notre Dame',
  'Oregon', 'Auburn', 'Florida State', 'Texas A&M', 'UCLA', 'Wisconsin'
];

const firstNames = [
  'Marcus', 'Jaylen', 'Xavier', 'Darius', 'Tyler', 'Brandon', 'Jordan',
  'Cameron', 'Isaiah', 'Jackson', 'Malik', 'Devin', 'Trey', 'Jamal',
  'Connor', 'Blake', 'Hunter', 'Chase', 'Zach', 'Ryan'
];

const lastNames = [
  'Williams', 'Johnson', 'Smith', 'Brown', 'Jones', 'Davis', 'Miller',
  'Wilson', 'Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson', 'White',
  'Martinez', 'Robinson', 'Lewis', 'Harris', 'Clark', 'Walker'
];

function generateProspects(count: number, year: number): DraftProspect[] {
  const prospects: DraftProspect[] = [];
  const seed = year * 1000; // Different seed per year
  
  for (let i = 0; i < count; i++) {
    const position = positions[Math.floor((Math.abs(Math.sin(seed + i * 0.1)) * 1000) % positions.length)];
    const overall = Math.floor((Math.abs(Math.sin(seed + i * 0.2)) * 40) + 60); // 60-99
    const potential = Math.min(99, overall + Math.floor((Math.abs(Math.sin(seed + i * 0.3)) * 20) - 5));
    // Only current year has drafted players
    const isDrafted = year < 2025 && Math.abs(Math.sin(seed + i * 0.4)) < 0.3; // 30% drafted for past years
    
    const prospect: DraftProspect = {
      prospect_id: `${year}_PROSPECT_${i + 1}`,
      name: `${firstNames[Math.floor((Math.abs(Math.sin(seed + i * 0.5)) * 1000) % firstNames.length)]} ${lastNames[Math.floor((Math.abs(Math.sin(seed + i * 0.6)) * 1000) % lastNames.length)]}`,
      position,
      college: colleges[Math.floor((Math.abs(Math.sin(seed + i * 0.7)) * 1000) % colleges.length)],
      overall,
      potential,
      speed: Math.floor((Math.abs(Math.sin(seed + i * 0.8)) * 40) + 60),
      agility: Math.floor((Math.abs(Math.sin(seed + i * 0.9)) * 40) + 60),
      strength: Math.floor((Math.abs(Math.sin(seed + i * 1.0)) * 40) + 60),
      awareness: Math.floor((Math.abs(Math.sin(seed + i * 1.1)) * 40) + 60),
      board_score: Math.floor((overall * 0.6 + potential * 0.4) * 100) / 100,
      tier: overall >= 90 ? 1 : overall >= 85 ? 2 : overall >= 80 ? 3 : overall >= 75 ? 4 : 5,
      drafted: isDrafted,
    };

    if (isDrafted) {
      prospect.draft_round = Math.floor((Math.abs(Math.sin(seed + i * 1.2)) * 7) + 1);
      prospect.draft_pick = Math.floor((Math.abs(Math.sin(seed + i * 1.3)) * 32) + 1);
      prospect.team_drafted = ['NE', 'KC', 'SF', 'DAL', 'GB'][Math.floor((Math.abs(Math.sin(seed + i * 1.4)) * 1000) % 5)];
    }

    prospects.push(prospect);
  }

  return prospects;
}

// Generate 4 years of draft classes
const draftClasses: { [year: number]: DraftProspect[] } = {
  2025: generateProspects(Math.floor(Math.random() * 51) + 200, 2025), // Current year: 200-250
  2024: generateProspects(Math.floor(Math.random() * 51) + 200, 2024),
  2023: generateProspects(Math.floor(Math.random() * 51) + 200, 2023),
  2022: generateProspects(Math.floor(Math.random() * 51) + 200, 2022),
};

const mockProspects = draftClasses[2025]; // Default to current year

// Mock watchlist storage (in real app, this would be in a database)
const watchlistIds = new Set<string>();
// Mock draft board storage - ordered list of prospect IDs
const draftBoardIds: string[] = [];

// Add some prospects to watchlist by default (for demo purposes)
mockProspects.slice(0, 15).forEach((p, i) => {
  if (i % 3 === 0) { // Add every 3rd prospect to watchlist
    watchlistIds.add(p.prospect_id);
    p.watchlist = true;
  }
});

// Add some prospects to draft board by default (for demo purposes)
mockProspects.slice(0, 8).forEach((p, i) => {
  if (i % 2 === 0) { // Add every 2nd prospect to draft board
    draftBoardIds.push(p.prospect_id);
  }
});

export async function getDraftProspects(filters: DraftFilters = {}): Promise<DraftProspect[]> {
  await new Promise(resolve => setTimeout(resolve, 500)); // Simulate network delay

  const year = filters.year || 2025;
  let filtered = [...(draftClasses[year] || draftClasses[2025])];

  // Update watchlist status for all prospects
  filtered = filtered.map(p => ({
    ...p,
    watchlist: watchlistIds.has(p.prospect_id)
  }));

  // Apply filters
  if (filters.position === 'WATCHLIST') {
    filtered = filtered.filter(p => watchlistIds.has(p.prospect_id));
  } else if (filters.position && filters.position !== 'ALL') {
    filtered = filtered.filter(p => p.position === filters.position);
  }

  if (filters.minOverall) {
    filtered = filtered.filter(p => p.overall >= filters.minOverall!);
  }

  if (filters.minPotential) {
    filtered = filtered.filter(p => p.potential >= filters.minPotential!);
  }

  if (filters.showDrafted === false) {
    filtered = filtered.filter(p => !p.drafted);
  }

  // Apply sorting
  const sortBy = filters.sortBy || 'board_score';
  const sortOrder = filters.sortOrder || 'desc';

  filtered.sort((a, b) => {
    let aVal = a[sortBy];
    let bVal = b[sortBy];

    if (sortBy === 'name') {
      return sortOrder === 'asc' 
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
  });

  return filtered;
}

export async function toggleWatchlist(prospectId: string): Promise<boolean> {
  await new Promise(resolve => setTimeout(resolve, 200));
  
  if (watchlistIds.has(prospectId)) {
    watchlistIds.delete(prospectId);
    return false;
  } else {
    watchlistIds.add(prospectId);
    return true;
  }
}

export async function addToDraftBoard(prospectId: string): Promise<boolean> {
  await new Promise(resolve => setTimeout(resolve, 200));
  
  if (!draftBoardIds.includes(prospectId)) {
    draftBoardIds.push(prospectId);
    return true;
  }
  return false;
}

export async function removeFromDraftBoard(prospectId: string): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, 200));
  
  const index = draftBoardIds.indexOf(prospectId);
  if (index > -1) {
    draftBoardIds.splice(index, 1);
  }
}

export async function getDraftBoardPlayers(): Promise<DraftProspect[]> {
  await new Promise(resolve => setTimeout(resolve, 200));
  
  // Return prospects in the order they were added to the draft board
  const boardProspects: DraftProspect[] = [];
  
  for (const id of draftBoardIds) {
    // Search all draft classes for the prospect
    for (const year in draftClasses) {
      const prospect = draftClasses[year].find(p => p.prospect_id === id);
      if (prospect) {
        boardProspects.push({
          ...prospect,
          watchlist: watchlistIds.has(id)
        });
        break;
      }
    }
  }
  
  return boardProspects;
}

export async function reorderDraftBoard(prospectIds: string[]): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, 200));
  
  // Replace the entire draft board order
  draftBoardIds.length = 0;
  draftBoardIds.push(...prospectIds);
}

export async function getBestAvailable(limit: number = 10, position?: string): Promise<DraftProspect[]> {
  await new Promise(resolve => setTimeout(resolve, 300));

  let available = mockProspects.filter(p => !p.drafted);

  if (position && position !== 'ALL') {
    available = available.filter(p => p.position === position);
  }

  return available
    .sort((a, b) => b.board_score - a.board_score)
    .slice(0, limit);
}

export async function getProspectsByTier(position: string): Promise<{ tier: number; prospects: DraftProspect[] }[]> {
  await new Promise(resolve => setTimeout(resolve, 400));

  let filtered = mockProspects;
  
  if (position !== 'ALL') {
    filtered = filtered.filter(p => p.position === position);
  }

  const tiers: { [key: number]: DraftProspect[] } = {};
  
  filtered.forEach(prospect => {
    if (!tiers[prospect.tier]) {
      tiers[prospect.tier] = [];
    }
    tiers[prospect.tier].push(prospect);
  });

  return Object.entries(tiers)
    .map(([tier, prospects]) => ({
      tier: Number(tier),
      prospects: prospects.sort((a, b) => b.board_score - a.board_score)
    }))
    .sort((a, b) => a.tier - b.tier);
}
