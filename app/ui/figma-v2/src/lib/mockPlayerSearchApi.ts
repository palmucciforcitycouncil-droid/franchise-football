// Mock Player Search API for NFL simulation game

export interface SearchablePlayer {
  id: string;
  name: string;
  team: string;
  position: string;
  number: number;
  age: number;
  
  // Overall & Potential
  overall: number;
  potential: number;
  
  // Physical Attributes
  speed: number;
  strength: number;
  agility: number;
  stamina: number;
  
  // Skill Attributes
  throwPower: number;
  throwAccuracy: number;
  catching: number;
  tackle: number;
  awareness: number;
  
  // Other Stats
  injury: number;
  morale: number;
  
  // Contract
  contract: string;
  years: number;
  
  // Status
  depth: string;
  health: string;
}

export interface SearchFilters {
  name?: string;
  position?: string;
  team?: string;
  
  // Range filters
  ageMin?: number;
  ageMax?: number;
  overallMin?: number;
  overallMax?: number;
  potentialMin?: number;
  potentialMax?: number;
  speedMin?: number;
  speedMax?: number;
  strengthMin?: number;
  strengthMax?: number;
  agilityMin?: number;
  agilityMax?: number;
  throwPowerMin?: number;
  throwPowerMax?: number;
  throwAccuracyMin?: number;
  throwAccuracyMax?: number;
  catchingMin?: number;
  catchingMax?: number;
  tackleMin?: number;
  tackleMax?: number;
  awarenessMin?: number;
  awarenessMax?: number;
}

