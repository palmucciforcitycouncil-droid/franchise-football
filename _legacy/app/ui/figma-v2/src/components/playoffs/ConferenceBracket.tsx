/**
 * ConferenceBracket Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked - full bracket view with SVG connectors
 */

import { Matchup } from '../../lib/mockPlayoffsApi';
import { BracketMatchup } from './BracketMatchup';
import { PlayoffBadge } from './PlayoffBadge';

interface ConferenceBracketProps {
  conference: 'AFC' | 'NFC';
  wildCardMatchups: Matchup[];
  divisionalMatchups: Matchup[];
  conferenceMatchup: Matchup | null;
  championshipSeed: { seed: number; team_id: number; team_name?: string; wins: number; losses: number; ties: number; power_rank: number } | null;
}

export function ConferenceBracket({ 
  conference, 
  wildCardMatchups, 
  divisionalMatchups, 
  conferenceMatchup,
  championshipSeed 
}: ConferenceBracketProps) {
  const isAFC = conference === 'AFC';
  
  return (
    <div className="relative max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="mb-6 text-center">
        <PlayoffBadge variant={conference} size="md" className="mb-2">
          {conference}
        </PlayoffBadge>
        <h2 className="text-white text-xl">
          {isAFC ? 'American Football Conference' : 'National Football Conference'}
        </h2>
      </div>

      {/* Bracket Grid */}
      <div className="relative">
        {/* SVG Connector Lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
          <defs>
            <marker id={`arrowhead-${conference}`} markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="#2d4a6f" />
            </marker>
          </defs>
          
          {/* Wild Card to Divisional Lines */}
          {wildCardMatchups.length > 0 && (
            <>
              {/* Top WC to Top Div */}
              <path
                d={isAFC 
                  ? "M 230 70 L 260 70 L 260 120 L 290 120"
                  : "M 70 70 L 40 70 L 40 120 L 10 120"
                }
                stroke="#2d4a6f"
                strokeWidth="2"
                fill="none"
                opacity="0.5"
              />
              
              {/* Middle WC to Top Div */}
              <path
                d={isAFC
                  ? "M 230 200 L 260 200 L 260 155 L 290 155"
                  : "M 70 200 L 40 200 L 40 155 L 10 155"
                }
                stroke="#2d4a6f"
                strokeWidth="2"
                fill="none"
                opacity="0.5"
              />
              
              {/* Bottom WC to Bottom Div */}
              <path
                d={isAFC
                  ? "M 230 330 L 260 330 L 260 320 L 290 320"
                  : "M 70 330 L 40 330 L 40 320 L 10 320"
                }
                stroke="#2d4a6f"
                strokeWidth="2"
                fill="none"
                opacity="0.5"
              />
            </>
          )}
          
          {/* Divisional to Conference Lines */}
          {divisionalMatchups.length > 0 && (
            <>
              <path
                d={isAFC
                  ? "M 520 138 L 560 138 L 560 230 L 590 230"
                  : "M -220 138 L -260 138 L -260 230 L -290 230"
                }
                stroke="#2d4a6f"
                strokeWidth="2"
                fill="none"
                opacity="0.5"
              />
              <path
                d={isAFC
                  ? "M 520 338 L 560 338 L 560 265 L 590 265"
                  : "M -220 338 L -260 338 L -260 265 L -290 265"
                }
                stroke="#2d4a6f"
                strokeWidth="2"
                fill="none"
                opacity="0.5"
              />
            </>
          )}
        </svg>

        {/* Bracket Layout */}
        <div className={`grid gap-4 ${isAFC ? 'grid-cols-4' : 'grid-cols-4 direction-rtl'}`}>
          {/* Round 1: Wild Card (3 games) */}
          <div className="space-y-4" style={{ zIndex: 1 }} data-layer={isAFC ? 'afc-wc' : 'nfc-wc'}>
            <div>
              <div className="text-center mb-2">
                <PlayoffBadge variant="neutral" size="sm">WILD CARD</PlayoffBadge>
              </div>
              <div className="space-y-3">
                {wildCardMatchups.length > 0 ? (
                  wildCardMatchups.map((matchup, idx) => (
                    <BracketMatchup
                      key={idx}
                      higherSeed={matchup.higher_seed_team}
                      lowerSeed={matchup.lower_seed_team}
                      higherSeedScore={matchup.higher_seed_score}
                      lowerSeedScore={matchup.lower_seed_score}
                      winnerTeamId={matchup.winner_team_id}
                    />
                  ))
                ) : (
                  <>
                    <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder />
                    <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder />
                    <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder />
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Round 2: Divisional (2 games) */}
          <div className="space-y-4" style={{ zIndex: 1, paddingTop: '3rem' }} data-layer={isAFC ? 'afc-div' : 'nfc-div'}>
            <div>
              <div className="text-center mb-2">
                <PlayoffBadge variant="neutral" size="sm">DIVISIONAL</PlayoffBadge>
              </div>
              <div className="space-y-20">
                {divisionalMatchups.length > 0 ? (
                  divisionalMatchups.map((matchup, idx) => (
                    <BracketMatchup
                      key={idx}
                      higherSeed={matchup.higher_seed_team}
                      lowerSeed={matchup.lower_seed_team}
                      higherSeedScore={matchup.higher_seed_score}
                      lowerSeedScore={matchup.lower_seed_score}
                      winnerTeamId={matchup.winner_team_id}
                    />
                  ))
                ) : (
                  <>
                    <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder />
                    <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder />
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Round 3: Conference Championship (1 game) */}
          <div className="space-y-4" style={{ zIndex: 1, paddingTop: '8.5rem' }} data-layer={isAFC ? 'afc-conf' : 'nfc-conf'}>
            <div>
              <div className="text-center mb-2">
                <PlayoffBadge variant="neutral" size="sm">CONFERENCE</PlayoffBadge>
              </div>
              {conferenceMatchup ? (
                <BracketMatchup
                  higherSeed={conferenceMatchup.higher_seed_team}
                  lowerSeed={conferenceMatchup.lower_seed_team}
                  higherSeedScore={conferenceMatchup.higher_seed_score}
                  lowerSeedScore={conferenceMatchup.lower_seed_score}
                  winnerTeamId={conferenceMatchup.winner_team_id}
                />
              ) : (
                <BracketMatchup higherSeed={null} lowerSeed={null} isPlaceholder />
              )}
            </div>
          </div>

          {/* Conference Champion */}
          <div className="space-y-4" style={{ zIndex: 1, paddingTop: '10rem' }}>
            <div>
              <div className="text-center mb-2">
                <PlayoffBadge variant={conference} size="sm">CHAMPION</PlayoffBadge>
              </div>
              {championshipSeed ? (
                <div className="bg-[#11161C] border-2 border-[#d4af37] rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-[#d4af37]/20 border border-[#d4af37] flex items-center justify-center flex-shrink-0">
                      <span className="text-[#d4af37] font-semibold text-sm">{championshipSeed.seed}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-semibold text-sm truncate">
                        {championshipSeed.team_name || `Team ${championshipSeed.team_id}`}
                      </p>
                      <p className="text-[#94a3b8] text-xs">
                        {championshipSeed.wins}-{championshipSeed.losses}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-[#11161C] border border-[#1F2A35] rounded-lg p-3">
                  <div className="text-center text-[#64748b] text-sm">
                    TBD
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
