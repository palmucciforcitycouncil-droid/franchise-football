export interface CapYearData {
  year: number;
  team_obligations: number;
  league_cap: number;
  cap_space: number;
  is_projected: boolean;
}

export interface CapSummaryResponse {
  team_id: number;
  base_year: number;
  items: CapYearData[];
}

// Mock cap growth rate (e.g., 5% per year)
const CAP_GROWTH_RATE = 0.05;

// Round down to nearest number ending in 0 or 5
function roundCapValue(value: number): number {
  const floor = Math.floor(value / 5) * 5;
  return floor;
}

export async function getCapSummary(teamId: number = 1): Promise<CapSummaryResponse> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));

  const currentYear = 2025;
  const baseLeagueCap = 255000000; // $255M base cap
  const currentTeamObligations = 242500000; // $242.5M in obligations
  
  const items: CapYearData[] = [];
  
  for (let i = 0; i < 4; i++) {
    const year = currentYear + i;
    const isProjected = i > 0;
    
    // Calculate league cap for future years with growth
    let leagueCap = baseLeagueCap;
    if (isProjected) {
      leagueCap = baseLeagueCap * Math.pow(1 + CAP_GROWTH_RATE, i);
      leagueCap = roundCapValue(leagueCap);
    }
    
    // Simulate team obligations decreasing slightly in future years (contracts expiring)
    let teamObligations = currentTeamObligations;
    if (isProjected) {
      // Each year, some contracts expire
      teamObligations = currentTeamObligations * (1 - (i * 0.15));
      // Add some randomness
      teamObligations += Math.random() * 10000000 - 5000000;
    }
    
    const capSpace = leagueCap - teamObligations;
    
    items.push({
      year,
      team_obligations: Math.round(teamObligations),
      league_cap: Math.round(leagueCap),
      cap_space: Math.round(capSpace),
      is_projected: isProjected,
    });
  }
  
  return {
    team_id: teamId,
    base_year: currentYear,
    items,
  };
}
