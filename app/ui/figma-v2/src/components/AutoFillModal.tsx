import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { Info } from 'lucide-react';
import { AutoFillOptions } from '../lib/mockDepthChartApi';

interface AutoFillModalProps {
  open: boolean;
  onClose: () => void;
  onApply: (options: AutoFillOptions) => Promise<void>;
}

export function AutoFillModal({ open, onClose, onApply }: AutoFillModalProps) {
  const [isApplying, setIsApplying] = useState(false);
  const [options, setOptions] = useState<AutoFillOptions>({
    respect_injuries: true,
    respect_fatigue: true,
    lock_starters: false,
    allow_cross_training: false,
  });

  const handleApply = async () => {
    setIsApplying(true);
    try {
      await onApply(options);
      onClose();
    } catch (error) {
      console.error('Failed to auto-fill depth chart:', error);
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#1a2332] border border-[#2d4a6f] max-w-[520px]">
        <DialogHeader>
          <DialogTitle className="text-white text-xl">Auto-Fill Depth Chart</DialogTitle>
          <DialogDescription className="text-[#94a3b8]">
            We'll assign the best available players at each slot based on OVR and positional fit.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Respect Injuries */}
          <div className="flex items-center justify-between space-x-4">
            <div className="flex items-center gap-2 flex-1">
              <Label htmlFor="respect-injuries" className="text-white cursor-pointer">
                Respect Injuries
              </Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-4 w-4 text-[#94a3b8] cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="bg-[#0a1929] border-[#2d4a6f] text-white max-w-[280px]">
                    <p>Skip players marked OUT or Doubtful</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Switch
              id="respect-injuries"
              checked={options.respect_injuries}
              onCheckedChange={(checked) =>
                setOptions({ ...options, respect_injuries: checked })
              }
              className="data-[state=checked]:bg-[#d4af37]"
            />
          </div>

          {/* Respect Fatigue */}
          <div className="flex items-center justify-between space-x-4">
            <div className="flex items-center gap-2 flex-1">
              <Label htmlFor="respect-fatigue" className="text-white cursor-pointer">
                Respect Fatigue
              </Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-4 w-4 text-[#94a3b8] cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="bg-[#0a1929] border-[#2d4a6f] text-white max-w-[280px]">
                    <p>De-prioritize players with STA &lt; 50 if a comparable alternative exists (±2 OVR)</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Switch
              id="respect-fatigue"
              checked={options.respect_fatigue}
              onCheckedChange={(checked) =>
                setOptions({ ...options, respect_fatigue: checked })
              }
              className="data-[state=checked]:bg-[#d4af37]"
            />
          </div>

          {/* Lock Starters */}
          <div className="flex items-center justify-between space-x-4">
            <div className="flex items-center gap-2 flex-1">
              <Label htmlFor="lock-starters" className="text-white cursor-pointer">
                Lock Starters
              </Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-4 w-4 text-[#94a3b8] cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="bg-[#0a1929] border-[#2d4a6f] text-white max-w-[280px]">
                    <p>Keep currently assigned starter slots (QB1, RB1, etc.); re-fill backups only</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Switch
              id="lock-starters"
              checked={options.lock_starters}
              onCheckedChange={(checked) =>
                setOptions({ ...options, lock_starters: checked })
              }
              className="data-[state=checked]:bg-[#d4af37]"
            />
          </div>

          {/* Allow Cross-Training */}
          <div className="flex items-center justify-between space-x-4">
            <div className="flex items-center gap-2 flex-1">
              <Label htmlFor="allow-cross-training" className="text-white cursor-pointer">
                Allow Cross-Training
              </Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-4 w-4 text-[#94a3b8] cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="bg-[#0a1929] border-[#2d4a6f] text-white max-w-[280px]">
                    <p>Allow secondary positions if primary slots are filled (applies -2 OVR penalty)</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Switch
              id="allow-cross-training"
              checked={options.allow_cross_training}
              onCheckedChange={(checked) =>
                setOptions({ ...options, allow_cross_training: checked })
              }
              className="data-[state=checked]:bg-[#d4af37]"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={isApplying}
            className="text-[#94a3b8] hover:text-white hover:bg-[#2d4a6f]"
          >
            Cancel
          </Button>
          <Button
            onClick={handleApply}
            disabled={isApplying}
            className="bg-[#d4af37] hover:bg-[#b8941f] text-[#0a1929]"
          >
            {isApplying ? 'Applying...' : 'Apply Auto-Fill'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