// Mock database of all players in the league
const ALL_PLAYERS: SearchablePlayer[] = [
  // QBs
  { id: 'p1', name: 'Patrick Mahomes', team: 'KC', position: 'QB', number: 15, age: 28, overall: 99, potential: 99, speed: 83, strength: 80, agility: 86, stamina: 95, throwPower: 99, throwAccuracy: 97, catching: 45, tackle: 20, awareness: 96, injury: 10, morale: 95, contract: '10yr/$450M', years: 8, depth: 'QB1', health: 'Healthy' },
  { id: 'p2', name: 'Joe Burrow', team: 'CIN', position: 'QB', number: 9, age: 27, overall: 94, potential: 97, speed: 78, strength: 75, agility: 82, stamina: 92, throwPower: 94, throwAccuracy: 95, catching: 42, tackle: 18, awareness: 93, injury: 22, morale: 90, contract: '5yr/$275M', years: 4, depth: 'QB1', health: 'Healthy' },
  { id: 'p3', name: 'Josh Allen', team: 'BUF', position: 'QB', number: 17, age: 27, overall: 95, potential: 96, speed: 85, strength: 88, agility: 84, stamina: 94, throwPower: 99, throwAccuracy: 88, catching: 48, tackle: 25, awareness: 92, injury: 18, morale: 92, contract: '6yr/$258M', years: 3, depth: 'QB1', health: 'Healthy' },
  { id: 'p4', name: 'Lamar Jackson', team: 'BAL', position: 'QB', number: 8, age: 27, overall: 93, potential: 94, speed: 96, strength: 78, agility: 95, stamina: 96, throwPower: 92, throwAccuracy: 86, catching: 50, tackle: 22, awareness: 89, injury: 25, morale: 88, contract: '5yr/$260M', years: 4, depth: 'QB1', health: 'Healthy' },
  { id: 'p5', name: 'Dak Prescott', team: 'DAL', position: 'QB', number: 4, age: 30, overall: 89, potential: 89, speed: 80, strength: 81, agility: 79, stamina: 91, throwPower: 90, throwAccuracy: 91, catching: 44, tackle: 19, awareness: 90, injury: 20, morale: 87, contract: '4yr/$160M', years: 2, depth: 'QB1', health: 'Healthy' },
  
  // RBs
  { id: 'p6', name: 'Christian McCaffrey', team: 'SF', position: 'RB', number: 23, age: 27, overall: 97, potential: 95, speed: 94, strength: 76, agility: 96, stamina: 90, throwPower: 35, throwAccuracy: 38, catching: 92, tackle: 40, awareness: 94, injury: 30, morale: 93, contract: '4yr/$64M', years: 2, depth: 'RB1', health: 'Healthy' },
  { id: 'p7', name: 'Derrick Henry', team: 'TEN', position: 'RB', number: 22, age: 30, overall: 91, potential: 88, speed: 89, strength: 95, agility: 82, stamina: 96, throwPower: 30, throwAccuracy: 32, catching: 74, tackle: 45, awareness: 88, injury: 15, morale: 85, contract: '2yr/$16M', years: 1, depth: 'RB1', health: 'Healthy' },
  { id: 'p8', name: 'Bijan Robinson', team: 'ATL', position: 'RB', number: 7, age: 22, overall: 85, potential: 95, speed: 92, strength: 80, agility: 93, stamina: 94, throwPower: 32, throwAccuracy: 35, catching: 86, tackle: 38, awareness: 82, injury: 8, morale: 95, contract: '4yr/$14M', years: 4, depth: 'RB1', health: 'Healthy' },
  { id: 'p9', name: 'Saquon Barkley', team: 'NYG', position: 'RB', number: 26, age: 26, overall: 90, potential: 92, speed: 95, strength: 82, agility: 96, stamina: 91, throwPower: 33, throwAccuracy: 36, catching: 88, tackle: 42, awareness: 87, injury: 32, morale: 80, contract: '3yr/$31M', years: 2, depth: 'RB1', health: 'Q' },
  { id: 'p10', name: 'Nick Chubb', team: 'CLE', position: 'RB', number: 24, age: 28, overall: 92, potential: 90, speed: 91, strength: 90, agility: 88, stamina: 93, throwPower: 31, throwAccuracy: 34, catching: 72, tackle: 48, awareness: 89, injury: 35, morale: 88, contract: '3yr/$36M', years: 1, depth: 'RB1', health: 'IR' },
  
  // WRs
  { id: 'p11', name: 'Tyreek Hill', team: 'MIA', position: 'WR', number: 10, age: 29, overall: 97, potential: 94, speed: 99, strength: 70, agility: 97, stamina: 92, throwPower: 34, throwAccuracy: 36, catching: 96, tackle: 28, awareness: 92, injury: 12, morale: 91, contract: '4yr/$120M', years: 2, depth: 'WR1', health: 'Healthy' },
  { id: 'p12', name: 'Justin Jefferson', team: 'MIN', position: 'WR', number: 18, age: 24, overall: 98, potential: 99, speed: 94, strength: 74, agility: 95, stamina: 94, throwPower: 32, throwAccuracy: 35, catching: 98, tackle: 30, awareness: 95, injury: 10, morale: 94, contract: '4yr/$140M', years: 4, depth: 'WR1', health: 'Healthy' },
  { id: 'p13', name: 'CeeDee Lamb', team: 'DAL', position: 'WR', number: 88, age: 24, overall: 94, potential: 97, speed: 92, strength: 76, agility: 93, stamina: 93, throwPower: 33, throwAccuracy: 36, catching: 95, tackle: 32, awareness: 91, injury: 14, morale: 89, contract: '4yr/$136M', years: 4, depth: 'WR1', health: 'Healthy' },
  { id: 'p14', name: 'Stefon Diggs', team: 'BUF', position: 'WR', number: 14, age: 30, overall: 92, potential: 89, speed: 91, strength: 72, agility: 90, stamina: 91, throwPower: 31, throwAccuracy: 34, catching: 94, tackle: 29, awareness: 93, injury: 18, morale: 84, contract: '4yr/$96M', years: 1, depth: 'WR1', health: 'Healthy' },
  { id: 'p15', name: 'Garrett Wilson', team: 'NYJ', position: 'WR', number: 5, age: 23, overall: 88, potential: 96, speed: 93, strength: 71, agility: 94, stamina: 92, throwPower: 32, throwAccuracy: 35, catching: 91, tackle: 27, awareness: 86, injury: 9, morale: 90, contract: '4yr/$20M', years: 2, depth: 'WR1', health: 'Healthy' },
  
  // TEs
  { id: 'p16', name: 'Travis Kelce', team: 'KC', position: 'TE', number: 87, age: 34, overall: 95, potential: 90, speed: 84, strength: 82, agility: 85, stamina: 89, throwPower: 35, throwAccuracy: 38, catching: 96, tackle: 52, awareness: 96, injury: 22, morale: 93, contract: '2yr/$34M', years: 1, depth: 'TE1', health: 'Healthy' },
  { id: 'p17', name: 'George Kittle', team: 'SF', position: 'TE', number: 85, age: 30, overall: 94, potential: 91, speed: 86, strength: 88, agility: 84, stamina: 92, throwPower: 36, throwAccuracy: 39, catching: 94, tackle: 78, awareness: 94, injury: 25, morale: 95, contract: '5yr/$75M', years: 3, depth: 'TE1', health: 'Healthy' },
  { id: 'p18', name: 'Mark Andrews', team: 'BAL', position: 'TE', number: 89, age: 28, overall: 91, potential: 92, speed: 82, strength: 84, agility: 81, stamina: 90, throwPower: 34, throwAccuracy: 37, catching: 93, tackle: 56, awareness: 90, injury: 28, morale: 88, contract: '4yr/$56M', years: 2, depth: 'TE1', health: 'Healthy' },
  { id: 'p19', name: 'T.J. Hockenson', team: 'MIN', position: 'TE', number: 87, age: 26, overall: 88, potential: 93, speed: 83, strength: 81, agility: 82, stamina: 88, throwPower: 33, throwAccuracy: 36, catching: 90, tackle: 60, awareness: 87, injury: 30, morale: 86, contract: '4yr/$68M', years: 3, depth: 'TE1', health: 'Q' },
  { id: 'p20', name: 'Sam LaPorta', team: 'DET', position: 'TE', number: 87, age: 23, overall: 84, potential: 94, speed: 84, strength: 78, agility: 83, stamina: 87, throwPower: 32, throwAccuracy: 35, catching: 88, tackle: 54, awareness: 83, injury: 10, morale: 92, contract: '4yr/$8M', years: 4, depth: 'TE1', health: 'Healthy' },
  
  // Defensive Players
  { id: 'p21', name: 'Micah Parsons', team: 'DAL', position: 'LB', number: 11, age: 25, overall: 98, potential: 99, speed: 91, strength: 88, agility: 92, stamina: 96, throwPower: 30, throwAccuracy: 32, catching: 65, tackle: 96, awareness: 95, injury: 12, morale: 94, contract: '4yr/$96M', years: 1, depth: 'OLB1', health: 'Healthy' },
  { id: 'p22', name: 'Fred Warner', team: 'SF', position: 'LB', number: 54, age: 27, overall: 96, potential: 95, speed: 88, strength: 82, agility: 89, stamina: 95, throwPower: 31, throwAccuracy: 33, catching: 72, tackle: 95, awareness: 97, injury: 15, morale: 92, contract: '5yr/$95M', years: 3, depth: 'MLB1', health: 'Healthy' },
  { id: 'p23', name: 'Jalen Ramsey', team: 'MIA', position: 'CB', number: 5, age: 29, overall: 94, potential: 92, speed: 94, strength: 78, agility: 96, stamina: 93, throwPower: 32, throwAccuracy: 34, catching: 82, tackle: 76, awareness: 94, injury: 18, morale: 89, contract: '3yr/$72M', years: 2, depth: 'CB1', health: 'Healthy' },
  { id: 'p24', name: 'Sauce Gardner', team: 'NYJ', position: 'CB', number: 1, age: 23, overall: 93, potential: 98, speed: 92, strength: 80, agility: 94, stamina: 95, throwPower: 30, throwAccuracy: 32, catching: 78, tackle: 80, awareness: 91, injury: 8, morale: 96, contract: '4yr/$16M', years: 3, depth: 'CB1', health: 'Healthy' },
  { id: 'p25', name: 'Minkah Fitzpatrick', team: 'PIT', position: 'S', number: 39, age: 27, overall: 95, potential: 94, speed: 90, strength: 81, agility: 91, stamina: 94, throwPower: 31, throwAccuracy: 33, catching: 84, tackle: 86, awareness: 96, injury: 16, morale: 90, contract: '4yr/$73M', years: 2, depth: 'FS1', health: 'Healthy' },
  { id: 'p26', name: 'Aaron Donald', team: 'LAR', position: 'DL', number: 99, age: 32, overall: 99, potential: 95, speed: 86, strength: 99, agility: 88, stamina: 90, throwPower: 28, throwAccuracy: 30, catching: 45, tackle: 98, awareness: 99, injury: 20, morale: 91, contract: '3yr/$95M', years: 1, depth: 'DT1', health: 'Healthy' },
  { id: 'p27', name: 'Nick Bosa', team: 'SF', position: 'DL', number: 97, age: 26, overall: 97, potential: 98, speed: 88, strength: 92, agility: 90, stamina: 93, throwPower: 29, throwAccuracy: 31, catching: 48, tackle: 96, awareness: 94, injury: 18, morale: 93, contract: '5yr/$170M', years: 5, depth: 'DE1', health: 'Healthy' },
  { id: 'p28', name: 'Maxx Crosby', team: 'LV', position: 'DL', number: 98, age: 26, overall: 94, potential: 96, speed: 87, strength: 90, agility: 88, stamina: 96, throwPower: 28, throwAccuracy: 30, catching: 46, tackle: 94, awareness: 92, injury: 12, morale: 95, contract: '4yr/$98M', years: 3, depth: 'DE1', health: 'Healthy' },
  { id: 'p29', name: 'Roquan Smith', team: 'BAL', position: 'LB', number: 18, age: 27, overall: 95, potential: 94, speed: 89, strength: 84, agility: 91, stamina: 96, throwPower: 30, throwAccuracy: 32, catching: 70, tackle: 94, awareness: 96, injury: 14, morale: 91, contract: '5yr/$100M', years: 4, depth: 'MLB1', health: 'Healthy' },
  { id: 'p30', name: 'Patrick Surtain II', team: 'DEN', position: 'CB', number: 2, age: 23, overall: 92, potential: 97, speed: 93, strength: 79, agility: 95, stamina: 94, throwPower: 31, throwAccuracy: 33, catching: 80, tackle: 78, awareness: 90, injury: 10, morale: 93, contract: '4yr/$18M', years: 2, depth: 'CB1', health: 'Healthy' },
];

