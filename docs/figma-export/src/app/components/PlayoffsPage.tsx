/**
 * Playoffs Page - Main Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked and ready for backend integration
 * API Endpoint: GET /api/v1/playoffs
 * 
 * Data Hooks:
 * - data-layer="afc-wc|afc-div|afc-conf" - AFC round containers
 * - data-layer="nfc-wc|nfc-div|nfc-conf" - NFC round containers
 * - data-layer="sb-card" - Super Bowl game card
 * - data-layer="hunt-strip" - In The Hunt section
 * - data-test="playoff-content" - Main content wrapper
 */

import { useState, useEffect } from 'react';
import { getPlayoffBracket, PlayoffBracketDTO } from '../lib/mockPlayoffsApi';
import { ConferenceBracket } from './playoffs/ConferenceBracket';
import { SuperBowlView } from './playoffs/SuperBowlView';
import { FullPlayoffTree } from './playoffs/FullPlayoffTree';
import { HuntCard } from './playoffs/HuntCard';
import { DivisionStandings } from './DivisionStandings';
import { PlayoffBadge } from './playoffs/PlayoffBadge';
import { Skeleton } from './ui/skeleton';
import { AlertCircle } from 'lucide-react';
import { Button } from './ui/button';

type ViewMode = 'full' | 'afc' | 'nfc' | 'superbowl';

export function PlayoffsPage() {
  const [data, setData] = useState<PlayoffBracketDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('full');

  const loadPlayoffData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getPlayoffBracket();
      setData(result);
    } catch (err) {
      setError('Failed to load playoff data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlayoffData();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-[120px] bg-[#11161C]" />
        <Skeleton className="h-[600px] bg-[#11161C]" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-12 text-center">
        <AlertCircle className="h-12 w-12 text-[#e74c3c] mx-auto mb-4" />
        <h3 className="text-white mb-2">Data Unavailable</h3>
        <p className="text-[#94a3b8] mb-4">{error || 'Unable to load playoff data'}</p>
        <Button onClick={loadPlayoffData} className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]">
          Retry
        </Button>
      </div>
    );
  }

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

  // Split In The Hunt by conference
  const afcHunt = data.in_the_hunt.filter(t => t.side === 'AFC').slice(0, 5);
  const nfcHunt = data.in_the_hunt.filter(t => t.side === 'NFC').slice(0, 5);

  return (
    <div className="space-y-6">
      {/* View Mode Toggle */}
      <div className="flex items-center justify-center gap-3">
        <Button
          onClick={() => setViewMode('full')}
          variant={viewMode === 'full' ? 'default' : 'outline'}
          className={
            viewMode === 'full'
              ? 'bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]'
              : 'bg-transparent border-[#2d4a6f] text-[#d4af37] hover:bg-[#d4af37]/10'
          }
        >
          Full Bracket
        </Button>
        
        <Button
          onClick={() => setViewMode('afc')}
          variant={viewMode === 'afc' ? 'default' : 'outline'}
          className={
            viewMode === 'afc'
              ? 'bg-[#dc2626] hover:bg-[#dc2626]/90 text-white border-[#dc2626]'
              : 'bg-transparent border-[#2d4a6f] text-[#ef4444] hover:bg-[#dc2626]/10'
          }
        >
          <PlayoffBadge variant="AFC" size="sm" className="mr-2">
            AFC
          </PlayoffBadge>
          AFC Bracket
        </Button>
        
        <Button
          onClick={() => setViewMode('superbowl')}
          variant={viewMode === 'superbowl' ? 'default' : 'outline'}
          className={
            viewMode === 'superbowl'
              ? 'bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]'
              : 'bg-transparent border-[#2d4a6f] text-[#d4af37] hover:bg-[#d4af37]/10'
          }
        >
          Super Bowl
        </Button>
        
        <Button
          onClick={() => setViewMode('nfc')}
          variant={viewMode === 'nfc' ? 'default' : 'outline'}
          className={
            viewMode === 'nfc'
              ? 'bg-[#1e40af] hover:bg-[#1e40af]/90 text-white border-[#1e40af]'
              : 'bg-transparent border-[#2d4a6f] text-[#60a5fa] hover:bg-[#1e40af]/10'
          }
        >
          <PlayoffBadge variant="NFC" size="sm" className="mr-2">
            NFC
          </PlayoffBadge>
          NFC Bracket
        </Button>
      </div>

      {/* Main Content Area */}
      <div data-test="playoff-content">
        {viewMode === 'full' && (
          <FullPlayoffTree data={data} />
        )}
        
        {viewMode === 'afc' && (
          <ConferenceBracket
            conference="AFC"
            wildCardMatchups={afcWildCard}
            divisionalMatchups={afcDivisional}
            conferenceMatchup={afcConference[0] || null}
            championshipSeed={afcChampion}
          />
        )}
        
        {viewMode === 'nfc' && (
          <ConferenceBracket
            conference="NFC"
            wildCardMatchups={nfcWildCard}
            divisionalMatchups={nfcDivisional}
            conferenceMatchup={nfcConference[0] || null}
            championshipSeed={nfcChampion}
          />
        )}
        
        {viewMode === 'superbowl' && (
          <SuperBowlView data={data} />
        )}
      </div>

      {/* In The Hunt Section - Only show on AFC/NFC views */}
      {(viewMode === 'afc' || viewMode === 'nfc') && (
        <>
          <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6" data-test="hunt-strip" data-layer="hunt-strip">
            <div className="mb-4">
              <h3 className="text-white mb-1">In The Hunt</h3>
              <p className="text-[#94a3b8] text-sm">Teams on the playoff bubble</p>
            </div>

            {/* AFC Section */}
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-3">
                <PlayoffBadge variant="AFC" size="sm">AFC</PlayoffBadge>
                <span className="text-[#94a3b8] text-sm">American Conference</span>
              </div>
              <div className="flex gap-4 flex-wrap">
                {afcHunt.map((team) => (
                  <HuntCard key={team.team_id} team={team} />
                ))}
              </div>
            </div>

            {/* NFC Section */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <PlayoffBadge variant="NFC" size="sm">NFC</PlayoffBadge>
                <span className="text-[#94a3b8] text-sm">National Conference</span>
              </div>
              <div className="flex gap-4 flex-wrap">
                {nfcHunt.map((team) => (
                  <HuntCard key={team.team_id} team={team} />
                ))}
              </div>
            </div>
          </div>

          {/* Division Standings - Bottom of AFC/NFC views */}
          <div>
            <DivisionStandings />
          </div>
        </>
      )}
    </div>
  );
}