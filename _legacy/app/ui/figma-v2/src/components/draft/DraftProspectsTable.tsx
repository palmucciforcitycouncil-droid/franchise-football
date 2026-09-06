/**
 * Draft Prospects Table with Checkboxes
 * Integrated checkbox column within table structure
 */

import { useState, useEffect, useRef } from 'react';
import { Skeleton } from '../ui/skeleton';
import { ArrowUpDown, ArrowUp, ArrowDown, Check, Star, Clipboard } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';
import '../DraftProspectsTable.css';

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
  watchlist?: boolean;
}

interface DraftProspectsTableProps {
  players: Player[];
  selectedIds: Set<string>;
  onToggleSelection: (index: number) => void;
  onToggleWatchlist?: (index: number) => void;
  onAddToDraftBoard?: (index: number) => void;
  loading: boolean;
  headerContent?: React.ReactNode;
}

export function DraftProspectsTable({
  players,
  selectedIds,
  onToggleSelection,
  onToggleWatchlist,
  onAddToDraftBoard,
  loading,
  headerContent,
}: DraftProspectsTableProps) {
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

  const sortedPlayers = [...players].sort((a, b) => {
    let aVal = a[sortField as keyof Player];
    let bVal = b[sortField as keyof Player];
    
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc' 
        ? aVal.localeCompare(bVal) 
        : bVal.localeCompare(aVal);
    }
    
    return sortDirection === 'asc' ? Number(aVal) - Number(bVal) : Number(bVal) - Number(aVal);
  });

  // Sync scrollbars
  useEffect(() => {
    const body = bodyScrollRef.current;
    const topBar = topScrollbarRef.current;
    const table = tableRef.current;
    const sizer = topBar?.querySelector('.sizer') as HTMLElement | null;

    if (!body || !topBar || !sizer || !table) return;

    const setSizerWidth = () => {
      sizer.style.width = table.scrollWidth + 'px';
    };

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

    topBar.addEventListener('scroll', handleTopBarScroll);
    body.addEventListener('scroll', handleBodyScroll);

    const ro = new ResizeObserver(setSizerWidth);
    ro.observe(table);

    window.addEventListener('resize', setSizerWidth);
    if (document.fonts?.ready) {
      document.fonts.ready.then(setSizerWidth);
    }

    setSizerWidth();

    return () => {
      topBar.removeEventListener('scroll', handleTopBarScroll);
      body.removeEventListener('scroll', handleBodyScroll);
      ro.disconnect();
      window.removeEventListener('resize', setSizerWidth);
    };
  }, [players]);

  return (
    <div className="draft-prospects-card" id="draftProspectsCard">
      {/* Header Content */}
      {headerContent && (
        <div className="p-4 border-b border-[#2d4a6f]">
          {headerContent}
        </div>
      )}

      {/* Top synced scrollbar */}
      <div className="draft-prospects-scrollbar" id="draftProspectsTopScrollbar" ref={topScrollbarRef}>
        <div className="sizer"></div>
      </div>

      {/* Scrollable table region */}
      <div className="draft-prospects-scroll" id="draftProspectsBodyScroll" ref={bodyScrollRef}>
        <table className="draft-prospects-table" id="draftProspectsTable" ref={tableRef}>
          <thead id="draftProspectsHead">
            <tr className="border-b border-[#2d4a6f]">
              {/* Checkbox column */}
              <th className="stickyCheckbox text-left py-3 px-2 text-[#94a3b8]">
                <div className="flex items-center justify-center">
                  <div className="w-5 h-5"></div>
                </div>
              </th>
              {/* Player name column */}
              <th className="stickyName text-left py-3 px-3 text-[#94a3b8]">
                <button
                  onClick={() => handleSort('name')}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  Player {getSortIcon('name')}
                </button>
              </th>
              {/* Watchlist column */}
              <th className="text-center py-3 px-2 text-[#94a3b8] w-12">
                <Star className="w-4 h-4 mx-auto" />
              </th>
              {/* Draft Board column */}
              <th className="text-center py-3 px-2 text-[#94a3b8] w-12">
                <Clipboard className="w-4 h-4 mx-auto" />
              </th>
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
              <th className="text-left py-3 px-3 text-[#94a3b8]">Pos</th>
              <th className="text-left py-3 px-3 text-[#94a3b8]">Age</th>
              <th className="text-left py-3 px-3 text-[#94a3b8]">College</th>
              <th className="text-left py-3 px-3 text-[#94a3b8]">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 10 }).map((_, i) => (
                <tr key={i} className="border-b border-[#2d4a6f]/50">
                  <td className="py-3 px-3" colSpan={19}>
                    <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
                  </td>
                </tr>
              ))
            ) : (
              sortedPlayers.map((player, index) => {
                const isSelected = selectedIds.has(String(index));
                
                return (
                  <tr
                    key={index}
                    className={`border-b border-[#2d4a6f]/50 hover:bg-[#2d4a6f]/30 transition-colors group ${
                      isSelected ? 'bg-[#1e3a5f]/40' : ''
                    }`}
                  >
                    {/* Checkbox column */}
                    <td className="stickyCheckbox py-3 px-2">
                      <div 
                        className="flex items-center justify-center cursor-pointer"
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleSelection(index);
                        }}
                      >
                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                          isSelected
                            ? 'bg-[#d4af37] border-[#d4af37]'
                            : 'border-[#2d4a6f] hover:border-[#94a3b8]'
                        }`}>
                          {isSelected && (
                            <Check className="w-3 h-3 text-[#0a1929]" />
                          )}
                        </div>
                      </div>
                    </td>
                    {/* Player name column */}
                    <td className="stickyName py-3 px-3 text-white">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-[#2d4a6f] flex items-center justify-center text-xs">
                          {player.num || '—'}
                        </div>
                        <div>
                          <ClickablePlayerName player={player}>
                            <div className="truncate max-w-[160px]">{player.name}</div>
                          </ClickablePlayerName>
                          <div className="text-xs text-[#94a3b8]">{player.pos}</div>
                        </div>
                      </div>
                    </td>
                    {/* Watchlist column */}
                    <td className="text-center py-3 px-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleWatchlist?.(index);
                        }}
                        className="hover:scale-110 transition-transform"
                      >
                        <Star 
                          className={`w-4 h-4 ${
                            player.watchlist 
                              ? 'fill-[#d4af37] text-[#d4af37]' 
                              : 'text-[#94a3b8] hover:text-[#d4af37]'
                          }`}
                        />
                      </button>
                    </td>
                    {/* Draft Board column */}
                    <td className="text-center py-3 px-2">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onAddToDraftBoard?.(index);
                              }}
                              className="hover:scale-110 transition-transform"
                            >
                              <Clipboard className="w-4 h-4 text-[#94a3b8] hover:text-[#d4af37]" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="bg-[#1a2332] border-[#2d4a6f]">
                            <p className="text-white text-xs">Add to Draft Board</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </td>
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
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
