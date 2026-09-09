import { useState } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Clipboard } from 'lucide-react';

interface ProspectRowProps {
  prospect: {
    id: string;
    name: string;
    pos: string;
    ovr: number;
    college: string;
    grade: string;
  };
  isOnClock: boolean;
  onDraft?: () => void;
  onAddToBoard?: () => void;
  onClick?: () => void;
}

export function ProspectRow({ prospect, isOnClock, onDraft, onAddToBoard, onClick }: ProspectRowProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <tr
      className="border-b border-[#1F2A35] hover:bg-[#1a2332]/50 transition-colors cursor-pointer group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {/* Name */}
      <td className="py-3 px-4">
        <span className="text-white text-sm hover:text-[#d4af37] transition-colors">
          {prospect.name}
        </span>
      </td>
      
      {/* Position */}
      <td className="py-3 px-4 text-center" style={{ width: '80px' }}>
        <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8] text-xs">
          {prospect.pos}
        </Badge>
      </td>
      
      {/* OVR */}
      <td className="py-3 px-4 text-right" style={{ width: '80px' }}>
        <span className={`text-sm px-2 py-0.5 rounded ${
          prospect.ovr >= 90 ? 'bg-green-500/20 text-green-300' :
          prospect.ovr >= 80 ? 'bg-blue-500/20 text-blue-300' :
          prospect.ovr >= 70 ? 'bg-yellow-500/20 text-yellow-300' :
          'bg-gray-500/20 text-gray-300'
        }`}>
          {prospect.ovr}
        </span>
      </td>
      
      {/* College */}
      <td className="py-3 px-4 text-[#94a3b8] text-sm" style={{ width: '180px' }}>
        {prospect.college}
      </td>
      
      {/* Grade */}
      <td className="py-3 px-4 text-[#94a3b8] text-sm" style={{ width: '100px' }}>
        {prospect.grade}
      </td>
      
      {/* Actions */}
      <td className="py-3 px-4 text-right" style={{ width: '200px' }}>
        <div className="flex items-center justify-end gap-2">
          {(isHovered || isOnClock) && (
            <>
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onAddToBoard?.();
                }}
                className="opacity-0 group-hover:opacity-100 transition-opacity text-[#94a3b8] hover:text-[#d4af37]"
              >
                <Clipboard className="w-4 h-4 mr-1" />
                Board
              </Button>
              {isOnClock && (
                <Button
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDraft?.();
                  }}
                  className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
                >
                  Draft
                </Button>
              )}
            </>
          )}
        </div>
      </td>
    </tr>
  );
}
