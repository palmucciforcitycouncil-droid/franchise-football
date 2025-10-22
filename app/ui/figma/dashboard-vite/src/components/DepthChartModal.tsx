import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { GripVertical } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';

interface Player {
  name: string;
  num: number;
  pos: string;
  ovr: number;
  dep: string;
}

interface DepthChartModalProps {
  open: boolean;
  onClose: () => void;
  players: Player[];
}

export function DepthChartModal({ open, onClose, players }: DepthChartModalProps) {
  const positions = ['QB', 'RB', 'WR', 'TE', 'C', 'G', 'T', 'DE', 'DT', 'LB', 'CB', 'S', 'K', 'P'];

  const getPlayersForPosition = (pos: string) => {
    return players
      .filter(p => p.pos === pos)
      .sort((a, b) => {
        const depA = parseInt(a.dep.replace(/\D/g, '')) || 999;
        const depB = parseInt(b.dep.replace(/\D/g, '')) || 999;
        return depA - depB;
      });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#1a2332] border-[#2d4a6f] max-w-4xl max-h-[80vh]">
        <DialogHeader className="border-b border-[#2d4a6f] pb-4">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-white">Depth Chart</DialogTitle>
            <Button
              size="sm"
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              Auto Assign
            </Button>
          </div>
          <DialogDescription className="text-[#94a3b8] text-sm mt-2">
            Drag to reorder. Auto Assign uses OVR, then AWR, then STA to fill slots.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-5 gap-4 py-4">
          {/* Positions List */}
          <div className="col-span-2 bg-[#0a1929] rounded-lg p-3">
            <h3 className="text-white mb-3 text-sm">Positions</h3>
            <ScrollArea className="h-[400px]">
              <div className="space-y-1">
                {positions.map(pos => (
                  <button
                    key={pos}
                    className="w-full text-left px-3 py-2 rounded hover:bg-[#2d4a6f] text-white transition-colors text-sm"
                  >
                    {pos}
                  </button>
                ))}
              </div>
            </ScrollArea>
          </div>

          {/* Depth List */}
          <div className="col-span-3 bg-[#0a1929] rounded-lg p-3">
            <h3 className="text-white mb-3 text-sm">QB Depth</h3>
            <ScrollArea className="h-[400px]">
              <div className="space-y-2">
                {getPlayersForPosition('QB').map((player, idx) => (
                  <div
                    key={player.num}
                    className="flex items-center gap-2 p-2 bg-[#1a2332] rounded border border-[#2d4a6f] hover:border-[#d4af37] transition-colors cursor-move"
                  >
                    <GripVertical className="h-4 w-4 text-[#94a3b8]" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[#94a3b8] text-xs">#{player.num}</span>
                          <span className="text-white text-sm">{player.name}</span>
                        </div>
                        <span className="text-[#d4af37] text-sm">{player.ovr}</span>
                      </div>
                      <div className="text-[#94a3b8] text-xs mt-0.5">{player.dep}</div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>

        <div className="flex justify-end gap-3 border-t border-[#2d4a6f] pt-4">
          <Button
            variant="outline"
            onClick={onClose}
            className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
          >
            Cancel
          </Button>
          <Button
            onClick={onClose}
            className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
          >
            Save Changes
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
