import { useState, useEffect, useRef } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { ArrowUpDown, ArrowUp, ArrowDown, X } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { ClickablePlayerName } from './ui/ClickablePlayerName';
import './RosterTable.css';

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

interface PositionQuota {
  current: number;
  min: number;
}

interface RosterTableProps {
  players: Player[];
  stats: PlayerStats[];
  viewMode: 'attributes' | 'stats';
  loading: boolean;
  error: boolean;
  searchQuery: string;
  positionFilter: string | null;
  onPlayerClick: (player: Player) => void;
  positionQuotas?: Record<string, PositionQuota>;
  onPositionFilterChange?: (position: string | null) => void;
}

export function RosterTable({ players, stats, viewMode, loading, error, searchQuery, positionFilter, onPlayerClick, positionQuotas, onPositionFilterChange }: RosterTableProps) {
  const [sortField, setSortField] = useState<string>('ovr');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  
  // Refs for scroll sync
  const bodyScrollRef = useRef<HTMLDivElement>(null);
  const topScrollbarRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getSortIcon = (field: string) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 opacity-50" />;
    return sortDirection === 'asc' ? 
      <ArrowUp className="h-3 w-3" /> : 
      <ArrowDown className="h-3 w-3" />;
  };

  const filteredPlayers = players.filter(player => {
    if (positionFilter && player.pos !== positionFilter) return false;
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      player.name.toLowerCase().includes(query) ||
      player.pos.toLowerCase().includes(query) ||
      player.num.toString().includes(query)
    );
  });

  const sortedPlayers = [...filteredPlayers].sort((a, b) => {
    const aVal = a[sortField as keyof Player];
    const bVal = b[sortField as keyof Player];
    
    // Handle boolean values (for Trade column)
    if (typeof aVal === 'boolean' && typeof bVal === 'boolean') {
      const aNum = aVal ? 1 : 0;
      const bNum = bVal ? 1 : 0;
      return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
    }
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    }
    
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc' 
        ? aVal.localeCompare(bVal) 
        : bVal.localeCompare(aVal);
    }
    
    return 0;
  });

  // Sync scrollbars bidirectionally
  useEffect(() => {
    const body = bodyScrollRef.current;
    const topBar = topScrollbarRef.current;
    const table = tableRef.current;
    const sizer = topBar?.querySelector('.sizer') as HTMLElement | null;

    if (!body || !topBar || !sizer || !table) return;

    // Update sizer width to match table scrollWidth
    const setSizerWidth = () => {
      sizer.style.width = table.scrollWidth + 'px';
    };

    // Loop guard for bidirectional sync
    let syncing = false;

    const handleTopBarScroll = () => {
      if (syncing) return;
      syncing = true;
      body.scrollLeft = topBar.scrollLeft;
      syncing = false;
    };

    const handleBodyScroll = () => {
      if (syncing) return;
      syncing = true;
      topBar.scrollLeft = body.scrollLeft;
      syncing = false;
    };

    // Attach listeners
    topBar.addEventListener('scroll', handleTopBarScroll);
    body.addEventListener('scroll', handleBodyScroll);

    // ResizeObserver to keep sizer accurate
    const ro = new ResizeObserver(setSizerWidth);
    ro.observe(table);

    // Also update on window resize and font load
    window.addEventListener('resize', setSizerWidth);
    if (document.fonts?.ready) {
      document.fonts.ready.then(setSizerWidth);
    }

    // Initial width set
    setSizerWidth();

    // Sticky-breaker diagnostic (dev only - can be removed after confirming sticky works)
    if (process.env.NODE_ENV === 'development') {
      let p = body.parentElement;
      while (p) {
        const cs = getComputedStyle(p);
        if (/(transform|filter|perspective)/.test(
          cs.transform + cs.filter + cs.perspective
        )) {
          console.warn('Sticky-breaker found on', p, cs.transform, cs.filter, cs.perspective);
        }
        // Only warn about overflow on ancestors ABOVE #rosterCard (not #rosterCard itself or #rosterBodyScroll)
        if (/(auto|scroll|hidden)/.test(cs.overflow + cs.overflowX + cs.overflowY) &&
          p.id !== 'rosterBodyScroll' && p.id !== 'rosterCard') {
          console.warn('Non-scrolling ancestor has overflow set (can break sticky):', p, cs.overflow, cs.overflowX, cs.overflowY);
        }
        p = p.parentElement;
      }
    }

    return () => {
      topBar.removeEventListener('scroll', handleTopBarScroll);
      body.removeEventListener('scroll', handleBodyScroll);
      ro.disconnect();
      window.removeEventListener('resize', setSizerWidth);
    };
  }, [viewMode, sortedPlayers.length]);

  const handlePositionClick = (pos: string | null) => {
    if (onPositionFilterChange) {
      onPositionFilterChange(positionFilter === pos ? null : pos);
    }
  };

  const totalRosterCount = players.length;
  const MAX_ROSTER_SIZE = 53;

  return (
    <div className="roster-card" id="rosterCard">
      {/* Title and Controls */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white">Team Roster</h3>
          {error && <span className="text-[#94a3b8] text-xs">(demo)</span>}
        </div>

        {/* Integrated Position Quota Filter */}
        {positionQuotas && onPositionFilterChange && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-white text-sm">Team Quota</h4>
              {positionFilter && (
                <button
                  onClick={() => onPositionFilterChange(null)}
                  className="px-2 py-1 rounded text-xs bg-[#2d4a6f] text-white hover:bg-[#3d5a7f] flex items-center gap-1"
                >
                  <X className="h-3 w-3" />
                  Clear Filter
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {/* ALL option */}
              <button
                onClick={() => handlePositionClick(null)}
                className={`px-2.5 py-1 rounded text-xs border transition-colors cursor-pointer ${
                  totalRosterCount >= MAX_ROSTER_SIZE 
                    ? 'bg-[#4ade80]/10 text-[#4ade80] border-[#4ade80]/30'
                    : 'bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/30'
                } ${
                  !positionFilter ? 'ring-2 ring-[#d4af37] ring-offset-2 ring-offset-[#0a1929]' : 'hover:opacity-80'
                }`}
              >
                ALL {totalRosterCount}/{MAX_ROSTER_SIZE}
              </button>

              {/* Position buttons */}
              {Object.entries(positionQuotas).map(([pos, { current, min }]) => {
                const isMeetingQuota = current >= min;
                const isActive = positionFilter === pos;
                
                let bgColor = 'bg-[#4ade80]/10 text-[#4ade80] border-[#4ade80]/30';
                if (!isMeetingQuota) {
                  bgColor = 'bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/30';
                }

                return (
                  <button
                    key={pos}
                    onClick={() => handlePositionClick(pos)}
                    className={`px-2.5 py-1 rounded text-xs border transition-colors cursor-pointer ${bgColor} ${
                      isActive ? 'ring-2 ring-[#d4af37] ring-offset-2 ring-offset-[#0a1929]' : 'hover:opacity-80'
                    }`}
                  >
                    {pos} {current}/{min}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 border-b border-[#2d4a6f]">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              Couldn't load roster. Showing demo data.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Top synced scrollbar */}
      <div className="roster-scrollbar" id="rosterTopScrollbar" ref={topScrollbarRef}>
        <div className="sizer"></div>
      </div>

      {/* Scrollable table region */}
      <div className="roster-scroll" id="rosterBodyScroll" ref={bodyScrollRef}>
        <table className="roster-table" id="rosterTable" ref={tableRef}>
          <thead id="rosterHead">
            <tr className="border-b border-[#2d4a6f]">
              <th className="stickyCol text-left py-3 px-3 text-[#94a3b8]">
                <button
                  onClick={() => handleSort('name')}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  Player {getSortIcon('name')}
                </button>
              </th>
              {viewMode === 'attributes' ? (
                <>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('ovr')}>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex items-center justify-end gap-1 whitespace-nowrap">
                            OVR {getSortIcon('ovr')}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent className="bg-[#1a2332] border-[#2d4a6f] text-white">Overall Rating</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('pot')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">POT {getSortIcon('pot')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('spd')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">SPD {getSortIcon('spd')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('str')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">STR {getSortIcon('str')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('agi')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">AGI {getSortIcon('agi')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('tpw')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">TPW {getSortIcon('tpw')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('tac')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">TAC {getSortIcon('tac')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('cth')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">CTH {getSortIcon('cth')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('tck')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">TCK {getSortIcon('tck')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('awr')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">AWR {getSortIcon('awr')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('sta')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">STA {getSortIcon('sta')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('inj')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">INJ {getSortIcon('inj')}</div>
                  </th>
                  <th className="text-right py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('mor')}>
                    <div className="flex items-center justify-end gap-1 whitespace-nowrap">MOR {getSortIcon('mor')}</div>
                  </th>
                  <th className="text-left py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('pos')}>
                    <div className="flex items-center gap-1 whitespace-nowrap">Pos {getSortIcon('pos')}</div>
                  </th>
                  <th className="text-left py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('age')}>
                    <div className="flex items-center gap-1 whitespace-nowrap">Age {getSortIcon('age')}</div>
                  </th>
                  <th className="text-left py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('ctr')}>
                    <div className="flex items-center gap-1 whitespace-nowrap">Contract {getSortIcon('ctr')}</div>
                  </th>
                  <th className="text-left py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('dep')}>
                    <div className="flex items-center gap-1 whitespace-nowrap">Depth {getSortIcon('dep')}</div>
                  </th>
                  <th className="text-left py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('hlth')}>
                    <div className="flex items-center gap-1 whitespace-nowrap">Health {getSortIcon('hlth')}</div>
                  </th>
                  <th className="text-left py-3 px-3 text-[#94a3b8] cursor-pointer hover:text-white" onClick={() => handleSort('trd')}>
                    <div className="flex items-center gap-1 whitespace-nowrap">Trade {getSortIcon('trd')}</div>
                  </th>
                </>
              ) : (
                <>
                  <th className="text-right py-3 px-3 text-[#94a3b8]">G</th>
                  <th className="text-right py-3 px-3 text-[#94a3b8]">GS</th>
                  <th className="text-right py-3 px-3 text-[#94a3b8]">Snaps</th>
                  <th className="text-left py-3 px-3 text-[#94a3b8]">Pos-specific stats...</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 10 }).map((_, i) => (
                <tr key={i} className="border-b border-[#2d4a6f]/50">
                  <td className="py-3 px-3" colSpan={viewMode === 'attributes' ? 19 : 4}>
                    <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
                  </td>
                </tr>
              ))
            ) : (
              sortedPlayers.map((player, index) => (
                <tr
                  key={index}
                  onClick={() => onPlayerClick(player)}
                  className="border-b border-[#2d4a6f]/50 hover:bg-[#2d4a6f]/30 cursor-pointer transition-colors group"
                >
                  <td className="stickyCol py-3 px-3 text-white">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-[#2d4a6f] flex items-center justify-center text-xs">
                        {player.num}
                      </div>
                      <div>
                        <div className="truncate max-w-[160px]">
                          <ClickablePlayerName playerName={player.name} />
                        </div>
                        <div className="text-xs text-[#94a3b8]">{player.pos}</div>
                      </div>
                    </div>
                  </td>
                  {viewMode === 'attributes' ? (
                    <>
                      <td className="text-right py-3 px-3">
                        <span className={`px-2 py-1 rounded ${
                          player.ovr >= 90 ? 'bg-green-500/20 text-green-300' :
                          player.ovr >= 80 ? 'bg-blue-500/20 text-blue-300' :
                          player.ovr >= 70 ? 'bg-yellow-500/20 text-yellow-300' :
                          'bg-gray-500/20 text-gray-300'
                        }`}>
                          {player.ovr}
                        </span>
                      </td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.pot}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.spd}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.str}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.agi}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.tpw}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.tac}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.cth}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.tck}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.awr}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.sta}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.inj}</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">{player.mor}</td>
                      <td className="text-left py-3 px-3 text-[#94a3b8]">{player.pos}</td>
                      <td className="text-left py-3 px-3 text-[#94a3b8]">{player.age}</td>
                      <td className="text-left py-3 px-3 text-[#94a3b8]">{player.ctr}</td>
                      <td className="text-left py-3 px-3 text-[#94a3b8]">{player.dep}</td>
                      <td className="text-left py-3 px-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          player.hlth === 'Healthy' ? 'bg-green-500/20 text-green-300' :
                          player.hlth === 'Q' ? 'bg-yellow-500/20 text-yellow-300' :
                          player.hlth === 'D' ? 'bg-red-500/20 text-red-300' :
                          'bg-gray-500/20 text-gray-300'
                        }`}>
                          {player.hlth}
                        </span>
                      </td>
                      <td className="text-left py-3 px-3">
                        {player.trd ? (
                          <span className="px-2 py-1 rounded text-xs bg-blue-500/20 text-blue-300">Available</span>
                        ) : (
                          <span className="text-[#94a3b8] text-xs">—</span>
                        )}
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">16</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">14</td>
                      <td className="text-right py-3 px-3 text-[#94a3b8]">892</td>
                      <td className="text-left py-3 px-3 text-[#94a3b8]">...</td>
                    </>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
