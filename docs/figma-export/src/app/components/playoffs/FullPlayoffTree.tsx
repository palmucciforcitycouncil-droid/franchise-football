/**
 * FullPlayoffTree Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked - Complete playoff tree view showing AFC, NFC, and Super Bowl
 */

import { PlayoffBracketDTO, TeamSeed } from '../../lib/mockPlayoffsApi';
import { BracketMatchup } from './BracketMatchup';
import { PlayoffBadge } from './PlayoffBadge';

interface FullPlayoffTreeProps {
  data: PlayoffBracketDTO;
}

// Team abbreviation helper
const getTeamAbbr = (team: TeamSeed): string => {
  const abbrMap: Record<number, string> = {
    101: 'KC', 102: 'BUF', 103: 'BAL', 104: 'JAX', 105: 'LAC',
    106: 'MIA', 107: 'PIT', 108: 'CIN', 109: 'CLE', 110: 'IND',
    201: 'SF', 202: 'PHI', 203: 'DAL', 204: 'DET', 205: 'TB',
    206: 'MIN', 207: 'GB', 208: 'LAR', 209: 'SEA', 210: 'NO',
  };
  
  return team.team_abbr || abbrMap[team.team_id] || team.team_name || `T${team.team_id}`;
};

export function FullPlayoffTree({ data }: FullPlayoffTreeProps) {
  // Filter matchups by conference and round
  const wcRound = data.rounds.find(r => r.round_name === 'WC');
  const divRound = data.rounds.find(r => r.round_name === 'DIV');
  const confRound = data.rounds.find(r => r.round_name === 'CONF');
  const sbRound = data.rounds.find(r => r.round_name === 'SB');

  const afcWildCard = wcRound?.matchups.filter(m => m.side === 'AFC') || [];
  const nfcWildCard = wcRound?.matchups.filter(m => m.side === 'NFC') || [];
  
  const afcDivisional = divRound?.matchups.filter(m => m.side === 'AFC') || [];
  const nfcDivisional = divRound?.matchups.filter(m => m.side === 'NFC') || [];
  
  const afcConference = confRound?.matchups.filter(m => m.side === 'AFC') || [];
  const nfcConference = confRound?.matchups.filter(m => m.side === 'NFC') || [];

  const superBowlMatchup = sbRound?.matchups[0] || null;

  // Get conference champions for bracket display
  const afcChampion = superBowlMatchup?.higher_seed_team || null;
  const nfcChampion = superBowlMatchup?.lower_seed_team || null;

  return (
    <div className="w-full">
      {/* Header */}
      <div className="text-center mb-6">
        <div className="inline-block bg-[#d4af37] text-[#0a1929] px-6 py-2 rounded-lg mb-2">
          <span className="text-xl uppercase tracking-wider">NFL Playoff Bracket</span>
        </div>
        <p className="text-[#94a3b8] text-sm">Complete Playoff Tree - {data.season_year} Season</p>
      </div>

      {/* Full Bracket Grid */}
      <div className="max-w-[1400px] mx-auto">
        <div className="grid grid-cols-9 gap-3">
          {/* AFC WILD CARD */}
          <div className="space-y-2">
            <div className="text-center mb-2">
              <PlayoffBadge variant="AFC" size="sm" className="mb-1">AFC</PlayoffBadge>
              <div className="text-[#94a3b8] text-[10px] uppercase tracking-wide">Wild Card</div>
            </div>
            <div className="space-y-2">
              {afcWildCard.length > 0 ? (
                afcWildCard.map((matchup, idx) => (
                  <BracketMatchup
                    key={idx}
                    higherSeed={matchup.higher_seed_team}
                    lowerSeed={matchup.lower_seed_team}
                    higherSeedScore={matchup.higher_seed_score}
                    lowerSeedScore={matchup.lower_seed_score}
                    winnerTeamId={matchup.winner_team_id}
                    compact
                  />
                ))
              ) : (
                <>
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                </>
              )}
            </div>
          </div>

          {/* AFC DIVISIONAL */}
          <div className="space-y-2" style={{ paddingTop: '2.5rem' }}>
            <div className="text-center mb-2">
              <div className="text-[#94a3b8] text-[10px] uppercase tracking-wide">Divisional</div>
            </div>
            <div className="space-y-[4.5rem]">
              {afcDivisional.length > 0 ? (
                afcDivisional.map((matchup, idx) => (
                  <BracketMatchup
                    key={idx}
                    higherSeed={matchup.higher_seed_team}
                    lowerSeed={matchup.lower_seed_team}
                    higherSeedScore={matchup.higher_seed_score}
                    lowerSeedScore={matchup.lower_seed_score}
                    winnerTeamId={matchup.winner_team_id}
                    compact
                  />
                ))
              ) : (
                <>
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                </>
              )}
            </div>
          </div>

          {/* AFC CONFERENCE */}
          <div className="space-y-2" style={{ paddingTop: '6.5rem' }}>
            <div className="text-center mb-2">
              <div className="text-[#94a3b8] text-[10px] uppercase tracking-wide">Conference</div>
            </div>
            {afcConference.length > 0 && afcConference[0] ? (
              <BracketMatchup
                higherSeed={afcConference[0].higher_seed_team}
                lowerSeed={afcConference[0].lower_seed_team}
                higherSeedScore={afcConference[0].higher_seed_score}
                lowerSeedScore={afcConference[0].lower_seed_score}
                winnerTeamId={afcConference[0].winner_team_id}
                compact
              />
            ) : (
              <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
            )}
          </div>

          {/* AFC CHAMPION */}
          <div className="space-y-2" style={{ paddingTop: '7.5rem' }}>
            <div className="text-center mb-2">
              <div className="text-[#dc2626] text-[10px] uppercase tracking-wide">AFC Champ</div>
            </div>
            {afcChampion ? (
              <div className="bg-[#11161C] border-2 border-[#dc2626] rounded-lg p-2">
                <div className="flex items-center gap-1.5">
                  <div className="w-5 h-5 rounded-full bg-[#dc2626]/20 border border-[#dc2626] flex items-center justify-center flex-shrink-0">
                    <span className="text-[#dc2626] font-semibold text-[10px]">{afcChampion.seed}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-semibold text-xs truncate">
                      {getTeamAbbr(afcChampion)}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-[#11161C] border border-[#1F2A35] rounded-lg p-2">
                <div className="text-center text-[#64748b] text-xs">TBD</div>
              </div>
            )}
          </div>

          {/* SUPER BOWL */}
          <div className="space-y-2" style={{ paddingTop: '5.5rem' }}>
            <div className="bg-gradient-to-br from-[#1e3a5f] to-[#11161C] rounded-xl border-2 border-[#d4af37] p-4 shadow-2xl">
              <div className="text-center mb-3">
                <div className="text-[#d4af37] text-base mb-0.5 uppercase tracking-wider">Super Bowl</div>
                <div className="text-[#94a3b8] text-[10px]">Championship</div>
              </div>
              
              {superBowlMatchup ? (
                <div className="space-y-2">
                  {/* AFC Team */}
                  <div className={`flex items-center gap-1.5 rounded-lg p-1.5 border ${ 
                    superBowlMatchup.winner_team_id === superBowlMatchup.higher_seed_team.team_id 
                      ? 'bg-[#1e3a5f] border-[#d4af37]' 
                      : 'bg-[#11161C]/80 border-[#2d4a6f]'
                  }`}>
                    <div className="w-5 h-5 rounded-full bg-[#1F2A35] border border-[#dc2626] flex items-center justify-center">
                      <span className="text-white text-[10px] font-semibold">{superBowlMatchup.higher_seed_team.seed}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs truncate font-semibold ${ 
                        superBowlMatchup.winner_team_id === superBowlMatchup.higher_seed_team.team_id 
                          ? 'text-white' 
                          : 'text-[#94a3b8]'
                      }`}>
                        {getTeamAbbr(superBowlMatchup.higher_seed_team)}
                      </p>
                    </div>
                    {superBowlMatchup.higher_seed_score !== undefined && (
                      <div className={`text-base font-bold min-w-[1.5rem] text-right ${ 
                        superBowlMatchup.winner_team_id === superBowlMatchup.higher_seed_team.team_id 
                          ? 'text-[#d4af37]' 
                          : 'text-[#94a3b8]'
                      }`}>
                        {superBowlMatchup.higher_seed_score}
                      </div>
                    )}
                  </div>

                  {/* VS */}
                  <div className="text-center">
                    <span className="text-[#d4af37] text-[10px] uppercase tracking-wider">Final</span>
                  </div>

                  {/* NFC Team */}
                  <div className={`flex items-center gap-1.5 rounded-lg p-1.5 border ${ 
                    superBowlMatchup.winner_team_id === superBowlMatchup.lower_seed_team.team_id 
                      ? 'bg-[#1e3a5f] border-[#d4af37]' 
                      : 'bg-[#11161C]/80 border-[#2d4a6f]'
                  }`}>
                    <div className="w-5 h-5 rounded-full bg-[#1F2A35] border border-[#1e40af] flex items-center justify-center">
                      <span className="text-white text-[10px] font-semibold">{superBowlMatchup.lower_seed_team.seed}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs truncate font-semibold ${ 
                        superBowlMatchup.winner_team_id === superBowlMatchup.lower_seed_team.team_id 
                          ? 'text-white' 
                          : 'text-[#94a3b8]'
                      }`}>
                        {getTeamAbbr(superBowlMatchup.lower_seed_team)}
                      </p>
                    </div>
                    {superBowlMatchup.lower_seed_score !== undefined && (
                      <div className={`text-base font-bold min-w-[1.5rem] text-right ${ 
                        superBowlMatchup.winner_team_id === superBowlMatchup.lower_seed_team.team_id 
                          ? 'text-[#d4af37]' 
                          : 'text-[#94a3b8]'
                      }`}>
                        {superBowlMatchup.lower_seed_score}
                      </div>
                    )}
                  </div>

                  {/* Champion */}
                  {superBowlMatchup.winner_team_id && (
                    <div className="mt-2 pt-2 border-t border-[#2d4a6f]">
                      <div className="bg-gradient-to-r from-[#d4af37] to-[#f4d03f] text-[#0a1929] px-2 py-1 rounded text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                          <span className="text-[10px] uppercase tracking-wide font-semibold">Champions</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-[#64748b] py-6">
                  <p className="text-xs">TBD</p>
                </div>
              )}
            </div>
          </div>

          {/* NFC CHAMPION */}
          <div className="space-y-2" style={{ paddingTop: '7.5rem' }}>
            <div className="text-center mb-2">
              <div className="text-[#1e40af] text-[10px] uppercase tracking-wide">NFC Champ</div>
            </div>
            {nfcChampion ? (
              <div className="bg-[#11161C] border-2 border-[#1e40af] rounded-lg p-2">
                <div className="flex items-center gap-1.5">
                  <div className="w-5 h-5 rounded-full bg-[#1e40af]/20 border border-[#1e40af] flex items-center justify-center flex-shrink-0">
                    <span className="text-[#1e40af] font-semibold text-[10px]">{nfcChampion.seed}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-semibold text-xs truncate">
                      {getTeamAbbr(nfcChampion)}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-[#11161C] border border-[#1F2A35] rounded-lg p-2">
                <div className="text-center text-[#64748b] text-xs">TBD</div>
              </div>
            )}
          </div>

          {/* NFC CONFERENCE */}
          <div className="space-y-2" style={{ paddingTop: '6.5rem' }}>
            <div className="text-center mb-2">
              <div className="text-[#94a3b8] text-[10px] uppercase tracking-wide">Conference</div>
            </div>
            {nfcConference.length > 0 && nfcConference[0] ? (
              <BracketMatchup
                higherSeed={nfcConference[0].higher_seed_team}
                lowerSeed={nfcConference[0].lower_seed_team}
                higherSeedScore={nfcConference[0].higher_seed_score}
                lowerSeedScore={nfcConference[0].lower_seed_score}
                winnerTeamId={nfcConference[0].winner_team_id}
                compact
              />
            ) : (
              <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
            )}
          </div>

          {/* NFC DIVISIONAL */}
          <div className="space-y-2" style={{ paddingTop: '2.5rem' }}>
            <div className="text-center mb-2">
              <div className="text-[#94a3b8] text-[10px] uppercase tracking-wide">Divisional</div>
            </div>
            <div className="space-y-[4.5rem]">
              {nfcDivisional.length > 0 ? (
                nfcDivisional.map((matchup, idx) => (
                  <BracketMatchup
                    key={idx}
                    higherSeed={matchup.higher_seed_team}
                    lowerSeed={matchup.lower_seed_team}
                    higherSeedScore={matchup.higher_seed_score}
                    lowerSeedScore={matchup.lower_seed_score}
                    winnerTeamId={matchup.winner_team_id}
                    compact
                  />
                ))
              ) : (
                <>
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                </>
              )}
            </div>
          </div>

          {/* NFC WILD CARD */}
          <div className="space-y-2">
            <div className="text-center mb-2">
              <PlayoffBadge variant="NFC" size="sm" className="mb-1">NFC</PlayoffBadge>
              <div className="text-[#94a3b8] text-[10px] uppercase tracking-wide">Wild Card</div>
            </div>
            <div className="space-y-2">
              {nfcWildCard.length > 0 ? (
                nfcWildCard.map((matchup, idx) => (
                  <BracketMatchup
                    key={idx}
                    higherSeed={matchup.higher_seed_team}
                    lowerSeed={matchup.lower_seed_team}
                    higherSeedScore={matchup.higher_seed_score}
                    lowerSeedScore={matchup.lower_seed_score}
                    winnerTeamId={matchup.winner_team_id}
                    compact
                  />
                ))
              ) : (
                <>
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                  <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder compact />
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}