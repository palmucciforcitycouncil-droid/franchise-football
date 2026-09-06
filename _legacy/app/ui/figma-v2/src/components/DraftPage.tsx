/**
 * Draft Page Component
 * Matches Roster page structure with draft prospects
 */

import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Skeleton } from './ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Users, TrendingUp, Search, Star } from 'lucide-react';
import { RosterTable } from './RosterTable';
import { DraftProspectsTable } from './draft/DraftProspectsTable';
import { CompareDrawer } from './draft/CompareDrawer';
import { DraftBoardBox } from './draft/DraftBoardBox';
import { TopFreeAgentsBox } from './roster/TopFreeAgentsBox';
import { TradeBlockBox } from './roster/TradeBlockBox';
import { TopProspectsBox } from './gm/TopProspectsBox';
import { getDraftProspects, DraftProspect, DraftFilters, toggleWatchlist, addToDraftBoard, getDraftBoardPlayers, removeFromDraftBoard } from '../lib/mockDraftApi';
import { getRoster } from '../lib/mockDepthChartApi';
import { toast } from 'sonner@2.0.3';

interface Player {
  name: string;
  num: number;
  pos: string;
  age: number;
  ovr: number;
  spd: number;
  str: number;
  agi: number;
  tpw: number;
  tac: number;
  cth: number;
  tck: number;
  awr: number;
  pot: number;
  sta: number;
  inj: number;
  mor: number;
  ctr: string;
  yrs: number;
  dep: string;
  hlth: string;
  trd: boolean;
}

interface PlayerStats {
  name: string;
  pos: string;
  G: number;
  GS: number;
  Snaps: number;
  OVR: number;
  DEP: string;
  [key: string]: any;
}

