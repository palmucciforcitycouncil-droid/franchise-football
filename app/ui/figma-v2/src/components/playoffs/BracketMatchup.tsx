import { TeamSeed } from '../../lib/mockPlayoffsApi';

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
      <div className={`bg-[#11161C] border border-[#1F2A35] rounded-lg ${compact ? 'p-2' : 'p-3'}`}>
        <div className="space-y-1">
          <div className="h-8 bg-[#1F2A35]/30 rounded flex items-center justify-center">
            <span className="text-[#64748b] text-xs">TBD</span>
          </div>
          <div className="h-8 bg-[#1F2A35]/30 rounded flex items-center justify-center">
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
    <div className={`bg-[#11161C] border border-[#1F2A35] rounded-lg hover:border-[#2d4a6f] transition-colors ${compact ? 'p-2' : 'p-3'}`}>
      <div className="space-y-1">
        {/* Higher Seed */}
        <div className={`flex items-center gap-2 rounded px-2 py-1.5 hover:bg-[#1e3a5f] transition-colors cursor-pointer ${
          higherSeedWon ? 'bg-[#1e3a5f]' : 'bg-[#1a2332]'
        }`}>
          <div className="w-5 h-5 rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center flex-shrink-0">
            <span className="text-[#94a3b8] text-xs">{higherSeed.seed}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className={`truncate ${compact ? 'text-xs' : 'text-sm'} ${
              higherSeedWon ? 'text-white' : lowerSeedWon ? 'text-[#94a3b8]' : 'text-white'
            }`}>
              {higherSeed.team_name || `Team ${higherSeed.team_id}`}
            </p>
          </div>
          {hasScores ? (
            <div className={`text-xs flex-shrink-0 min-w-[2rem] text-right ${
              higherSeedWon ? 'text-[#d4af37]' : 'text-[#94a3b8]'
            }`}>
              {higherSeedScore}
            </div>
          ) : (
            <div className="text-[#64748b] text-xs flex-shrink-0">
              {higherSeed.wins}-{higherSeed.losses}
            </div>
          )}
        </div>
        
        {/* Lower Seed */}
        <div className={`flex items-center gap-2 rounded px-2 py-1.5 hover:bg-[#1e3a5f] transition-colors cursor-pointer ${
          lowerSeedWon ? 'bg-[#1e3a5f]' : 'bg-[#1a2332]'
        }`}>
          <div className="w-5 h-5 rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center flex-shrink-0">
            <span className="text-[#94a3b8] text-xs">{lowerSeed.seed}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className={`truncate ${compact ? 'text-xs' : 'text-sm'} ${
              lowerSeedWon ? 'text-white' : higherSeedWon ? 'text-[#94a3b8]' : 'text-white'
            }`}>
              {lowerSeed.team_name || `Team ${lowerSeed.team_id}`}
            </p>
          </div>
          {hasScores ? (
            <div className={`text-xs flex-shrink-0 min-w-[2rem] text-right ${
              lowerSeedWon ? 'text-[#d4af37]' : 'text-[#94a3b8]'
            }`}>
              {lowerSeedScore}
            </div>
          ) : (
            <div className="text-[#64748b] text-xs flex-shrink-0">
              {lowerSeed.wins}-{lowerSeed.losses}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
