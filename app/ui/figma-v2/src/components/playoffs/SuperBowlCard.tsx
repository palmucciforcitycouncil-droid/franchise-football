/**
 * Playoff/SuperBowlCard Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked - do not modify without version bump
 */

import { PlayoffBadge } from './PlayoffBadge';
import { Matchup } from '../../lib/mockPlayoffsApi';

interface SuperBowlCardProps {
  matchup: Matchup | null;
}

export function SuperBowlCard({ matchup }: SuperBowlCardProps) {
  if (!matchup) {
    return (
      <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6 shadow-lg">
        <div className="text-center">
          <PlayoffBadge variant="SB" size="md" className="mb-4">
            SUPER BOWL
          </PlayoffBadge>
          <p className="text-[#64748b] text-sm">Championship matchup TBD</p>
        </div>
      </div>
    );
  }

  const { higher_seed_team, lower_seed_team } = matchup;

  return (
    <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6 shadow-lg" data-layer="sb-card">
      {/* Header */}
      <div className="text-center mb-6">
        <h3 className="text-white text-2xl mb-1">SUPER BOWL</h3>
        <p className="text-[#d4af37] text-sm">Championship Game</p>
      </div>

      {/* Matchup */}
      <div className="border border-[#1F2A35] rounded-lg bg-[#0B0F14] p-4">
        <div className="space-y-4">
          {/* AFC Team */}
          <div className="flex items-center justify-between gap-3 pb-4 border-b border-[#1F2A35]">
            <div className="flex items-center gap-3 flex-1">
              <PlayoffBadge variant="AFC" size="sm">
                AFC
              </PlayoffBadge>
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center">
                <span className="text-[#94a3b8] text-sm font-semibold">{higher_seed_team.seed}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white">
                  {higher_seed_team.team_name || `Team ${higher_seed_team.team_id}`}
                </p>
                <p className="text-[#64748b] text-sm">
                  {higher_seed_team.wins}-{higher_seed_team.losses}
                  {higher_seed_team.ties > 0 ? `-${higher_seed_team.ties}` : ''}
                </p>
              </div>
            </div>
          </div>

          {/* VS Divider */}
          <div className="text-center">
            <span className="text-[#64748b] text-sm uppercase tracking-wider">vs</span>
          </div>

          {/* NFC Team */}
          <div className="flex items-center justify-between gap-3 pt-4 border-t border-[#1F2A35]">
            <div className="flex items-center gap-3 flex-1">
              <PlayoffBadge variant="NFC" size="sm">
                NFC
              </PlayoffBadge>
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center">
                <span className="text-[#94a3b8] text-sm font-semibold">{lower_seed_team.seed}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white">
                  {lower_seed_team.team_name || `Team ${lower_seed_team.team_id}`}
                </p>
                <p className="text-[#64748b] text-sm">
                  {lower_seed_team.wins}-{lower_seed_team.losses}
                  {lower_seed_team.ties > 0 ? `-${lower_seed_team.ties}` : ''}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
