import { X } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

interface ProspectCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  prospect: {
    id: string;
    name: string;
    pos: string;
    ovr: number;
    pot: number;
    college: string;
    grade: string;
    speed: number;
    strength: number;
    agility: number;
    awareness: number;
    blurb?: string;
    projection?: string;
  } | null;
  isOnClock: boolean;
  onDraft?: () => void;
  onAddToBoard?: () => void;
}

export function ProspectCardModal({
  isOpen,
  onClose,
  prospect,
  isOnClock,
  onDraft,
  onAddToBoard,
}: ProspectCardModalProps) {
  if (!prospect) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-[#11161C] border-[#1F2A35] text-white max-w-[720px] p-0">
        {/* Header */}
        <DialogHeader className="p-6 pb-4 border-b border-[#1F2A35]">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <DialogTitle className="text-white text-2xl mb-2">
                {prospect.name}
              </DialogTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8]">
                  {prospect.pos}
                </Badge>
                <span className={`px-3 py-1 rounded text-sm ${
                  prospect.ovr >= 90 ? 'bg-green-500/20 text-green-300' :
                  prospect.ovr >= 80 ? 'bg-blue-500/20 text-blue-300' :
                  prospect.ovr >= 70 ? 'bg-yellow-500/20 text-yellow-300' :
                  'bg-gray-500/20 text-gray-300'
                }`}>
                  OVR {prospect.ovr}
                </span>
                <Badge variant="outline" className="border-[#d4af37] text-[#d4af37]">
                  {prospect.college}
                </Badge>
              </div>
            </div>
          </div>
        </DialogHeader>

        {/* Body */}
        <div className="p-6">
          <div className="grid grid-cols-2 gap-6">
            {/* Left: Stats */}
            <div>
              <h4 className="text-[#94a3b8] text-sm uppercase tracking-wide mb-3">
                Attributes
              </h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between py-2 border-b border-[#1F2A35]">
                  <span className="text-[#94a3b8] text-sm">Overall</span>
                  <span className="text-white">{prospect.ovr}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-[#1F2A35]">
                  <span className="text-[#94a3b8] text-sm">Potential</span>
                  <span className="text-white">{prospect.pot}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-[#1F2A35]">
                  <span className="text-[#94a3b8] text-sm">Speed</span>
                  <span className="text-white">{prospect.speed}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-[#1F2A35]">
                  <span className="text-[#94a3b8] text-sm">Strength</span>
                  <span className="text-white">{prospect.strength}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-[#1F2A35]">
                  <span className="text-[#94a3b8] text-sm">Agility</span>
                  <span className="text-white">{prospect.agility}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-[#1F2A35]">
                  <span className="text-[#94a3b8] text-sm">Awareness</span>
                  <span className="text-white">{prospect.awareness}</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-[#94a3b8] text-sm">Grade</span>
                  <span className="text-[#d4af37]">{prospect.grade}</span>
                </div>
              </div>
            </div>

            {/* Right: Blurb & Projection */}
            <div>
              <h4 className="text-[#94a3b8] text-sm uppercase tracking-wide mb-3">
                Scout Report
              </h4>
              <div className="space-y-4">
                <div>
                  <p className="text-[#94a3b8] text-sm leading-relaxed">
                    {prospect.blurb || 
                      `${prospect.name} is a ${prospect.pos} prospect from ${prospect.college} with strong fundamentals and solid athletic ability. Shows promise in multiple areas of the game.`
                    }
                  </p>
                </div>
                
                <div className="bg-[#1a2332] border border-[#2d4a6f] rounded-lg p-3">
                  <div className="text-[#d4af37] text-xs uppercase tracking-wide mb-1">
                    Draft Projection
                  </div>
                  <div className="text-white text-sm">
                    {prospect.projection || 
                      `Round ${prospect.ovr >= 90 ? '1-2' : prospect.ovr >= 80 ? '2-3' : prospect.ovr >= 70 ? '3-5' : '5-7'}`
                    }
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 pt-4 border-t border-[#1F2A35] flex items-center justify-end gap-3">
          <Button
            variant="outline"
            onClick={onClose}
            className="border-[#2d4a6f] text-[#94a3b8] hover:bg-[#1a2332]"
          >
            Close
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              onAddToBoard?.();
              onClose();
            }}
            className="border-[#2d4a6f] text-white hover:bg-[#1a2332]"
          >
            Add to Board
          </Button>
          {isOnClock && (
            <Button
              onClick={() => {
                onDraft?.();
                onClose();
              }}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              Draft
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
