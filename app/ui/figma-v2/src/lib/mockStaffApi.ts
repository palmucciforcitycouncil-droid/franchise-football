export interface Coach {
  id: string;
  name: string;
  title: 'Head Coach' | 'Offensive Coordinator' | 'Defensive Coordinator' | 'Assistant Coach';
  age: number;
  experience: number;
  salary: string;
  yearsRemaining: number;
  overallRating: number;
  reputation: number;
  background: string;
  attitude: string;
  style: string;
  offense?: string;
  defense?: string;
  focusArea: CoachFocusArea;
}

export interface CoachingPosition {
  positionId: string;
  title: 'Head Coach' | 'Offensive Coordinator' | 'Defensive Coordinator' | 'Assistant Coach';
  coach: Coach | null;
}

export type CoachFocusArea = 
  | 'OF Gameplan'
  | 'DF Gameplan'
  | 'Training'
  | 'Development'
  | 'Scouting'
  | 'Special Teams Work'
  | '2 Min Offense';

export interface AvailableCoach {
  id: string;
  name: string;
  age: number;
  experience: number;
  desiredSalary: string;
  desiredLength: number;
  overallRating: number;
  reputation: number;
  background: string;
  attitude: string;
  style: string;
  specialty: string;
  currentTeam?: string; // Team abbreviation if currently employed, undefined if free agent
  currentRole?: 'Head Coach' | 'Offensive Coordinator' | 'Defensive Coordinator' | 'Assistant Coach';
  offense?: string;
  defense?: string;
}

const COACHING_POSITIONS: CoachingPosition[] = [
  {
    positionId: 'pos-hc',
    title: 'Head Coach',
    coach: {
      id: 'hc-1',
      name: 'Bill Parcells',
      title: 'Head Coach',
      age: 52,
      experience: 18,
      salary: '$4.2M',
      yearsRemaining: 3,
      overallRating: 4,
      reputation: 85,
      background: 'Player',
      attitude: 'Disciplined',
      style: 'Balanced',
      offense: 'West Coast',
      defense: '3-4',
      focusArea: 'Training',
    },
  },
  {
    positionId: 'pos-oc',
    title: 'Offensive Coordinator',
    coach: {
      id: 'oc-1',
      name: 'Josh McDaniels',
      title: 'Offensive Coordinator',
      age: 42,
      experience: 12,
      salary: '$2.1M',
      yearsRemaining: 2,
      overallRating: 3.5,
      reputation: 75,
      background: 'Position Coach',
      attitude: 'Aggressive',
      style: 'Aggressive',
      offense: 'Vertical',
      focusArea: 'OF Gameplan',
    },
  },
  {
    positionId: 'pos-dc',
    title: 'Defensive Coordinator',
    coach: {
      id: 'dc-1',
      name: 'Matt Patricia',
      title: 'Defensive Coordinator',
      age: 45,
      experience: 10,
      salary: '$1.8M',
      yearsRemaining: 2,
      overallRating: 3,
      reputation: 70,
      background: 'Position Coach',
      attitude: 'Relaxed',
      style: 'Conservative',
      defense: '4-3',
      focusArea: 'DF Gameplan',
    },
  },
  {
    positionId: 'pos-ac1',
    title: 'Assistant Coach',
    coach: {
      id: 'ac-1',
      name: 'Ivan Fears',
      title: 'Assistant Coach',
      age: 58,
      experience: 22,
      salary: '$1.2M',
      yearsRemaining: 1,
      overallRating: 3,
      reputation: 68,
      background: 'Position Coach',
      attitude: 'Motivator',
      style: 'Balanced',
      focusArea: 'Development',
    },
  },
  {
    positionId: 'pos-ac2',
    title: 'Assistant Coach',
    coach: {
      id: 'ac-2',
      name: 'Dante Scarnecchia',
      title: 'Assistant Coach',
      age: 61,
      experience: 25,
      salary: '$1.5M',
      yearsRemaining: 1,
      overallRating: 4,
      reputation: 80,
      background: 'Position Coach',
      attitude: 'Disciplined',
      style: 'Conservative',
      focusArea: 'Special Teams Work',
    },
  },
];

