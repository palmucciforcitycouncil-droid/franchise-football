import { GripVertical, X, ChevronUp, ChevronDown } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';

interface BoardItemProps {
  prospect: {
    id: string;
    name: string;
    pos: string;
    ovr: number;
    college: string;
  };
  index: number;
  isOnClock: boolean;
  isDragging?: boolean;
  onDraft?: () => void;
  onRemove?: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  isFirst?: boolean;
  isLast?: boolean;
}

export function BoardItem({ 
  prospect, 
  index, 
  isOnClock, 
  isDragging,
  onDraft,
  onRemove,
  onMoveUp,
  onMoveDown,
  isFirst,
  isLast
}: BoardItemProps) {
  return (
    <div
      className={`
        bg-[#0B0F14] border border-[#1F2A35] rounded-lg p-3 transition-all group
        ${isDragging ? 'opacity-50 scale-95' : 'hover:bg-[#1a2332]'}
      `}
    >
      <div className="flex items-start gap-3">
        {/* Drag Handle & Rank */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <GripVertical className="w-4 h-4 text-[#94a3b8]/50 cursor-move" />
          <div className="w-6 h-6 rounded-full bg-[#d4af37] flex items-center justify-center text-xs text-[#0a1929]">
            {index + 1}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex-1 min-w-0">
              <div className="text-white text-sm truncate">
                <ClickablePlayerName playerName={prospect.name} />
              </div>
              <div className="text-[#94a3b8] text-xs">{prospect.college}</div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8] text-xs">
                {prospect.pos}
              </Badge>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                prospect.ovr >= 90 ? 'bg-green-500/20 text-green-300' :
                prospect.ovr >= 80 ? 'bg-blue-500/20 text-blue-300' :
                prospect.ovr >= 70 ? 'bg-yellow-500/20 text-yellow-300' :
                'bg-gray-500/20 text-gray-300'
              }`}>
                {prospect.ovr}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {isOnClock && (
              <Button
                size="sm"
                onClick={onDraft}
                className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] h-7 text-xs"
              >
                Draft
              </Button>
            )}
            
            {/* Keyboard reordering buttons */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={onMoveUp}
                disabled={isFirst}
                className="p-1 text-[#94a3b8] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Move up"
              >
                <ChevronUp className="w-3 h-3" />
              </button>
              <button
                onClick={onMoveDown}
                disabled={isLast}
                className="p-1 text-[#94a3b8] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Move down"
              >
                <ChevronDown className="w-3 h-3" />
              </button>
            </div>

            <button
              onClick={onRemove}
              className="ml-auto p-1 text-[#94a3b8] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
              title="Remove from board"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
