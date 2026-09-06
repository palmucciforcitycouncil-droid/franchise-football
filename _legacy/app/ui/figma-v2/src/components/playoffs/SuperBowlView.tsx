/**
 * SuperBowlView Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked - Super Bowl tab view
 */

import { PlayoffBracketDTO } from '../../lib/mockPlayoffsApi';
import { BracketMatchup } from './BracketMatchup';
import { PlayoffBadge } from './PlayoffBadge';
import { ScoutingPanel } from '../ScoutingPanel';
import { BoxScore } from '../BoxScore';
import { PlayByPlay } from '../PlayByPlay';

interface SuperBowlViewProps {
  data: PlayoffBracketDTO;
}

export function SuperBowlView({ data }: SuperBowlViewProps) {
  const sbRound = data.rounds.find(r => r.round_name === 'SB');
  const superBowlMatchup = sbRound?.matchups[0] || null;

  const wcRound = data.rounds.find(r => r.round_name === 'WC');
  const afcWC = wcRound?.matchups.filter(m => m.side === 'AFC').slice(0, 2) || [];
  const nfcWC = wcRound?.matchups.filter(m => m.side === 'NFC').slice(0, 2) || [];

  return (
    <div className="space-y-6">
      {/* Compact Bracket Overview */}
      <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6">
        <div className="relative flex items-center justify-center gap-8">
          {/* AFC Side - Compact */}
          <div className="flex-1 max-w-md">
            <div className="text-center mb-4">
              <PlayoffBadge variant="AFC" size="sm">AFC</PlayoffBadge>
            </div>
            <div className="space-y-3">
              {afcWC.map((matchup, idx) => (
                <BracketMatchup
                  key={idx}
                  higherSeed={matchup.higher_seed_team}
                  lowerSeed={matchup.lower_seed_team}
                  higherSeedScore={matchup.higher_seed_score}
                  lowerSeedScore={matchup.lower_seed_score}
                  winnerTeamId={matchup.winner_team_id}
                  compact
                />
              ))}
              <div className="text-center">
                <div className="inline-block bg-[#1a2332] rounded px-3 py-1 border border-[#2d4a6f]">
                  <span className="text-[#94a3b8] text-xs">→ Conference Champ</span>
                </div>
              </div>
            </div>
          </div>

          {/* Super Bowl - Center */}
          <div className="flex-shrink-0 w-80">
            <div className="bg-gradient-to-br from-[#1e3a5f] to-[#11161C] rounded-xl border-2 border-[#d4af37] p-6 shadow-2xl" data-layer="sb-card">
              <div className="text-center mb-4">
                <div className="text-[#d4af37] text-2xl mb-1">SUPER BOWL</div>
                <div className="text-[#94a3b8] text-sm">Championship Game</div>
              </div>
              
              {superBowlMatchup ? (
                <div className="space-y-3">
                  <div className={`flex items-center gap-3 rounded-lg p-3 border ${
                    superBowlMatchup.winner_team_id === superBowlMatchup.higher_seed_team.team_id 
                      ? 'bg-[#1e3a5f] border-[#d4af37]' 
                      : 'bg-[#11161C]/80 border-[#2d4a6f]'
                  }`}>
                    <PlayoffBadge variant="AFC" size="sm">AFC</PlayoffBadge>
                    <div className="w-6 h-6 rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center">
                      <span className="text-[#94a3b8] text-xs">{superBowlMatchup.higher_seed_team.seed}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm truncate font-semibold ${
                        superBowlMatchup.winner_team_id === superBowlMatchup.higher_seed_team.team_id 
                          ? 'text-white' 
                          : 'text-[#94a3b8]'
                      }`}>
                        {superBowlMatchup.higher_seed_team.team_name}
                      </p>
                      <p className="text-[#64748b] text-xs">
                        {superBowlMatchup.higher_seed_team.wins}-{superBowlMatchup.higher_seed_team.losses}
                      </p>
                    </div>
                    {superBowlMatchup.higher_seed_score !== undefined && (
                      <div className={`text-xl font-semibold min-w-[2.5rem] text-right ${
                        superBowlMatchup.winner_team_id === superBowlMatchup.higher_seed_team.team_id 
                          ? 'text-[#d4af37]' 
                          : 'text-[#94a3b8]'
                      }`}>
                        {superBowlMatchup.higher_seed_score}
                      </div>
                    )}
                  </div>
                  
                  <div className="text-center">
                    <span className="text-[#d4af37] text-sm uppercase tracking-wider">final</span>
                  </div>
                  
                  <div className={`flex items-center gap-3 rounded-lg p-3 border ${
                    superBowlMatchup.winner_team_id === superBowlMatchup.lower_seed_team.team_id 
                      ? 'bg-[#1e3a5f] border-[#d4af37]' 
                      : 'bg-[#11161C]/80 border-[#2d4a6f]'
                  }`}>
                    <PlayoffBadge variant="NFC" size="sm">NFC</PlayoffBadge>
                    <div className="w-6 h-6 rounded-full bg-[#1F2A35] border border-[#2d4a6f] flex items-center justify-center">
                      <span className="text-[#94a3b8] text-xs">{superBowlMatchup.lower_seed_team.seed}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm truncate font-semibold ${
                        superBowlMatchup.winner_team_id === superBowlMatchup.lower_seed_team.team_id 
                          ? 'text-white' 
                          : 'text-[#94a3b8]'
                      }`}>
                        {superBowlMatchup.lower_seed_team.team_name}
                      </p>
                      <p className="text-[#64748b] text-xs">
                        {superBowlMatchup.lower_seed_team.wins}-{superBowlMatchup.lower_seed_team.losses}
                      </p>
                    </div>
                    {superBowlMatchup.lower_seed_score !== undefined && (
                      <div className={`text-xl font-semibold min-w-[2.5rem] text-right ${
                        superBowlMatchup.winner_team_id === superBowlMatchup.lower_seed_team.team_id 
                          ? 'text-[#d4af37]' 
                          : 'text-[#94a3b8]'
                      }`}>
                        {superBowlMatchup.lower_seed_score}
                      </div>
                    )}
                  </div>

                  {/* MVP Section */}
                  <div className="pt-3 mt-3 border-t border-[#1F2A35]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[#d4af37] text-xs uppercase tracking-wider">MVP</span>
                    </div>
                    <div className="bg-[#11161C]/80 rounded-lg p-3 border border-[#2d4a6f]">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-white text-sm font-semibold">Tom Brady</p>
                          <p className="text-[#94a3b8] text-xs">QB • Kansas City Chiefs</p>
                        </div>
                        <div className="text-right">
                          <p className="text-white text-sm">341 YDS • 3 TD</p>
                          <p className="text-[#64748b] text-xs">28/35, 80.0%</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-[#64748b] py-8">
                  <p className="text-sm">Championship matchup TBD</p>
                </div>
              )}
            </div>
          </div>

          {/* NFC Side - Compact */}
          <div className="flex-1 max-w-md">
            <div className="text-center mb-4">
              <PlayoffBadge variant="NFC" size="sm">NFC</PlayoffBadge>
            </div>
            <div className="space-y-3">
              {nfcWC.map((matchup, idx) => (
                <BracketMatchup
                  key={idx}
                  higherSeed={matchup.higher_seed_team}
                  lowerSeed={matchup.lower_seed_team}
                  higherSeedScore={matchup.higher_seed_score}
                  lowerSeedScore={matchup.lower_seed_score}
                  winnerTeamId={matchup.winner_team_id}
                  compact
                />
              ))}
              <div className="text-center">
                <div className="inline-block bg-[#1a2332] rounded px-3 py-1 border border-[#2d4a6f]">
                  <span className="text-[#94a3b8] text-xs">→ Conference Champ</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Scouting Panels */}
      {superBowlMatchup && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <PlayoffBadge variant="AFC" size="sm">AFC</PlayoffBadge>
              <span className="text-white">{superBowlMatchup.higher_seed_team.team_name}</span>
            </div>
            <ScoutingPanel />
          </div>
          <div>
            <div className="mb-2 flex items-center gap-2">
              <PlayoffBadge variant="NFC" size="sm">NFC</PlayoffBadge>
              <span className="text-white">{superBowlMatchup.lower_seed_team.team_name}</span>
            </div>
            <ScoutingPanel />
          </div>
        </div>
      )}

      {/* Box Score */}
      <div>
        <BoxScore hideNavigation />
      </div>

      {/* Play by Play */}
      <div>
        <PlayByPlay />
      </div>
    </div>
  );
}
