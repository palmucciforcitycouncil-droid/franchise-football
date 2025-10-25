import { useState, useEffect } from 'react';
import { Search, Pause, Play } from 'lucide-react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { RoundTabs } from './draft-v2/RoundTabs';
import { StatusChip } from './draft-v2/StatusChip';
import { PickRow } from './draft-v2/PickRow';
import { BoardItem } from './draft-v2/BoardItem';
import { DraftProspectsTable } from './draft/DraftProspectsTable';
import { CompareDrawer } from './draft/CompareDrawer';
import { RosterTable } from './RosterTable';
import { TradeBlockBox } from './roster/TradeBlockBox';
import { TradeBox } from './gm/TradeBox';
import { ClickablePlayerName } from './ui/ClickablePlayerName';
import { toast } from 'sonner@2.0.3';

// Mock data types
interface Prospect {
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
  ctr: string; // college
  yrs: number;
  dep: string; // status
  hlth: string;
  trd: boolean;
  watchlist?: boolean;
}

interface DraftPick {
  pick: number;
  round: number;
  team: {
    abbr: string;
    name: string;
    color?: string;
  };
  prospect?: {
    name: string;
    ovr: number;
    pos: string;
    college: string;
  };
  status: 'pending' | 'made';
}

// Mock prospects data
const generateMockProspects = (): Prospect[] => {
  const positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S'];
  const colleges = ['Alabama', 'Ohio State', 'Georgia', 'Michigan', 'LSU', 'Clemson', 'Texas', 'USC'];
  const firstNames = ['Marcus', 'Jaylen', 'Xavier', 'Darius', 'Tyler', 'Brandon', 'Jordan', 'Cameron'];
  const lastNames = ['Williams', 'Johnson', 'Smith', 'Brown', 'Jones', 'Davis', 'Miller', 'Wilson'];

  return Array.from({ length: 250 }, (_, i) => {
    const ovr = Math.floor(Math.random() * 35) + 65; // 65-99
    const age = 21 + Math.floor(Math.random() * 3); // 21-23
    return {
      name: `${firstNames[Math.floor(Math.random() * firstNames.length)]} ${lastNames[Math.floor(Math.random() * lastNames.length)]}`,
      num: 0,
      pos: positions[Math.floor(Math.random() * positions.length)],
      age,
      ovr,
      spd: Math.floor(Math.random() * 35) + 65,
      str: Math.floor(Math.random() * 35) + 65,
      agi: Math.floor(Math.random() * 35) + 65,
      tpw: Math.floor(Math.random() * 40) + 60,
      tac: Math.floor(Math.random() * 40) + 60,
      cth: Math.floor(Math.random() * 40) + 60,
      tck: Math.floor(Math.random() * 40) + 60,
      awr: Math.floor(Math.random() * 35) + 65,
      pot: Math.min(99, ovr + Math.floor(Math.random() * 15)),
      sta: Math.floor(Math.random() * 40) + 60,
      inj: Math.floor(Math.random() * 40) + 60,
      mor: Math.floor(Math.random() * 40) + 60,
      ctr: colleges[Math.floor(Math.random() * colleges.length)],
      yrs: 0,
      dep: 'Available',
      hlth: 'Healthy',
      trd: false,
      watchlist: false,
    };
  }).sort((a, b) => b.ovr - a.ovr);
};

// Mock teams
const teams = [
  { abbr: 'NE', name: 'New England', color: '#002244' },
  { abbr: 'KC', name: 'Kansas City', color: '#E31837' },
  { abbr: 'SF', name: 'San Francisco', color: '#AA0000' },
  { abbr: 'DAL', name: 'Dallas', color: '#041E42' },
  { abbr: 'GB', name: 'Green Bay', color: '#203731' },
  { abbr: 'PIT', name: 'Pittsburgh', color: '#FFB612' },
  { abbr: 'LAR', name: 'LA Rams', color: '#003594' },
  { abbr: 'BUF', name: 'Buffalo', color: '#00338D' },
];