const AVAILABLE_COACHES: AvailableCoach[] = [
  // Free Agents
  {
    id: 'avail-1',
    name: 'Brian Daboll',
    age: 48,
    experience: 15,
    desiredSalary: '$2.5M',
    desiredLength: 3,
    overallRating: 4,
    reputation: 78,
    background: 'Coordinator',
    attitude: 'Innovative',
    style: 'Aggressive',
    specialty: 'Offensive Coordinator',
    offense: 'Spread',
  },
  {
    id: 'avail-2',
    name: 'Vic Fangio',
    age: 64,
    experience: 30,
    desiredSalary: '$2.8M',
    desiredLength: 2,
    overallRating: 4.5,
    reputation: 88,
    background: 'Coordinator',
    attitude: 'Veteran',
    style: 'Conservative',
    specialty: 'Defensive Coordinator',
    defense: '3-4',
  },
  {
    id: 'avail-3',
    name: 'Eric Bieniemy',
    age: 54,
    experience: 12,
    desiredSalary: '$2.0M',
    desiredLength: 3,
    overallRating: 3.5,
    reputation: 72,
    background: 'Position Coach',
    attitude: 'Energetic',
    style: 'Aggressive',
    specialty: 'Offensive Coordinator',
    offense: 'West Coast',
  },
  {
    id: 'avail-4',
    name: 'Robert Saleh',
    age: 44,
    experience: 9,
    desiredSalary: '$1.8M',
    desiredLength: 3,
    overallRating: 3.5,
    reputation: 70,
    background: 'Coordinator',
    attitude: 'Energetic',
    style: 'Aggressive',
    specialty: 'Defensive Coordinator',
    defense: '4-3',
  },
  
  // Coaches on other teams
  {
    id: 'avail-5',
    name: 'Brandon Staley',
    age: 40,
    experience: 8,
    desiredSalary: '$1.6M',
    desiredLength: 3,
    overallRating: 3,
    reputation: 65,
    background: 'Position Coach',
    attitude: 'Analytical',
    style: 'Aggressive',
    specialty: 'Defensive Coordinator',
    currentTeam: 'LAC',
    currentRole: 'Assistant Coach',
    defense: '4-3',
  },
  {
    id: 'avail-6',
    name: 'Todd Bowles',
    age: 59,
    experience: 20,
    desiredSalary: '$2.2M',
    desiredLength: 2,
    overallRating: 3.5,
    reputation: 75,
    background: 'Coordinator',
    attitude: 'Disciplined',
    style: 'Balanced',
    specialty: 'Defensive Coordinator',
    currentTeam: 'TB',
    currentRole: 'Assistant Coach',
    defense: '3-4',
  },
  {
    id: 'avail-7',
    name: 'Kellen Moore',
    age: 35,
    experience: 6,
    desiredSalary: '$1.9M',
    desiredLength: 3,
    overallRating: 3.5,
    reputation: 68,
    background: 'Position Coach',
    attitude: 'Innovative',
    style: 'Aggressive',
    specialty: 'Offensive Coordinator',
    currentTeam: 'LAC',
    currentRole: 'Offensive Coordinator',
    offense: 'Spread',
  },
  {
    id: 'avail-8',
    name: 'Raheem Morris',
    age: 47,
    experience: 14,
    desiredSalary: '$2.3M',
    desiredLength: 2,
    overallRating: 3.5,
    reputation: 73,
    background: 'Coordinator',
    attitude: 'Motivator',
    style: 'Balanced',
    specialty: 'Defensive Coordinator',
    currentTeam: 'ATL',
    currentRole: 'Defensive Coordinator',
    defense: '3-4',
  },
  {
    id: 'avail-9',
    name: 'Ben Johnson',
    age: 37,
    experience: 7,
    desiredSalary: '$2.4M',
    desiredLength: 3,
    overallRating: 4,
    reputation: 76,
    background: 'Coordinator',
    attitude: 'Innovative',
    style: 'Aggressive',
    specialty: 'Offensive Coordinator',
    currentTeam: 'DET',
    currentRole: 'Offensive Coordinator',
    offense: 'West Coast',
  },
  {
    id: 'avail-10',
    name: 'DeMeco Ryans',
    age: 39,
    experience: 5,
    desiredSalary: '$2.1M',
    desiredLength: 3,
    overallRating: 4,
    reputation: 79,
    background: 'Player',
    attitude: 'Disciplined',
    style: 'Aggressive',
    specialty: 'Defensive Coordinator',
    currentTeam: 'SF',
    currentRole: 'Defensive Coordinator',
    defense: '4-3',
  },
];

