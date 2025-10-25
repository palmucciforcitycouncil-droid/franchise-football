/**
 * Playoff/HuntCard Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked - do not modify without version bump
 */

import { PlayoffBadge } from './PlayoffBadge';
import { InTheHunt } from '../../lib/mockPlayoffsApi';

interface HuntCardProps {
  team: InTheHunt;
}

export function HuntCard({ team }: HuntCardProps) {
  return (
    <div className="flex-shrink-0 w-[240px] bg-[#11161C] rounded-xl border border-[#1F2A35] p-4 hover:bg-[#1a2332] transition-colors snap-start">
      <div className="flex items-start justify-between mb-3">
        <PlayoffBadge variant={team.side} size="sm">
          {team.side}
        </PlayoffBadge>
        <div className="text-right">
          <p className="text-[#64748b] text-xs">If in:</p>
          <p className="text-[#d4af37] text-sm font-semibold">#{team.seed_if_made}</p>
        </div>
      </div>
      
      <div>
        <p className="text-white mb-1">{team.team_name}</p>
        <p className="text-[#94a3b8] text-sm mb-2">
          {team.wins}-{team.losses}{team.ties > 0 ? `-${team.ties}` : ''}
        </p>
        <div className="flex items-center gap-1 text-xs">
          <span className="text-[#64748b]">GB:</span>
          <span className="text-[#e74c3c]">{team.gb.toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
}
