import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { Checkbox } from './ui/checkbox';
import { Slider } from './ui/slider';
import { Label } from './ui/label';
import { Button } from './ui/button';

interface FilterPanelProps {
  open: boolean;
  onClose: () => void;
}

export function FilterPanel({ open, onClose }: FilterPanelProps) {
  const positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'ST'];

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="bg-[#1a2332] border-l border-[#2d4a6f] w-[400px] overflow-y-auto" aria-describedby="filter-description">
        <div id="filter-description" className="sr-only">Filter roster by position, attributes, and status</div>
        <SheetHeader className="border-b border-[#2d4a6f] pb-4 mb-6">
          <SheetTitle className="text-white">Filter Roster</SheetTitle>
        </SheetHeader>

        <div className="space-y-6">
          {/* Position Filter */}
          <div>
            <Label className="text-white mb-3 block">Positions</Label>
            <div className="grid grid-cols-2 gap-3">
              {positions.map(pos => (
                <div key={pos} className="flex items-center space-x-2">
                  <Checkbox id={pos} />
                  <label
                    htmlFor={pos}
                    className="text-sm text-white cursor-pointer"
                  >
                    {pos}
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Attribute Sliders */}
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-white">Overall (OVR)</Label>
                <span className="text-[#94a3b8] text-sm">60-99</span>
              </div>
              <Slider defaultValue={[60, 99]} max={99} min={0} step={1} className="w-full" />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-white">Speed (SPD)</Label>
                <span className="text-[#94a3b8] text-sm">0-99</span>
              </div>
              <Slider defaultValue={[0, 99]} max={99} min={0} step={1} className="w-full" />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-white">Catching (CTH)</Label>
                <span className="text-[#94a3b8] text-sm">0-99</span>
              </div>
              <Slider defaultValue={[0, 99]} max={99} min={0} step={1} className="w-full" />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-white">Tackling (TCK)</Label>
                <span className="text-[#94a3b8] text-sm">0-99</span>
              </div>
              <Slider defaultValue={[0, 99]} max={99} min={0} step={1} className="w-full" />
            </div>
          </div>

          {/* Status Toggles */}
          <div>
            <Label className="text-white mb-3 block">Status</Label>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox id="injured" />
                <label htmlFor="injured" className="text-sm text-white cursor-pointer">
                  Injured only
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox id="trade-block" />
                <label htmlFor="trade-block" className="text-sm text-white cursor-pointer">
                  On trade block
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox id="rookie" />
                <label htmlFor="rookie" className="text-sm text-white cursor-pointer">
                  Rookie (age ≤ 23)
                </label>
              </div>
            </div>
          </div>

          {/* Query Helper */}
          <div>
            <Label className="text-white mb-2 block">Generated Query</Label>
            <div className="bg-[#0a1929] rounded-lg p-3 border border-[#2d4a6f]">
              <code className="text-[#94a3b8] text-xs">
                {'OVR >= 60 AND OVR <= 99'}
              </code>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 border-t border-[#2d4a6f]">
            <Button
              variant="outline"
              className="flex-1 bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
              onClick={onClose}
            >
              Clear All
            </Button>
            <Button
              className="flex-1 bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
              onClick={onClose}
            >
              Apply Filters
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