export function DraftPage() {
  const [prospects, setProspects] = useState<DraftProspect[]>([]);
  const [draftBoardProspects, setDraftBoardProspects] = useState<DraftProspect[]>([]);
  const [rosterPlayers, setRosterPlayers] = useState<Player[]>([]);
  const [selectedProspectIndices, setSelectedProspectIndices] = useState<Set<string>>(new Set());
  const [compareProspects, setCompareProspects] = useState<DraftProspect[]>([]);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [rosterLoading, setRosterLoading] = useState(true);
  const [currentYear, setCurrentYear] = useState(2025);
  const [positionFilter, setPositionFilter] = useState<string>('ALL');
  const [rosterPositionFilter, setRosterPositionFilter] = useState<string | null>(null);

  const years = [
    { value: 2025, label: '2025 (Current)', isCurrent: true },
    { value: 2024, label: '2024' },
    { value: 2023, label: '2023' },
    { value: 2022, label: '2022' },
  ];

  const positions = ['ALL', 'WATCHLIST', 'QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K', 'P'];

  // User's draft picks for current year
  const draftPicks = [
    { round: 1, pick: 15, overall: 15 },
    { round: 2, pick: 18, overall: 50 },
    { round: 3, pick: 15, overall: 79 },
    { round: 4, pick: 22, overall: 118 },
    { round: 5, pick: 15, overall: 151 },
    { round: 6, pick: 20, overall: 192 },
    { round: 7, pick: 15, overall: 223 },
  ];

  useEffect(() => {
    loadProspects();
  }, [currentYear, positionFilter]);

  useEffect(() => {
    loadRoster();
    loadDraftBoard();
  }, []);

  const loadProspects = async () => {
    setLoading(true);
    try {
      const filters: DraftFilters = {
        year: currentYear,
        position: positionFilter,
        showDrafted: true,
      };
      const data = await getDraftProspects(filters);
      setProspects(data);
    } catch (error) {
      console.error('Failed to load prospects:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadRoster = async () => {
    setRosterLoading(true);
    try {
      const data = await getRoster(1);
      // Convert PlayerData to Player format
      const convertedPlayers: Player[] = data.map(p => ({
        name: `${p.first_name} ${p.last_name}`,
        num: p.jersey_number,
        pos: p.position,
        age: p.age,
        ovr: p.ratings.ovr,
        spd: p.ratings.spd,
        str: p.ratings.str,
        agi: p.ratings.agi,
        tpw: p.ratings.thp,
        tac: p.ratings.tha,
        cth: p.ratings.cth,
        tck: p.ratings.tkl,
        awr: p.ratings.awr,
        pot: p.ratings.ovr + Math.floor(Math.random() * 10) - 5, // Estimate potential
        sta: p.ratings.sta,
        inj: p.injury_proneness || 50,
        mor: 75 + Math.floor(Math.random() * 20), // Random morale
        ctr: '3yr/$12M', // Placeholder contract
        yrs: 2, // Placeholder years
        dep: 'Starter', // Placeholder depth
        hlth: p.status === 'Active' ? 'Healthy' : p.status,
        trd: false,
      }));
      setRosterPlayers(convertedPlayers);
    } catch (error) {
      console.error('Failed to load roster:', error);
    } finally {
      setRosterLoading(false);
    }
  };

  const toggleProspectByIndex = (index: number) => {
    const indexStr = String(index);
    const newSelected = new Set(selectedProspectIndices);
    if (newSelected.has(indexStr)) {
      newSelected.delete(indexStr);
    } else {
      if (newSelected.size < 5) {
        newSelected.add(indexStr);
      }
    }
    setSelectedProspectIndices(newSelected);
  };

  const handleCompare = () => {
    const indices = Array.from(selectedProspectIndices).map(Number);
    const selected = indices.map(i => prospects[i]).filter(Boolean);
    setCompareProspects(selected);
    setIsCompareOpen(true);
  };

  const handleClearSelection = () => {
    setSelectedProspectIndices(new Set());
  };

  const handleToggleWatchlist = async (index: number) => {
    const prospect = prospects[index];
    if (!prospect) return;

    try {
      const isNowOnWatchlist = await toggleWatchlist(prospect.prospect_id);
      
      // Update local state
      setProspects(prevProspects => 
        prevProspects.map((p, i) => 
          i === index ? { ...p, watchlist: isNowOnWatchlist } : p
        )
      );

      toast.success(
        isNowOnWatchlist 
          ? `${prospect.name} added to watchlist` 
          : `${prospect.name} removed from watchlist`
      );
    } catch (error) {
      toast.error('Failed to update watchlist');
    }
  };

  const loadDraftBoard = async () => {
    try {
      const data = await getDraftBoardPlayers();
      setDraftBoardProspects(data);
    } catch (error) {
      console.error('Failed to load draft board:', error);
    }
  };

  const handleAddToDraftBoard = async (index: number) => {
    const prospect = prospects[index];
    if (!prospect) return;

    try {
      const success = await addToDraftBoard(prospect.prospect_id);
      
      if (success) {
        await loadDraftBoard(); // Reload draft board
        toast.success(`${prospect.name} added to draft board`);
      } else {
        toast.info(`${prospect.name} is already on your draft board`);
      }
    } catch (error) {
      toast.error('Failed to add to draft board');
    }
  };

  const handleRemoveFromDraftBoard = async (index: number) => {
    const prospect = draftBoardProspects[index];
    if (!prospect) return;

    try {
      await removeFromDraftBoard(prospect.prospect_id);
      await loadDraftBoard(); // Reload draft board
      toast.success(`${prospect.name} removed from draft board`);
    } catch (error) {
      toast.error('Failed to remove from draft board');
    }
  };

  // Calculate position quotas from prospects (available undrafted)
  const prospectQuotas = {
    QB: prospects.filter(p => p.position === 'QB' && !p.drafted).length,
    RB: prospects.filter(p => p.position === 'RB' && !p.drafted).length,
    WR: prospects.filter(p => p.position === 'WR' && !p.drafted).length,
    TE: prospects.filter(p => p.position === 'TE' && !p.drafted).length,
    OL: prospects.filter(p => p.position === 'OL' && !p.drafted).length,
    DL: prospects.filter(p => p.position === 'DL' && !p.drafted).length,
    LB: prospects.filter(p => p.position === 'LB' && !p.drafted).length,
    CB: prospects.filter(p => p.position === 'CB' && !p.drafted).length,
    S: prospects.filter(p => p.position === 'S' && !p.drafted).length,
    K: prospects.filter(p => p.position === 'K' && !p.drafted).length,
    P: prospects.filter(p => p.position === 'P' && !p.drafted).length,
  };

  // Calculate roster quotas from current team
  const rosterQuotas = {
    QB: { current: rosterPlayers.filter(p => p.pos === 'QB').length, min: 2 },
    RB: { current: rosterPlayers.filter(p => p.pos === 'RB').length, min: 3 },
    WR: { current: rosterPlayers.filter(p => p.pos === 'WR').length, min: 5 },
    TE: { current: rosterPlayers.filter(p => p.pos === 'TE').length, min: 2 },
    OL: { current: rosterPlayers.filter(p => ['C', 'G', 'T', 'OL'].includes(p.pos)).length, min: 8 },
    DL: { current: rosterPlayers.filter(p => ['DE', 'DT', 'DL'].includes(p.pos)).length, min: 6 },
    LB: { current: rosterPlayers.filter(p => p.pos === 'LB').length, min: 6 },
    CB: { current: rosterPlayers.filter(p => p.pos === 'CB').length, min: 4 },
    S: { current: rosterPlayers.filter(p => p.pos === 'S').length, min: 4 },
    K: { current: rosterPlayers.filter(p => p.pos === 'K').length, min: 1 },
    P: { current: rosterPlayers.filter(p => p.pos === 'P').length, min: 1 },
  };

  // Convert prospects to Player format for RosterTable
  const prospectsAsPlayers: Player[] = prospects.map(p => ({
    name: p.name,
    num: 0,
    pos: p.position,
    age: 21 + Math.floor(Math.random() * 3), // 21-23
    ovr: p.overall,
    spd: p.speed,
    str: p.strength,
    agi: p.agility,
    tpw: Math.floor(Math.random() * 40) + 60,
    tac: Math.floor(Math.random() * 40) + 60,
    cth: Math.floor(Math.random() * 40) + 60,
    tck: Math.floor(Math.random() * 40) + 60,
    awr: p.awareness,
    pot: p.potential,
    sta: Math.floor(Math.random() * 40) + 60,
    inj: Math.floor(Math.random() * 40) + 60,
    mor: Math.floor(Math.random() * 40) + 60,
    ctr: p.college,
    yrs: 0,
    dep: p.drafted ? `Rd ${p.draft_round}` : 'Available',
    hlth: 'Healthy',
    trd: false,
    watchlist: p.watchlist,
  }));

  // Convert draft board prospects to Player format
  const draftBoardAsPlayers: Player[] = draftBoardProspects.map(p => ({
    name: p.name,
    num: 0,
    pos: p.position,
    age: 21 + Math.floor(Math.random() * 3), // 21-23
    ovr: p.overall,
    spd: p.speed,
    str: p.strength,
    agi: p.agility,
    tpw: Math.floor(Math.random() * 40) + 60,
    tac: Math.floor(Math.random() * 40) + 60,
    cth: Math.floor(Math.random() * 40) + 60,
    tck: Math.floor(Math.random() * 40) + 60,
    awr: p.awareness,
    pot: p.potential,
    sta: Math.floor(Math.random() * 40) + 60,
    inj: Math.floor(Math.random() * 40) + 60,
    mor: Math.floor(Math.random() * 40) + 60,
    ctr: p.college,
    yrs: 0,
    dep: p.drafted ? `Rd ${p.draft_round}` : 'Available',
    hlth: 'Healthy',
    trd: false,
    watchlist: p.watchlist,
  }));

  // Empty stats for prospects (college stats coming soon)
  const prospectsAsStats = prospects.map(p => ({
    name: p.name,
    pos: p.position,
    G: 0,
    GS: 0,
    Snaps: 0,
    OVR: p.overall,
    DEP: p.drafted ? `Rd ${p.draft_round}` : 'Available',
  }));

  return (
    <div className="max-w-[1920px] mx-auto">
      {/* Draft Picks Section */}
      <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-white">Your 2025 Draft Picks</h3>
            <p className="text-[#94a3b8] text-sm">7 total picks</p>
          </div>
        </div>
        <div className="grid grid-cols-7 gap-3">
          {draftPicks.map((pick) => (
            <div
              key={pick.overall}
              className="bg-[#0B0F14] border border-[#1F2A35] rounded-lg p-4 text-center hover:bg-[#1a2332] transition-colors"
            >
              <div className="text-[#d4af37] mb-1">Round {pick.round}</div>
              <div className="text-white text-xl mb-1">#{pick.pick}</div>
              <div className="text-[#94a3b8] text-xs">Overall: {pick.overall}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Year Selector */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <label className="text-[#94a3b8] text-sm">Draft Class:</label>
          <select
            value={currentYear}
            onChange={(e) => setCurrentYear(Number(e.target.value))}
            className="bg-[#1F2A35] border border-[#2d4a6f] rounded-lg px-4 py-2 text-white"
          >
            {years.map((year) => (
              <option key={year.value} value={year.value}>
                {year.label}
              </option>
            ))}
          </select>
          <div className="text-[#94a3b8] text-sm">
            {prospects.length} prospects ({prospects.filter(p => !p.drafted).length} available)
          </div>
        </div>
      </div>

      {/* Available Prospects by Position */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-2 items-center">
          <div className="text-[#94a3b8] text-sm mr-1">Available Prospects:</div>
          {Object.entries(prospectQuotas).map(([pos, count]) => {
            const isActive = positionFilter === pos;
            
            return (
              <button
                key={pos}
                onClick={() => setPositionFilter(isActive ? 'ALL' : pos)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-[#1e3a5f] text-white border-2 border-[#d4af37]'
                    : 'bg-[#2d4a6f]/30 text-[#94a3b8] border border-[#2d4a6f] hover:bg-[#2d4a6f]/50'
                }`}
              >
                {pos}: {count}
              </button>
            );
          })}
          {positionFilter !== 'ALL' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPositionFilter('ALL')}
              className="text-[#94a3b8] hover:text-white"
            >
              Clear Filter
            </Button>
          )}
        </div>
      </div>

      {/* Draft Prospects Table */}
      <div className="mb-6">
        <DraftProspectsTable
        players={prospectsAsPlayers}
        selectedIds={selectedProspectIndices}
        onToggleSelection={toggleProspectByIndex}
        onToggleWatchlist={handleToggleWatchlist}
        onAddToDraftBoard={handleAddToDraftBoard}
        loading={loading}
        headerContent={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <h3 className="text-white">Draft Prospects ({prospectsAsPlayers.length})</h3>
                <p className="text-[#94a3b8] text-sm">
                  {positionFilter === 'WATCHLIST' ? 'Watchlist' : positionFilter === 'ALL' ? 'All positions' : positionFilter} · {currentYear} Draft Class
                </p>
              </div>
              <Select value={positionFilter} onValueChange={setPositionFilter}>
                <SelectTrigger className="w-[180px] bg-[#0a1929] border-[#2d4a6f] text-white">
                  <SelectValue placeholder="Filter by position" />
                </SelectTrigger>
                <SelectContent className="bg-[#1a2332] border-[#2d4a6f]">
                  <SelectItem value="ALL" className="text-white hover:bg-[#2d4a6f]">
                    All Positions
                  </SelectItem>
                  <SelectItem value="WATCHLIST" className="text-[#d4af37] hover:bg-[#2d4a6f]">
                    <div className="flex items-center gap-2">
                      <Star className="w-4 h-4" />
                      Watchlist
                    </div>
                  </SelectItem>
                  <SelectItem value="QB" className="text-white hover:bg-[#2d4a6f]">Quarterback</SelectItem>
                  <SelectItem value="RB" className="text-white hover:bg-[#2d4a6f]">Running Back</SelectItem>
                  <SelectItem value="WR" className="text-white hover:bg-[#2d4a6f]">Wide Receiver</SelectItem>
                  <SelectItem value="TE" className="text-white hover:bg-[#2d4a6f]">Tight End</SelectItem>
                  <SelectItem value="OL" className="text-white hover:bg-[#2d4a6f]">Offensive Line</SelectItem>
                  <SelectItem value="DL" className="text-white hover:bg-[#2d4a6f]">Defensive Line</SelectItem>
                  <SelectItem value="LB" className="text-white hover:bg-[#2d4a6f]">Linebacker</SelectItem>
                  <SelectItem value="CB" className="text-white hover:bg-[#2d4a6f]">Cornerback</SelectItem>
                  <SelectItem value="S" className="text-white hover:bg-[#2d4a6f]">Safety</SelectItem>
                  <SelectItem value="K" className="text-white hover:bg-[#2d4a6f]">Kicker</SelectItem>
                  <SelectItem value="P" className="text-white hover:bg-[#2d4a6f]">Punter</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-3">
              {selectedProspectIndices.size > 0 && (
                <Button
                  variant="outline"
                  onClick={handleClearSelection}
                  className="bg-transparent border-[#2d4a6f] text-[#94a3b8] hover:bg-[#1a2332]"
                >
                  Clear ({selectedProspectIndices.size})
                </Button>
              )}
              <Button
                onClick={handleCompare}
                disabled={selectedProspectIndices.size < 2}
                className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Compare {selectedProspectIndices.size >= 2 ? `(${selectedProspectIndices.size})` : ''}
              </Button>
            </div>
          </div>
        }
      />
      </div>

      {/* Four Quick Access Boxes */}
      <div className="grid grid-cols-4 gap-6 mb-6">
        {/* Draft Board */}
        <DraftBoardBox 
          draftBoardPlayers={draftBoardAsPlayers}
          onRemoveFromBoard={handleRemoveFromDraftBoard}
        />

        {/* Top Free Agents */}
        <TopFreeAgentsBox />

        {/* Trading Block */}
        <TradeBlockBox />

        {/* Top Prospects */}
        <TopProspectsBox />
      </div>

      {/* Current Roster Section */}
      {rosterLoading ? (
        <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-6 space-y-3">
          {[...Array(10)].map((_, i) => (
            <Skeleton key={i} className="h-12 bg-[#1F2A35]" />
          ))}
        </div>
      ) : (
        <RosterTable
          players={rosterPlayers}
          stats={[]}
          viewMode="attributes"
          loading={false}
          error={false}
          searchQuery=""
          positionFilter={rosterPositionFilter}
          onPlayerClick={() => {}}
          positionQuotas={rosterQuotas}
          onPositionFilterChange={setRosterPositionFilter}
        />
      )}

      {/* Compare Drawer */}
      <CompareDrawer
        prospects={compareProspects}
        isOpen={isCompareOpen}
        onClose={() => {
          setIsCompareOpen(false);
          setSelectedProspectIndices(new Set());
        }}
      />
    </div>
  );
}
