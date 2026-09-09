import { TeamSeed } from '../../lib/mockPlayoffsApi';

// Team abbreviation helper
const getTeamAbbr = (team: TeamSeed): string => {
  if (team.team_abbr) return team.team_abbr;
  
  // Fallback abbreviation mapping
  const abbrMap: Record<number, string> = {
    101: 'KC', 102: 'BUF', 103: 'BAL', 104: 'JAX', 105: 'LAC',
    106: 'MIA', 107: 'PIT', 108: 'CIN', 109: 'CLE', 110: 'IND',
    201: 'SF', 202: 'PHI', 203: 'DAL', 204: 'DET', 205: 'TB',
    206: 'MIN', 207: 'GB', 208: 'LAR', 209: 'SEA', 210: 'NO',
  };
  
  return abbrMap[team.team_id] || team.team_name || `T${team.team_id}`;
};

interface BracketMatchupProps {
  higherSeed: TeamSeed | null;
  lowerSeed: TeamSeed | null;
  isPlaceholder?: boolean;
  compact?: boolean;
  higherSeedScore?: number;
  lowerSeedScore?: number;
  winnerTeamId?: number;
}

export function BracketMatchup({ 
  higherSeed, 
  lowerSeed, 
  isPlaceholder = false, 
  compact = false,
  higherSeedScore,
  lowerSeedScore,
  winnerTeamId
}: BracketMatchupProps) {
  if (isPlaceholder || !higherSeed || !lowerSeed) {
    return (
      <div className={`bg-[#11161C] border border-[#1F2A35] rounded-lg ${compact ? 'p-1.5' : 'p-3'}`}>
        <div className="space-y-1">
          <div className={`${compact ? 'h-6' : 'h-8'} bg-[#1F2A35]/30 rounded flex items-center justify-center`}>
            <span className="text-[#64748b] text-xs">TBD</span>
          </div>
          <div className={`${compact ? 'h-6' : 'h-8'} bg-[#1F2A35]/30 rounded flex items-center justify-center`}>
            <span className="text-[#64748b] text-xs">TBD</span>
          </div>
        </div>
      </div>
    );
  }

  const hasScores = higherSeedScore !== undefined && lowerSeedScore !== undefined;
  const higherSeedWon = winnerTeamId === higherSeed.team_id;
  const lowerSeedWon = winnerTeamId === lowerSeed.team_id;

  return (
    <div className={`bg-[#11161C] border border-[#1F2A35] rounded-lg hover:border-[#2d4a6f] transition-colors ${compact ? 'p-1.5' : 'p-3'}`}>
      <div className="space-y-1">
        {/* Higher Seed */}
        <div className={`flex items-center gap-1.5 rounded px-1.5 py-1 hover:bg-[#1e3a5f] transition-colors cursor-pointer ${ 
          higherSeedWon ? 'bg-[#1e3a5f]' : 'bg-[#1a2332]'
        }`}>
          <div className={`${compact ? 'w-4 h-4' : 'w-5 h-5'} rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center flex-shrink-0`}>
            <span className={`text-[#94a3b8] ${compact ? 'text-[10px]' : 'text-xs'}`}>{higherSeed.seed}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className={`truncate font-medium ${ 
              compact ? 'text-xs' : 'text-sm'
            } ${ 
              higherSeedWon ? 'text-white' : lowerSeedWon ? 'text-[#94a3b8]' : 'text-white'
            }`}>
              {getTeamAbbr(higherSeed)}
            </p>
          </div>
          {hasScores ? (
            <div className={`${compact ? 'text-xs' : 'text-sm'} flex-shrink-0 min-w-[1.5rem] text-right font-semibold ${ 
              higherSeedWon ? 'text-[#d4af37]' : 'text-[#94a3b8]'
            }`}>
              {higherSeedScore}
            </div>
          ) : (
            <div className={`text-[#64748b] ${compact ? 'text-[10px]' : 'text-xs'} flex-shrink-0`}>
              {higherSeed.wins}-{higherSeed.losses}
            </div>
          )}
        </div>
        
        {/* Lower Seed */}
        <div className={`flex items-center gap-1.5 rounded px-1.5 py-1 hover:bg-[#1e3a5f] transition-colors cursor-pointer ${ 
          lowerSeedWon ? 'bg-[#1e3a5f]' : 'bg-[#1a2332]'
        }`}>
          <div className={`${compact ? 'w-4 h-4' : 'w-5 h-5'} rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center flex-shrink-0`}>
            <span className={`text-[#94a3b8] ${compact ? 'text-[10px]' : 'text-xs'}`}>{lowerSeed.seed}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className={`truncate font-medium ${ 
              compact ? 'text-xs' : 'text-sm'
            } ${ 
              lowerSeedWon ? 'text-white' : higherSeedWon ? 'text-[#94a3b8]' : 'text-white'
            }`}>
              {getTeamAbbr(lowerSeed)}
            </p>
          </div>
          {hasScores ? (
            <div className={`${compact ? 'text-xs' : 'text-sm'} flex-shrink-0 min-w-[1.5rem] text-right font-semibold ${ 
              lowerSeedWon ? 'text-[#d4af37]' : 'text-[#94a3b8]'
            }`}>
              {lowerSeedScore}
            </div>
          ) : (
            <div className={`text-[#64748b] ${compact ? 'text-[10px]' : 'text-xs'} flex-shrink-0`}>
              {lowerSeed.wins}-{lowerSeed.losses}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}