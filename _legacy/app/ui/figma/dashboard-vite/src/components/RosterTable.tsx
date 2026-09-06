import React, { useState, useEffect, useCallback } from 'react';
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  closestCenter,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
} from '@dnd-kit/sortable';
import { restrictToHorizontalAxis } from '@dnd-kit/modifiers';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { ColDef } from './roster/columnsAttributes';
import { attributesColumns } from './roster/columnsAttributes';
import { statsColumns } from './roster/columnsStats';
import { DraggableHeader } from './roster/DraggableHeader';
import { ColumnSettings } from './roster/ColumnSettings';
import {
  getSavedOrder,
  saveOrder,
  applyOrder,
  defaultKeys,
  moveGroup,
  ViewKey
} from '../utils/columnOrder';

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

interface RosterTableProps {
  players: Player[];
  stats: PlayerStats[];
  viewMode: 'attributes' | 'stats';
  loading: boolean;
  error: boolean;
  searchQuery: string;
  onPlayerClick: (player: Player) => void;
}

export function RosterTable({ players, stats, viewMode, loading, error, searchQuery, onPlayerClick }: RosterTableProps) {
  const [sortField, setSortField] = useState<string>('ovr');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [columns, setColumns] = useState<ColDef[]>([]);
  const [lockGroups, setLockGroups] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor)
  );

  // Load column configuration
  useEffect(() => {
    const defaultColumns = viewMode === 'attributes' ? attributesColumns : statsColumns;
    const savedOrder = getSavedOrder(viewMode as ViewKey);
    
    if (savedOrder) {
      const orderedColumns = applyOrder(defaultColumns, savedOrder);
      setColumns(orderedColumns);
    } else {
      setColumns(defaultColumns);
    }
  }, [viewMode]);

  // Load lock groups setting
  useEffect(() => {
    const saved = localStorage.getItem(`roster.lockGroups.${viewMode}`);
    if (saved !== null) {
      setLockGroups(JSON.parse(saved));
    }
  }, [viewMode]);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    
    if (!over || active.id === over.id) {
      setActiveId(null);
      return;
    }

    const activeColumn = columns.find(col => col.key === active.id);
    const overColumn = columns.find(col => col.key === over.id);
    
    if (!activeColumn || !overColumn) {
      setActiveId(null);
      return;
    }

    // Don't allow moving fixed columns
    if (activeColumn.fixed || overColumn.fixed) {
      setActiveId(null);
      return;
    }

    const oldIndex = columns.findIndex(col => col.key === active.id);
    const newIndex = columns.findIndex(col => col.key === over.id);

    let newColumns: ColDef[];

    if (lockGroups && viewMode === 'stats') {
      // Move entire group
      newColumns = moveGroup(columns, oldIndex, newIndex) as ColDef[];
    } else {
      // Move single column
      newColumns = arrayMove(columns, oldIndex, newIndex);
    }

    setColumns(newColumns);
    saveOrder(viewMode as ViewKey, newColumns.map(col => col.key));
    setActiveId(null);
  }, [columns, lockGroups, viewMode]);

  const handleKeyDown = useCallback((event: KeyboardEvent, columnKey: string) => {
    if (!event.altKey) return;

    const columnIndex = columns.findIndex(col => col.key === columnKey);
    const column = columns[columnIndex];
    
    if (!column || column.fixed) return;

    let newIndex = columnIndex;

    if (event.key === 'ArrowLeft') {
      newIndex = Math.max(1, columnIndex - 1); // Don't go before fixed column
    } else if (event.key === 'ArrowRight') {
      newIndex = Math.min(columns.length - 1, columnIndex + 1);
    } else {
      return;
    }

    if (newIndex === columnIndex) return;

    let newColumns: ColDef[];

    if (lockGroups && viewMode === 'stats') {
      newColumns = moveGroup(columns, columnIndex, newIndex) as ColDef[];
    } else {
      newColumns = arrayMove(columns, columnIndex, newIndex);
    }

    setColumns(newColumns);
    saveOrder(viewMode as ViewKey, newColumns.map(col => col.key));
  }, [columns, lockGroups, viewMode]);

  const handleResetColumns = useCallback(() => {
    const defaultColumns = viewMode === 'attributes' ? attributesColumns : statsColumns;
    setColumns(defaultColumns);
    saveOrder(viewMode as ViewKey, defaultKeys(defaultColumns));
  }, [viewMode]);

  const handleToggleLockGroups = useCallback((locked: boolean) => {
    setLockGroups(locked);
    localStorage.setItem(`roster.lockGroups.${viewMode}`, JSON.stringify(locked));
  }, [viewMode]);

  const getSortIcon = (field: string) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 opacity-50" />;
    return sortDirection === 'asc' ? 
      <ArrowUp className="h-3 w-3" /> : 
      <ArrowDown className="h-3 w-3" />;
  };

  const filteredPlayers = players.filter(player => {
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
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    }
    
    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return sortDirection === 'asc' ? 
      aStr.localeCompare(bStr) : 
      bStr.localeCompare(aStr);
  });

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'Healthy': return 'bg-green-500/20 text-green-400';
      case 'Q': return 'bg-amber-500/20 text-amber-400';
      case 'D': return 'bg-red-500/20 text-red-400';
      case 'O': return 'bg-gray-500/20 text-gray-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const activeColumn = columns.find(col => col.key === activeId);

  return (
    <div id="rosterCard" className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Title */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between">
          <h3 className="text-white">Roster ({sortedPlayers.length} players)</h3>
          <div className="flex items-center gap-2">
            {error && <span className="text-[#94a3b8] text-xs">(demo)</span>}
            <ColumnSettings
              view={viewMode}
              columns={columns}
              lockGroups={lockGroups}
              onResetColumns={handleResetColumns}
              onToggleLockGroups={handleToggleLockGroups}
              onReorderColumns={(keys) => {
                const newColumns = applyOrder(columns, keys);
                setColumns(newColumns);
              }}
            />
          </div>
        </div>
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

      {/* Table Container with Dual Scrollbars */}
      <div className="relative">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          modifiers={[restrictToHorizontalAxis]}
        >
          {/* Main scrollable container */}
          <div id="rosterBodyScroll" className="overflow-x-auto overflow-y-auto max-h-[560px]">
            <table id="rosterTable" className="w-full text-sm">
            <thead className="sticky top-0 bg-[#1a2332] z-10">
              <tr className="border-b border-[#2d4a6f]">
                  <SortableContext
                    items={columns.map(col => col.key)}
                    strategy={rectSortingStrategy}
                  >
                    {columns.map((column) => (
                      <DraggableHeader key={column.key} column={column} onKeyDown={handleKeyDown}>
                        <button
                          onClick={() => handleSort(column.key)}
                          className="flex items-center gap-1 hover:text-white transition-colors"
                        >
                          {column.label} {getSortIcon(column.key)}
                  </button>
                      </DraggableHeader>
                    ))}
                  </SortableContext>

              </tr>
            </thead>

            <tbody>
              {loading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-b border-[#2d4a6f]/50">
                    <td className="sticky left-0 bg-[#1a2332] py-3 px-4 border-r border-[#2d4a6f]">
                      <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
                    </td>
                    {Array.from({ length: viewMode === 'attributes' ? 19 : 7 }).map((_, j) => (
                      <td key={j} className="py-3 px-3">
                        <Skeleton className="h-6 w-full bg-[#2d4a6f]" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : sortedPlayers.length === 0 ? (
                <tr>
                  <td colSpan={viewMode === 'attributes' ? 20 : 8} className="py-12 text-center">
                    <div className="text-[#94a3b8]">
                      <p className="mb-2">No players found</p>
                      <p className="text-sm">Adjust filters or clear search</p>
                    </div>
                  </td>
                </tr>
              ) : (
                sortedPlayers.map((player, idx) => (
                  <tr
                    key={idx}
                    onClick={() => onPlayerClick(player)}
                    className="border-b border-[#2d4a6f]/50 hover:bg-[#2d4a6f]/30 transition-colors cursor-pointer"
                    style={{ height: '44px' }}
                  >
                    {columns.map((column) => {
                      const playerStats = stats.find(s => s.name === player.name);
                      const value = column.key === 'name' ? player : 
                                   viewMode === 'stats' ? (playerStats?.[column.key as keyof PlayerStats] ?? player[column.key as keyof Player]) :
                                   player[column.key as keyof Player];

                      return (
                        <td
                          key={column.key}
                          className={`${column.key === 'name' ? 'sticky left-0 bg-[#1a2332] border-r border-[#2d4a6f]' : ''} py-2.5 px-3`}
                          style={{
                            width: column.width,
                            minWidth: column.minWidth,
                            maxWidth: column.maxWidth,
                            textAlign: column.numeric ? 'right' : column.align || 'left',
                          }}
                        >
                          {column.key === 'name' ? (
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-[#2d4a6f] flex items-center justify-center text-white text-xs">
                          {player.num}
                        </div>
                        <div>
                                <a
                                  href={`/players/${player.id || '123'}`}
                                  data-entity="player"
                                  data-id={player.id || '123'}
                                  className="entity-link text-white hover:text-[#d4af37] transition-colors"
                                >
                                  {player.name}
                                </a>
                          <div className="text-[#94a3b8] text-xs">{player.pos} · Age {player.age}</div>
                        </div>
                      </div>
                          ) : column.key === 'ovr' ? (
                          <span className="inline-block px-2 py-1 rounded bg-[#d4af37]/20 text-[#d4af37] border border-[#d4af37]/30">
                              {value as number}
                          </span>
                          ) : column.key === 'hlth' ? (
                            <span className={`inline-block px-2 py-0.5 rounded text-xs ${getHealthColor(value as string)}`}>
                              {value as string}
                          </span>
                          ) : column.key === 'trd' ? (
                            <div className="text-center">
                              {value && (
                            <span className="inline-block w-2 h-2 rounded-full bg-[#d4af37]" />
                              )}
                            </div>
                          ) : (
                            <span className={column.numeric ? 'text-white tabular-nums' : 'text-[#94a3b8]'}>
                              {value || '—'}
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <DragOverlay>
          {activeColumn ? (
            <div className="bg-[#1e3a5f] text-white px-3 py-2 rounded border border-[#2d4a6f] shadow-lg">
              {activeColumn.label}
            </div>
          ) : null}
        </DragOverlay>
        </DndContext>

        {/* Pinned Bottom Scrollbar */}
        {!loading && sortedPlayers.length > 0 && (
          <div className="sticky bottom-0 overflow-x-auto border-t border-[#2d4a6f] bg-[#1a2332]">
            <div style={{ width: viewMode === 'attributes' ? '2400px' : '1200px', height: '1px' }} />
          </div>
        )}
      </div>
    </div>
  );
}
