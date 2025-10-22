import React, { ReactNode } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ColDef } from './columnsAttributes';
import { GripVertical } from 'lucide-react';

interface DraggableHeaderProps {
  column: ColDef;
  children: ReactNode;
  onKeyDown?: (event: KeyboardEvent, columnKey: string) => void;
}

export function DraggableHeader({ column, children, onKeyDown }: DraggableHeaderProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: column.key,
    disabled: column.fixed,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <th
      ref={setNodeRef}
      style={{
        ...style,
        width: column.width,
        minWidth: column.minWidth,
        maxWidth: column.maxWidth,
        textAlign: column.align || 'left',
      }}
      className={`${column.key === 'name' ? 'sticky left-0 bg-[#1a2332] z-20 border-r border-[#2d4a6f]' : ''} relative group text-left py-3 px-4 text-[#94a3b8]`}
      onKeyDown={(e) => onKeyDown?.(e as any, column.key)}
      tabIndex={column.fixed ? -1 : 0}
      title={column.tooltip}
      {...attributes}
    >
      <div className="flex items-center justify-between">
        {children}
        {!column.fixed && (
          <div
            {...listeners}
            className="opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing p-1 hover:bg-[#2d4a6f]/30 rounded"
            title="Drag to reorder column"
          >
            <GripVertical className="h-4 w-4 text-[#94a3b8]" />
          </div>
        )}
      </div>
    </th>
  );
}