export const searchPlayers = async (filters: SearchFilters): Promise<SearchablePlayer[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  
  let results = [...ALL_PLAYERS];
  
  // Name filter
  if (filters.name && filters.name.trim()) {
    const lowerName = filters.name.toLowerCase();
    results = results.filter(p => p.name.toLowerCase().includes(lowerName));
  }
  
  // Position filter
  if (filters.position && filters.position !== 'all') {
    results = results.filter(p => p.position === filters.position);
  }
  
  // Team filter
  if (filters.team && filters.team !== 'all') {
    results = results.filter(p => p.team === filters.team);
  }
  
  // Range filters
  if (filters.ageMin !== undefined) {
    results = results.filter(p => p.age >= filters.ageMin!);
  }
  if (filters.ageMax !== undefined) {
    results = results.filter(p => p.age <= filters.ageMax!);
  }
  
  if (filters.overallMin !== undefined) {
    results = results.filter(p => p.overall >= filters.overallMin!);
  }
  if (filters.overallMax !== undefined) {
    results = results.filter(p => p.overall <= filters.overallMax!);
  }
  
  if (filters.potentialMin !== undefined) {
    results = results.filter(p => p.potential >= filters.potentialMin!);
  }
  if (filters.potentialMax !== undefined) {
    results = results.filter(p => p.potential <= filters.potentialMax!);
  }
  
  if (filters.speedMin !== undefined) {
    results = results.filter(p => p.speed >= filters.speedMin!);
  }
  if (filters.speedMax !== undefined) {
    results = results.filter(p => p.speed <= filters.speedMax!);
  }
  
  if (filters.strengthMin !== undefined) {
    results = results.filter(p => p.strength >= filters.strengthMin!);
  }
  if (filters.strengthMax !== undefined) {
    results = results.filter(p => p.strength <= filters.strengthMax!);
  }
  
  if (filters.agilityMin !== undefined) {
    results = results.filter(p => p.agility >= filters.agilityMin!);
  }
  if (filters.agilityMax !== undefined) {
    results = results.filter(p => p.agility <= filters.agilityMax!);
  }
  
  if (filters.throwPowerMin !== undefined) {
    results = results.filter(p => p.throwPower >= filters.throwPowerMin!);
  }
  if (filters.throwPowerMax !== undefined) {
    results = results.filter(p => p.throwPower <= filters.throwPowerMax!);
  }
  
  if (filters.throwAccuracyMin !== undefined) {
    results = results.filter(p => p.throwAccuracy >= filters.throwAccuracyMin!);
  }
  if (filters.throwAccuracyMax !== undefined) {
    results = results.filter(p => p.throwAccuracy <= filters.throwAccuracyMax!);
  }
  
  if (filters.catchingMin !== undefined) {
    results = results.filter(p => p.catching >= filters.catchingMin!);
  }
  if (filters.catchingMax !== undefined) {
    results = results.filter(p => p.catching <= filters.catchingMax!);
  }
  
  if (filters.tackleMin !== undefined) {
    results = results.filter(p => p.tackle >= filters.tackleMin!);
  }
  if (filters.tackleMax !== undefined) {
    results = results.filter(p => p.tackle <= filters.tackleMax!);
  }
  
  if (filters.awarenessMin !== undefined) {
    results = results.filter(p => p.awareness >= filters.awarenessMin!);
  }
  if (filters.awarenessMax !== undefined) {
    results = results.filter(p => p.awareness <= filters.awarenessMax!);
  }
  
  // Sort by overall rating descending
  results.sort((a, b) => b.overall - a.overall);
  
  return results;
};

export const getAllTeams = (): string[] => {
  return Array.from(new Set(ALL_PLAYERS.map(p => p.team))).sort();
};

export const getAllPositions = (): string[] => {
  return Array.from(new Set(ALL_PLAYERS.map(p => p.position))).sort();
};
