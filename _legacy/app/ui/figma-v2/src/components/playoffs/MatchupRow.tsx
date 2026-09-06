/**
 * Playoff/MatchupRow Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked - do not modify without version bump
 */

import { TeamSeed } from '../../lib/mockPlayoffsApi';

interface MatchupRowProps {
  higherSeed: TeamSeed;
  lowerSeed: TeamSeed;
  isPlaceholder?: boolean;
}

export function MatchupRow({ higherSeed, lowerSeed, isPlaceholder = false }: MatchupRowProps) {
  if (isPlaceholder) {
    return (
      <div className="min-h-[48px] flex items-center justify-center border border-[#1F2A35] rounded-lg bg-[#0B0F14]/50 px-3 py-2">
        <p className="text-[#64748b] text-xs">Advances after games</p>
      </div>
    );
  }

  return (
    <div className="min-h-[48px] border border-[#1F2A35] rounded-lg bg-[#11161C] hover:bg-[#1a2332] transition-colors px-3 py-2 group">
      <div className="flex items-center justify-between gap-3">
        {/* Higher Seed Team */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center">
            <span className="text-[#94a3b8] text-xs">{higherSeed.seed}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm truncate group-hover:underline">
              {higherSeed.team_name || `Team ${higherSeed.team_id}`}
            </p>
            <p className="text-[#64748b] text-xs">
              {higherSeed.wins}-{higherSeed.losses}{higherSeed.ties > 0 ? `-${higherSeed.ties}` : ''}
            </p>
          </div>
        </div>

        {/* VS */}
        <div className="flex-shrink-0 text-[#64748b] text-xs uppercase tracking-wider px-2">
          vs
        </div>

        {/* Lower Seed Team */}
        <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
          <div className="flex-1 min-w-0 text-right">
            <p className="text-white text-sm truncate group-hover:underline">
              {lowerSeed.team_name || `Team ${lowerSeed.team_id}`}
            </p>
            <p className="text-[#64748b] text-xs">
              {lowerSeed.wins}-{lowerSeed.losses}{lowerSeed.ties > 0 ? `-${lowerSeed.ties}` : ''}
            </p>
          </div>
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center">
            <span className="text-[#94a3b8] text-xs">{lowerSeed.seed}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