// Generate draft picks for all 7 rounds
const generateDraftPicks = (): DraftPick[] => {
  const picks: DraftPick[] = [];
  const picksPerRound = 32;
  
  for (let round = 1; round <= 7; round++) {
    for (let pick = 1; pick <= picksPerRound; pick++) {
      const overallPick = (round - 1) * picksPerRound + pick;
      const teamIndex = (pick - 1) % teams.length;
      
      picks.push({
        pick: overallPick,
        round,
        team: teams[teamIndex],
        status: overallPick < 5 ? 'made' : 'pending', // First 4 picks are made
      });
    }
  }
  
  return picks;
};

export function DraftPageV2() {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeRound, setActiveRound] = useState(1);
  const [draftState, setDraftState] = useState<'simulating' | 'on-clock'>('on-clock');
  const [currentPick, setCurrentPick] = useState(5);
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [draftPicks, setDraftPicks] = useState<DraftPick[]>([]);
  const [draftBoard, setDraftBoard] = useState<Prospect[]>([]);
  const [selectedProspectIndices, setSelectedProspectIndices] = useState<Set<string>>(new Set());
  const [compareProspects, setCompareProspects] = useState<Prospect[]>([]);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [positionFilter, setPositionFilter] = useState<string>('ALL');
  const [isPaused, setIsPaused] = useState(false);
  const [draftYear, setDraftYear] = useState(2025);
  const [rosterPlayers, setRosterPlayers] = useState<Prospect[]>([]);

  useEffect(() => {
    setProspects(generateMockProspects());
    setDraftPicks(generateDraftPicks());
    
    // Initialize with a few prospects on the board
    const mockProspects = generateMockProspects();
    setDraftBoard(mockProspects.slice(0, 5));
    
    // Generate mock roster
    setRosterPlayers(generateMockProspects().slice(0, 53).map(p => ({
      ...p,
      dep: 'Starter',
      yrs: Math.floor(Math.random() * 10),
    })));
  }, [draftYear]);

  // Define position groups
  const offensivePositions = ['QB', 'RB', 'WR', 'TE', 'OL'];
  const defensivePositions = ['DL', 'LB', 'CB', 'S'];
  const allPositions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K', 'P'];

  // Filter prospects
  const filteredProspects = prospects.filter(p => {
    // Position filter
    let positionMatch = true;
    if (positionFilter === 'OFFENSE') {
      positionMatch = offensivePositions.includes(p.pos);
    } else if (positionFilter === 'DEFENSE') {
      positionMatch = defensivePositions.includes(p.pos);
    } else if (positionFilter !== 'ALL') {
      positionMatch = p.pos === positionFilter;
    }

    // Search filter
    const searchMatch = 
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.pos.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.ctr.toLowerCase().includes(searchQuery.toLowerCase());
    
    return positionMatch && searchMatch;
  });

  // Calculate position counts
  const prospectCounts = {
    ALL: prospects.length,
    OFFENSE: prospects.filter(p => offensivePositions.includes(p.pos)).length,
    DEFENSE: prospects.filter(p => defensivePositions.includes(p.pos)).length,
    QB: prospects.filter(p => p.pos === 'QB').length,
    RB: prospects.filter(p => p.pos === 'RB').length,
    WR: prospects.filter(p => p.pos === 'WR').length,
    TE: prospects.filter(p => p.pos === 'TE').length,
    OL: prospects.filter(p => p.pos === 'OL').length,
    DL: prospects.filter(p => p.pos === 'DL').length,
    LB: prospects.filter(p => p.pos === 'LB').length,
    CB: prospects.filter(p => p.pos === 'CB').length,
    S: prospects.filter(p => p.pos === 'S').length,
    K: prospects.filter(p => p.pos === 'K').length,
    P: prospects.filter(p => p.pos === 'P').length,
  };

  // Get top 8 prospects for the strip
  const topProspects = filteredProspects.slice(0, 8);

  // Get picks for active round
  const roundPicks = draftPicks.filter(p => p.round === activeRound);

  // Check if user is on the clock
  const userOnClock = draftState === 'on-clock';

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
    const selected = indices.map(i => filteredProspects[i]).filter(Boolean);
    setCompareProspects(selected);
    setIsCompareOpen(true);
  };

  const handleClearSelection = () => {
    setSelectedProspectIndices(new Set());
  };

  const handleToggleWatchlist = (index: number) => {
    setProspects(prev => 
      prev.map((p, i) => 
        i === index ? { ...p, watchlist: !p.watchlist } : p
      )
    );
    const prospect = filteredProspects[index];
    if (prospect) {
      toast.success(
        prospect.watchlist 
          ? `${prospect.name} removed from watchlist` 
          : `${prospect.name} added to watchlist`
      );
    }
  };

  const handleAddToDraftBoard = (index: number) => {
    const prospect = filteredProspects[index];
    if (!prospect) return;

    if (draftBoard.some(p => p.name === prospect.name)) {
      toast.info(`${prospect.name} is already on your draft board`);
      return;
    }
    
    setDraftBoard(prev => [...prev, prospect]);
    toast.success(`${prospect.name} added to draft board`);
  };

  const handleRemoveFromBoard = (index: number) => {
    const prospect = draftBoard[index];
    if (!prospect) return;
    
    setDraftBoard(prev => prev.filter((_, i) => i !== index));
    toast.success(`${prospect.name} removed from draft board`);
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const newBoard = [...draftBoard];
    [newBoard[index - 1], newBoard[index]] = [newBoard[index], newBoard[index - 1]];
    setDraftBoard(newBoard);
  };

  const handleMoveDown = (index: number) => {
    if (index === draftBoard.length - 1) return;
    const newBoard = [...draftBoard];
    [newBoard[index], newBoard[index + 1]] = [newBoard[index + 1], newBoard[index]];
    setDraftBoard(newBoard);
  };

  const handleSimToNextUserPick = () => {
    setDraftState('simulating');
    toast.info('Simulating to your next pick...');
    
    setTimeout(() => {
      setDraftState('on-clock');
      setCurrentPick(prev => prev + 5);
      toast.success('You\'re on the clock!');
    }, 2000);
  };

  const handleTogglePause = () => {
    setIsPaused(!isPaused);
    toast.info(isPaused ? 'Draft resumed' : 'Draft paused');
  };

  // Get team's picks (NE picks)
  const teamPicks = draftPicks.filter(pick => pick.team.abbr === 'NE' && pick.status === 'pending');
  const currentYearTeamPicks = teamPicks.slice(0, 7); // Show picks for all 7 rounds

  // Team needs - mock data
  const teamNeeds = ['WR', 'CB', 'OL', 'DL', 'LB'];

  return (
    <div className="max-w-[1920px] mx-auto">
      {/* Page Title */}
      <div className="mb-6">
        <h1 className="text-white text-3xl">Draft</h1>
        <p className="text-[#94a3b8] text-sm mt-1">{draftYear} NFL Draft · Round {activeRound}</p>
      </div>

      {/* Top Row: Team Picks and Team Needs */}
      <div className="grid grid-cols-12 gap-4 mb-4">
        {/* Team Picks Display - Spans most of the row */}
        <div className="col-span-9">
          <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-4">
            <h3 className="text-white mb-3">Team Picks ({currentYearTeamPicks.length})</h3>
            <div className="flex flex-wrap gap-3">
              {currentYearTeamPicks.map((pick) => (
                <div
                  key={pick.pick}
                  className="bg-[#0a1929] border border-[#d4af37] rounded px-4 py-2 min-w-[100px]"
                >
                  <div className="text-[#d4af37] text-xs">Round {pick.round}</div>
                  <div className="text-white">Pick #{pick.pick}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Team Needs - Small box */}
        <div className="col-span-3">
          <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-4 h-full">
            <h3 className="text-white mb-3">Team Needs</h3>
            <div className="flex flex-wrap gap-2">
              {teamNeeds.map((position, index) => (
                <div
                  key={index}
                  className="bg-[#0a1929] border border-[#2d4a6f] rounded px-3 py-1.5 text-[#94a3b8] text-sm"
                >
                  {position}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* First Row: Draft Results (Left) + Prospects Table (Right) */}
      <div className="grid grid-cols-12 gap-4 mb-4">
        {/* Draft Results - Left Side (3/12 - half width) */}
        <div className="col-span-3">
          <div className="bg-[#11161C] rounded-lg border border-[#1F2A35]">
            {/* Header */}
            <div className="p-3 border-b border-[#1F2A35]">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-white text-sm">Draft Results</h3>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleTogglePause}
                    className={`border-[#2d4a6f] text-xs h-7 ${
                      isPaused 
                        ? 'bg-green-500/20 text-green-300 border-green-500/50' 
                        : 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50'
                    }`}
                  >
                    {isPaused ? (
                      <>
                        <Play className="w-3 h-3 mr-1" />
                        Resume
                      </>
                    ) : (
                      <>
                        <Pause className="w-3 h-3 mr-1" />
                        Pause
                      </>
                    )}
                  </Button>
                  <StatusChip 
                    variant={draftState} 
                    pickNumber={currentPick}
                  />
                </div>
              </div>
              
              {/* Round Tabs */}
              <RoundTabs 
                activeRound={activeRound} 
                onRoundChange={setActiveRound} 
              />
              
              {/* Sim Button */}
              <div className="mt-2">
                {draftState === 'simulating' ? (
                  <Button
                    disabled
                    size="sm"
                    className="w-full bg-[#2d4a6f] text-[#94a3b8] cursor-not-allowed text-xs"
                  >
                    Simulating...
                  </Button>
                ) : (
                  <Button
                    disabled={isPaused}
                    size="sm"
                    className="w-full bg-[#2d4a6f] text-[#94a3b8] cursor-not-allowed text-xs"
                  >
                    Sim to Next Pick
                  </Button>
                )}
              </div>
            </div>

            {/* Results Table - Shows all 32 picks */}
            <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 300px)' }}>
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-[#11161C] border-b border-[#1F2A35]">
                  <tr>
                    <th className="py-2 px-2 text-left text-[#94a3b8] text-xs">#</th>
                    <th className="py-2 px-2 text-left text-[#94a3b8] text-xs">Team</th>
                    <th className="py-2 px-2 text-left text-[#94a3b8] text-xs">Player</th>
                  </tr>
                </thead>
                <tbody>
                  {roundPicks.map((pick) => (
                    <tr 
                      key={pick.pick}
                      className={`border-b border-[#1F2A35]/50 ${
                        pick.status === 'made' ? 'opacity-100' : 'opacity-50'
                      }`}
                    >
                      <td className="py-2 px-2 text-white">{pick.pick}</td>
                      <td className="py-2 px-2">
                        <span 
                          className="text-white text-xs px-1.5 py-0.5 rounded"
                          style={{ backgroundColor: pick.team.color }}
                        >
                          {pick.team.abbr}
                        </span>
                      </td>
                      <td className="py-2 px-2">
                        {pick.prospect ? (
                          <div>
                            <div className="text-white text-xs truncate">
                              <ClickablePlayerName playerName={pick.prospect.name} />
                            </div>
                            <div className="text-[#94a3b8] text-xs">
                              {pick.prospect.pos} · {pick.prospect.ovr}
                            </div>
                          </div>
                        ) : (
                          <span className="text-[#94a3b8] text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Prospects Table - Right Side (9/12) */}
        <div className="col-span-9">
          <DraftProspectsTable
            players={filteredProspects}
            selectedIds={selectedProspectIndices}
            onToggleSelection={toggleProspectByIndex}
            onToggleWatchlist={handleToggleWatchlist}
            onAddToDraftBoard={handleAddToDraftBoard}
            loading={loading}
            headerContent={
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-4">
                      <h3 className="text-white">Prospects ({filteredProspects.length})</h3>
                      
                      {/* Draft Year Selector */}
                      <div className="flex items-center gap-2">
                        <span className="text-[#94a3b8] text-xs">Draft Year:</span>
                        <div className="flex gap-1">
                          {[2025, 2026, 2027, 2028].map((year) => (
                            <button
                              key={year}
                              onClick={() => setDraftYear(year)}
                              className={`px-3 py-1 rounded text-xs transition-all ${
                                draftYear === year
                                  ? 'bg-[#d4af37] text-[#0a1929]'
                                  : 'bg-[#2d4a6f]/30 text-[#94a3b8] border border-[#2d4a6f] hover:bg-[#2d4a6f]/50'
                              }`}
                            >
                              {year}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                    <p className="text-[#94a3b8] text-sm mt-1">
                      {selectedProspectIndices.size > 0 
                        ? `${selectedProspectIndices.size} selected${selectedProspectIndices.size >= 5 ? ' (max)' : ''}`
                        : 'Select up to 5 prospects to compare'
                      }
                    </p>
                  </div>
                  {selectedProspectIndices.size > 0 && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleClearSelection}
                        className="border-[#2d4a6f] text-[#94a3b8] hover:bg-[#1a2332]"
                      >
                        Clear
                      </Button>
                      {selectedProspectIndices.size >= 2 && (
                        <Button
                          size="sm"
                          onClick={handleCompare}
                          className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
                        >
                          Compare ({selectedProspectIndices.size})
                        </Button>
                      )}
                    </div>
                  )}
                </div>

                {/* Position Filter Tiles */}
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setPositionFilter('ALL')}
                    className={`px-3 py-1.5 rounded text-xs transition-all ${
                      positionFilter === 'ALL'
                        ? 'bg-[#1e3a5f] text-white border-2 border-[#d4af37]'
                        : 'bg-[#2d4a6f]/30 text-[#94a3b8] border border-[#2d4a6f] hover:bg-[#2d4a6f]/50'
                    }`}
                  >
                    ALL {prospectCounts.ALL}
                  </button>
                  <button
                    onClick={() => setPositionFilter('OFFENSE')}
                    className={`px-3 py-1.5 rounded text-xs transition-all ${
                      positionFilter === 'OFFENSE'
                        ? 'bg-[#1e3a5f] text-white border-2 border-[#d4af37]'
                        : 'bg-[#2d4a6f]/30 text-[#94a3b8] border border-[#2d4a6f] hover:bg-[#2d4a6f]/50'
                    }`}
                  >
                    OFFENSE {prospectCounts.OFFENSE}
                  </button>
                  <button
                    onClick={() => setPositionFilter('DEFENSE')}
                    className={`px-3 py-1.5 rounded text-xs transition-all ${
                      positionFilter === 'DEFENSE'
                        ? 'bg-[#1e3a5f] text-white border-2 border-[#d4af37]'
                        : 'bg-[#2d4a6f]/30 text-[#94a3b8] border border-[#2d4a6f] hover:bg-[#2d4a6f]/50'
                    }`}
                  >
                    DEFENSE {prospectCounts.DEFENSE}
                  </button>
                  {allPositions.map(pos => (
                    <button
                      key={pos}
                      onClick={() => setPositionFilter(pos)}
                      className={`px-3 py-1.5 rounded text-xs transition-all ${
                        positionFilter === pos
                          ? 'bg-[#1e3a5f] text-white border-2 border-[#d4af37]'
                          : 'bg-[#2d4a6f]/30 text-[#94a3b8] border border-[#2d4a6f] hover:bg-[#2d4a6f]/50'
                      }`}
                    >
                      {pos} {prospectCounts[pos as keyof typeof prospectCounts]}
                    </button>
                  ))}
                </div>

                {/* Search Bar */}
                <div className="relative mt-3">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <Input
                    type="text"
                    placeholder="Search name, POS, college"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 bg-[#0B0F14] border-[#1F2A35] text-white placeholder:text-[#94a3b8]"
                  />
                </div>
              </div>
            }
          />
        </div>
      </div>

      {/* Second Row: Draft Board + Trade Block + Trade Box + Top Prospects */}
      <div className="grid grid-cols-12 gap-4">
        {/* Draft Board (4/12) */}
        <div className="col-span-4">
          <div className="bg-[#11161C] rounded-lg border border-[#1F2A35]" style={{ minHeight: '260px' }}>
            <div className="p-4 border-b border-[#1F2A35]">
              <h3 className="text-white">Draft Board ({draftBoard.length})</h3>
            </div>
            <div className="p-4 space-y-2 overflow-auto" style={{ maxHeight: '400px' }}>
              {draftBoard.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-[#94a3b8]">
                    <p>Add players to your board from Prospects.</p>
                  </div>
                </div>
              ) : (
                draftBoard.map((prospect, index) => (
                  <BoardItem
                    key={`${prospect.name}-${index}`}
                    prospect={{
                      id: `${prospect.name}-${index}`,
                      name: prospect.name,
                      pos: prospect.pos,
                      ovr: prospect.ovr,
                      pot: prospect.pot,
                      college: prospect.ctr,
                      grade: '',
                      speed: prospect.spd,
                      strength: prospect.str,
                      agility: prospect.agi,
                      awareness: prospect.awr,
                    }}
                    index={index}
                    isOnClock={userOnClock}
                    onDraft={() => {}}
                    onRemove={() => handleRemoveFromBoard(index)}
                    onMoveUp={() => handleMoveUp(index)}
                    onMoveDown={() => handleMoveDown(index)}
                    isFirst={index === 0}
                    isLast={index === draftBoard.length - 1}
                  />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Trade Block (3/12) */}
        <div className="col-span-3">
          <TradeBlockBox />
        </div>

        {/* Trade Box (3/12) */}
        <div className="col-span-3">
          <TradeBox />
        </div>

        {/* Top Prospects Strip (2/12) */}
        <div className="col-span-2">
          <div className="bg-[#11161C] rounded-lg border border-[#1F2A35] p-4">
            <h3 className="text-white text-sm mb-3 uppercase tracking-wide">Top Prospects</h3>
            <div className="space-y-3">
              {topProspects.slice(0, 6).map((prospect, idx) => (
                <div
                  key={`${prospect.name}-${idx}`}
                  className="bg-[#0B0F14] border border-[#1F2A35] rounded-lg p-2 hover:bg-[#1a2332] transition-colors"
                >
                  <div className="mb-2">
                    <div className="text-white text-xs truncate">
                      <ClickablePlayerName playerName={prospect.name} />
                    </div>
                    <div className="flex items-center gap-1 mt-1">
                      <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8] text-xs px-1 py-0">
                        {prospect.pos}
                      </Badge>
                      <span className={`text-xs px-1 py-0 rounded ${
                        prospect.ovr >= 90 ? 'bg-green-500/20 text-green-300' :
                        prospect.ovr >= 80 ? 'bg-blue-500/20 text-blue-300' :
                        'bg-yellow-500/20 text-yellow-300'
                      }`}>
                        {prospect.ovr}
                      </span>
                    </div>
                    <div className="text-[#94a3b8] text-xs mt-1 truncate">{prospect.ctr}</div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation();
                      const prospectIndex = prospects.findIndex(p => p.name === prospect.name);
                      if (prospectIndex >= 0) handleAddToDraftBoard(prospectIndex);
                    }}
                    className="w-full border-[#2d4a6f] text-[#94a3b8] hover:bg-[#1a2332] h-6 text-xs"
                  >
                    +Board
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Roster Box */}
      <div className="mt-4">
        <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
          <div className="p-4">
            <RosterTable
              players={rosterPlayers}
              loading={false}
              quotas={{
                QB: { current: rosterPlayers.filter(p => p.pos === 'QB').length, min: 2 },
                RB: { current: rosterPlayers.filter(p => p.pos === 'RB').length, min: 3 },
                WR: { current: rosterPlayers.filter(p => p.pos === 'WR').length, min: 5 },
                TE: { current: rosterPlayers.filter(p => p.pos === 'TE').length, min: 2 },
                OL: { current: rosterPlayers.filter(p => p.pos === 'OL').length, min: 8 },
                DL: { current: rosterPlayers.filter(p => p.pos === 'DL').length, min: 6 },
                LB: { current: rosterPlayers.filter(p => p.pos === 'LB').length, min: 6 },
                CB: { current: rosterPlayers.filter(p => p.pos === 'CB').length, min: 5 },
                S: { current: rosterPlayers.filter(p => p.pos === 'S').length, min: 4 },
                K: { current: rosterPlayers.filter(p => p.pos === 'K').length, min: 1 },
                P: { current: rosterPlayers.filter(p => p.pos === 'P').length, min: 1 },
              }}
              onUpdatePlayer={() => {}}
              showDepthChart={false}
            />
          </div>
        </div>
      </div>

      {/* Compare Drawer */}
      <CompareDrawer
        isOpen={isCompareOpen}
        onClose={() => setIsCompareOpen(false)}
        prospects={compareProspects}
      />
    </div>
  );
}
