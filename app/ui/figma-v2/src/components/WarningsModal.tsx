import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { AlertTriangle } from 'lucide-react';

interface WarningsModalProps {
  open: boolean;
  onClose: () => void;
  warnings: string[];
}

export function WarningsModal({ open, onClose, warnings }: WarningsModalProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            Auto-Fill Warnings
          </DialogTitle>
          <DialogDescription className="text-[#94a3b8]">
            {warnings.length} warning{warnings.length !== 1 ? 's' : ''} generated during depth chart auto-fill
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[400px] pr-4">
          <div className="space-y-2">
            {warnings.map((warning, index) => (
              <div
                key={index}
                className="flex gap-3 p-3 bg-amber-900/20 border border-amber-700/30 rounded text-sm"
              >
                <span className="text-amber-400 flex-shrink-0 font-mono text-xs mt-0.5">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="text-amber-100 flex-1">{warning}</span>
              </div>
            ))}
          </div>
        </ScrollArea>

        <div className="flex justify-end pt-4 border-t border-[#2d4a6f]">
          <Button
            onClick={onClose}
            className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
