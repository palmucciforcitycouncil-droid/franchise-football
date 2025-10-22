// Depth Chart Auto-Fill Logic per GDD v3.2 §5.2 and §3.1.8.4

import { PlayerRow, DepthSlot, PositionBucket, POSITION_BUCKETS, AUTO_FILL_RULES, ELIGIBILITY_RULES } from '../types/roster';

export interface AutoFillResult {
  depthChart: DepthSlot[];
  warnings: string[];
  changes: Array<{
    position: string;
    slot: number;
    oldPlayer?: string;
    newPlayer: string;
  }>;
}

export function autoFillDepthChart(
  players: PlayerRow[],
  currentDepthChart: DepthSlot[] = []
): AutoFillResult {
  const depthChart: DepthSlot[] = [];
  const warnings: string[] = [];
  const changes: Array<{
    position: string;
    slot: number;
    oldPlayer?: string;
    newPlayer: string;
  }> = [];

  // Create a map of current depth chart for comparison
  const currentMap = new Map<string, string>();
  currentDepthChart.forEach(slot => {
    const key = `${slot.unit}-${slot.pos}-${slot.slot}`;
    currentMap.set(key, slot.player_id);
  });

  // Process each position bucket
  for (const bucket of POSITION_BUCKETS) {
    const eligiblePlayers = getEligiblePlayers(players, bucket.position);
    
    if (eligiblePlayers.length === 0) {
      warnings.push(`No eligible players found for ${bucket.position}`);
      continue;
    }

    // Sort players according to auto-fill rules
    const sortedPlayers = sortPlayersByRules(eligiblePlayers);

    // Assign players to depth slots
    for (let slot = 1; slot <= bucket.depth_target; slot++) {
      const player = sortedPlayers[slot - 1];
      if (player) {
        const depthSlot: DepthSlot = {
          unit: bucket.unit,
          pos: bucket.position,
          slot: slot,
          player_id: player.player_id
        };
        depthChart.push(depthSlot);

        // Track changes
        const key = `${bucket.unit}-${bucket.position}-${slot}`;
        const oldPlayerId = currentMap.get(key);
        if (oldPlayerId !== player.player_id) {
          changes.push({
            position: bucket.position,
            slot: slot,
            oldPlayer: oldPlayerId,
            newPlayer: player.player_id
          });
        }
      } else {
        warnings.push(`Insufficient depth at ${bucket.position} (need ${bucket.depth_target}, have ${eligiblePlayers.length})`);
      }
    }
  }

  return {
    depthChart,
    warnings,
    changes
  };
}

function getEligiblePlayers(players: PlayerRow[], position: string): PlayerRow[] {
  return players.filter(player => {
    // Must match required position
    if (ELIGIBILITY_RULES.mustMatchPosition && player.pos !== position) {
      return false;
    }

    // Injury gating
    if (ELIGIBILITY_RULES.injuryGating) {
      if (ELIGIBILITY_RULES.excludeOutOfSeason && player.status.injury === 'OOS') {
        return false;
      }
      if (!ELIGIBILITY_RULES.allowQuestionable && player.status.injury === 'Q') {
        return false;
      }
    }

    return true;
  });
}

function sortPlayersByRules(players: PlayerRow[]): PlayerRow[] {
  return [...players].sort((a, b) => {
    for (const rule of AUTO_FILL_RULES) {
      let comparison = 0;
      
      switch (rule.sortBy) {
        case 'OVR':
          comparison = a.ovr - b.ovr;
          break;
        case 'STA':
          // Assuming stamina is available in player data
          comparison = (a as any).sta - (b as any).sta;
          break;
        case 'AGE':
          comparison = a.age - b.age;
          break;
        case 'PLAYER_ID':
          comparison = a.player_id.localeCompare(b.player_id);
          break;
      }

      if (comparison !== 0) {
        return rule.order === 'DESC' ? -comparison : comparison;
      }
    }
    return 0;
  });
}

// Special position handling per GDD v3.2 §3.1.8.4
export function assignSpecialTeams(
  players: PlayerRow[],
  depthChart: DepthSlot[]
): DepthSlot[] {
  const specialTeamsSlots: DepthSlot[] = [];

  // KR assignment - prefer RB/WR with highest speed
  const krCandidates = players.filter(p => ['RB', 'WR'].includes(p.pos));
  if (krCandidates.length > 0) {
    const krPlayer = krCandidates.sort((a, b) => (b as any).spd - (a as any).spd)[0];
    specialTeamsSlots.push({
      unit: 'ST',
      pos: 'KR',
      slot: 1,
      player_id: krPlayer.player_id
    });
  }

  // PR assignment - prefer WR with highest agility
  const prCandidates = players.filter(p => p.pos === 'WR');
  if (prCandidates.length > 0) {
    const prPlayer = prCandidates.sort((a, b) => (b as any).agi - (a as any).agi)[0];
    specialTeamsSlots.push({
      unit: 'ST',
      pos: 'PR',
      slot: 1,
      player_id: prPlayer.player_id
    });
  }

  // LS assignment - prefer OL by awareness + strength
  const lsCandidates = players.filter(p => ['C', 'G', 'T'].includes(p.pos));
  if (lsCandidates.length > 0) {
    const lsPlayer = lsCandidates.sort((a, b) => {
      const scoreA = (a as any).awr + (a as any).str;
      const scoreB = (b as any).awr + (b as any).str;
      return scoreB - scoreA;
    })[0];
    specialTeamsSlots.push({
      unit: 'ST',
      pos: 'LS',
      slot: 1,
      player_id: lsPlayer.player_id
    });
  }

  return [...depthChart, ...specialTeamsSlots];
}

// Validate depth chart completeness
export function validateDepthChart(
  depthChart: DepthSlot[],
  players: PlayerRow[]
): string[] {
  const warnings: string[] = [];
  
  for (const bucket of POSITION_BUCKETS) {
    const slots = depthChart.filter(slot => 
      slot.unit === bucket.unit && slot.pos === bucket.position
    );
    
    if (slots.length < bucket.depth_target) {
      warnings.push(`Needs Attention: ${bucket.position} (${slots.length}/${bucket.depth_target})`);
    }
  }

  return warnings;
}
