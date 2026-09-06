/**
 * Playoff/RoundCard Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked - do not modify without version bump
 */

import { PlayoffBadge } from './PlayoffBadge';
import { MatchupRow } from './MatchupRow';
import { Matchup } from '../../lib/mockPlayoffsApi';

interface RoundCardProps {
  conference: 'AFC' | 'NFC';
  roundName: 'WILD CARD' | 'DIVISIONAL' | 'CONFERENCE';
  matchups: Matchup[];
}

export function RoundCard({ conference, roundName, matchups }: RoundCardProps) {
  const hasMatchups = matchups.length > 0;

  return (
    <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-4 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <PlayoffBadge variant={conference} size="md">
          {conference}
        </PlayoffBadge>
        <PlayoffBadge variant="neutral" size="sm">
          {roundName}
        </PlayoffBadge>
      </div>

      {/* Matchups */}
      <div className="space-y-3">
        {hasMatchups ? (
          matchups.map((matchup, idx) => (
            <MatchupRow
              key={idx}
              higherSeed={matchup.higher_seed_team}
              lowerSeed={matchup.lower_seed_team}
            />
          ))
        ) : (
          <>
            <MatchupRow
              higherSeed={{ seed: 0, team_id: 0, team_name: '', wins: 0, losses: 0, ties: 0, power_rank: 0 }}
              lowerSeed={{ seed: 0, team_id: 0, team_name: '', wins: 0, losses: 0, ties: 0, power_rank: 0 }}
              isPlaceholder
            />
            <MatchupRow
              higherSeed={{ seed: 0, team_id: 0, team_name: '', wins: 0, losses: 0, ties: 0, power_rank: 0 }}
              lowerSeed={{ seed: 0, team_id: 0, team_name: '', wins: 0, losses: 0, ties: 0, power_rank: 0 }}
              isPlaceholder
            />
          </>
        )}
      </div>
    </div>
  );
}
