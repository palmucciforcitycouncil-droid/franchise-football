import { X } from 'lucide-react';

interface PositionQuota {
  current: number;
  min: number;
}

interface PositionQuotaFilterProps {
  positionQuotas: Record<string, PositionQuota>;
  selectedPosition: string | null;
  onPositionSelect: (position: string | null) => void;
  className?: string;
}

export function PositionQuotaFilter({
  positionQuotas,
  selectedPosition,
  onPositionSelect,
  className = ''
}: PositionQuotaFilterProps) {
  const handlePositionClick = (pos: string) => {
    if (selectedPosition === pos) {
      onPositionSelect(null);
    } else {
      onPositionSelect(pos);
    }
  };

  return (
    <div className={`bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-white text-sm">Team Quota</h3>
        {selectedPosition && (
          <button
            onClick={() => onPositionSelect(null)}
            className="px-2 py-1 rounded text-xs bg-[#2d4a6f] text-white hover:bg-[#3d5a7f] flex items-center gap-1"
          >
            <X className="h-3 w-3" />
            Clear Filter
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {Object.entries(positionQuotas).map(([pos, { current, min }]) => {
          const isMeetingQuota = current >= min;
          const isActive = selectedPosition === pos;
          
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
  );
}