export async function getCurrentStaff(): Promise<CoachingPosition[]> {
  await new Promise(resolve => setTimeout(resolve, 300));
  return COACHING_POSITIONS;
}

export async function getAvailableCoaches(): Promise<AvailableCoach[]> {
  await new Promise(resolve => setTimeout(resolve, 300));
  return AVAILABLE_COACHES;
}

export async function updateCoachFocus(coachId: string, focusArea: CoachFocusArea): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, 200));
  for (const position of COACHING_POSITIONS) {
    if (position.coach?.id === coachId) {
      position.coach.focusArea = focusArea;
      break;
    }
  }
}

export async function fireCoach(coachId: string): Promise<{ success: boolean; message: string }> {
  await new Promise(resolve => setTimeout(resolve, 400));
  
  for (const position of COACHING_POSITIONS) {
    if (position.coach?.id === coachId) {
      const coachName = position.coach.name;
      position.coach = null;
      return {
        success: true,
        message: `${coachName} has been released from the team.`
      };
    }
  }
  
  return { success: false, message: 'Coach not found' };
}

export async function promoteCoach(coachId: string, newTitle: string): Promise<{ success: boolean; message: string }> {
  await new Promise(resolve => setTimeout(resolve, 400));
  
  for (const position of COACHING_POSITIONS) {
    if (position.coach?.id === coachId) {
      return {
        success: true,
        message: `${position.coach.name} has been promoted to ${newTitle}.`
      };
    }
  }
  
  return { success: false, message: 'Coach not found' };
}

export async function resignCoach(coachId: string, years: number, totalValue: number): Promise<{ success: boolean; message: string }> {
  await new Promise(resolve => setTimeout(resolve, 500));
  
  for (const position of COACHING_POSITIONS) {
    if (position.coach?.id === coachId) {
      const apy = totalValue / years;
      return {
        success: true,
        message: `${position.coach.name} has agreed to a ${years}-year, $${totalValue}M contract ($${apy.toFixed(1)}M/yr).`
      };
    }
  }
  
  return { success: false, message: 'Coach not found' };
}

export async function hireCoach(
  coachId: string, 
  positionId: string, 
  years: number, 
  totalValue: number
): Promise<{ success: boolean; message: string }> {
  await new Promise(resolve => setTimeout(resolve, 500));
  
  const availableCoach = AVAILABLE_COACHES.find(c => c.id === coachId);
  if (!availableCoach) {
    return { success: false, message: 'Coach not found' };
  }
  
  const position = COACHING_POSITIONS.find(p => p.positionId === positionId);
  if (!position) {
    return { success: false, message: 'Position not found' };
  }
  
  const desiredTotal = parseFloat(availableCoach.desiredSalary.replace('$', '').replace('M', '')) * years;
  const apy = totalValue / years;
  
  if (totalValue >= desiredTotal * 0.9) {
    // Create new coach from available coach
    const newCoach: Coach = {
      id: `coach-${Date.now()}`,
      name: availableCoach.name,
      title: position.title,
      age: availableCoach.age,
      experience: availableCoach.experience,
      salary: `$${apy.toFixed(1)}M`,
      yearsRemaining: years,
      overallRating: availableCoach.overallRating,
      reputation: availableCoach.reputation,
      background: availableCoach.background,
      attitude: availableCoach.attitude,
      style: availableCoach.style,
      offense: availableCoach.offense,
      defense: availableCoach.defense,
      focusArea: position.title === 'Offensive Coordinator' ? 'OF Gameplan' : 
                 position.title === 'Defensive Coordinator' ? 'DF Gameplan' : 'Training',
    };
    
    position.coach = newCoach;
    
    return {
      success: true,
      message: `${availableCoach.name} has been hired as ${position.title} for ${years} years at $${apy.toFixed(1)}M/yr.`
    };
  } else {
    return {
      success: false,
      message: `${availableCoach.name} rejected the offer. Asking for at least $${(desiredTotal * 0.9 / years).toFixed(1)}M/yr.`
    };
  }
}
