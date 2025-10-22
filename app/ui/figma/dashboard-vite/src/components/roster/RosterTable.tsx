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
import { ColDef } from './columnsAttributes';
import { attributesColumns } from './columnsAttributes';
import { statsColumns } from './columnsStats';
import { DraggableHeader } from './DraggableHeader';
import { ColumnSettings } from './ColumnSettings';
import {
  getSavedOrder,
  saveOrder,
  applyOrder,
  defaultKeys,
  moveGroup,
  ViewKey
} from '../../utils/columnOrder';

interface Player {
  id: string;
  name: string;
  position: string;
  [key: string]: any;
}

interface RosterTableProps {
  view: 'attributes' | 'stats';
  players: Player[];
  onPlayerClick?: (player: Player) => void;
}

export function RosterTable({ view, players, onPlayerClick }: RosterTableProps) {
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
    const defaultColumns = view === 'attributes' ? attributesColumns : statsColumns;
    const savedOrder = getSavedOrder(view as ViewKey);
    
    if (savedOrder) {
      const orderedColumns = applyOrder(defaultColumns, savedOrder);
      setColumns(orderedColumns);
    } else {
      setColumns(defaultColumns);
    }
  }, [view]);

  // Load lock groups setting
  useEffect(() => {
    const saved = localStorage.getItem(`roster.lockGroups.${view}`);
    if (saved !== null) {
      setLockGroups(JSON.parse(saved));
    }
  }, [view]);

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

    if (lockGroups && view === 'stats') {
      // Move entire group
      newColumns = moveGroup(columns, oldIndex, newIndex);
    } else {
      // Move single column
      newColumns = arrayMove(columns, oldIndex, newIndex);
    }

    setColumns(newColumns);
    saveOrder(view as ViewKey, newColumns.map(col => col.key));
    setActiveId(null);
  }, [columns, lockGroups, view]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent, columnKey: string) => {
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

    if (lockGroups && view === 'stats') {
      newColumns = moveGroup(columns, columnIndex, newIndex);
    } else {
      newColumns = arrayMove(columns, columnIndex, newIndex);
    }

    setColumns(newColumns);
    saveOrder(view as ViewKey, newColumns.map(col => col.key));
  }, [columns, lockGroups, view]);

  const handleResetColumns = useCallback(() => {
    const defaultColumns = view === 'attributes' ? attributesColumns : statsColumns;
    setColumns(defaultColumns);
    saveOrder(view as ViewKey, defaultKeys(defaultColumns));
  }, [view]);

  const handleToggleLockGroups = useCallback((locked: boolean) => {
    setLockGroups(locked);
    localStorage.setItem(`roster.lockGroups.${view}`, JSON.stringify(locked));
  }, [view]);

  const activeColumn = columns.find(col => col.key === activeId);

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <div className="flex items-center justify-between">
          <h3 className="text-white">Roster</h3>
          <ColumnSettings
            view={view}
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

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          modifiers={[restrictToHorizontalAxis]}
        >
          <table className="w-full">
            <thead className="sticky top-0 bg-[#0a1929] z-10">
              <tr>
                <SortableContext
                  items={columns.map(col => col.key)}
                  strategy={rectSortingStrategy}
                >
                  {columns.map((column) => (
                    <DraggableHeader key={column.key} column={column}>
                      <th
                        className="px-3 py-2 text-left text-[#94a3b8] text-xs font-medium border-b border-[#2d4a6f]"
                        style={{
                          width: column.width,
                          minWidth: column.minWidth,
                          maxWidth: column.maxWidth,
                          textAlign: column.align || 'left',
                        }}
                        onKeyDown={(e) => handleKeyDown(e, column.key)}
                        tabIndex={column.fixed ? -1 : 0}
                        title={column.tooltip}
                      >
                        {column.label}
                      </th>
                    </DraggableHeader>
                  ))}
                </SortableContext>
              </tr>
            </thead>
            <tbody>
              {players.map((player) => (
                <tr
                  key={player.id}
                  className="border-b border-[#2d4a6f]/30 hover:bg-[#2d4a6f]/20 transition-colors cursor-pointer"
                  onClick={() => onPlayerClick?.(player)}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className="px-3 py-2 text-sm border-b border-[#2d4a6f]/20"
                      style={{
                        width: column.width,
                        minWidth: column.minWidth,
                        maxWidth: column.maxWidth,
                        textAlign: column.numeric ? 'right' : column.align || 'left',
                      }}
                    >
                      {column.key === 'name' ? (
                        <div>
                          <div className="text-white font-medium">{player.name}</div>
                          <div className="text-[#94a3b8] text-xs">{player.position}</div>
                        </div>
                      ) : (
                        <span className={column.numeric ? 'text-white' : 'text-[#94a3b8]'}>
                          {player[column.key] || '-'}
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          <DragOverlay>
            {activeColumn ? (
              <div className="bg-[#1e3a5f] text-white px-3 py-2 rounded border border-[#2d4a6f] shadow-lg">
                {activeColumn.label}
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>
    </div>
  );
}
