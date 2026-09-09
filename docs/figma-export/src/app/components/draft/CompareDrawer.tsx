/**
 * Compare Drawer Component
 * Opens from right on multi-select (2-5 prospects)
 * Shows comparison bars and diff table
 */

import { DraftProspect } from '../../lib/mockDraftApi';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '../ui/sheet';
import { Badge } from '../ui/badge';
import { X } from 'lucide-react';
import { Button } from '../ui/button';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';

interface CompareDrawerProps {
  prospects: DraftProspect[];
  isOpen: boolean;
  onClose: () => void;
}

export function CompareDrawer({ prospects, isOpen, onClose }: CompareDrawerProps) {
  if (prospects.length < 2) return null;

  const baseline = prospects[0];
  const attributes = [
    { key: 'overall', label: 'Overall' },
    { key: 'potential', label: 'Potential' },
    { key: 'speed', label: 'Speed' },
    { key: 'agility', label: 'Agility' },
    { key: 'strength', label: 'Strength' },
    { key: 'awareness', label: 'Awareness' },
    { key: 'board_score', label: 'Board Score' },
  ] as const;

  const getColor = (value: number) => {
    if (value >= 90) return 'bg-[#27ae60]';
    if (value >= 80) return 'bg-[#3498db]';
    if (value >= 70) return 'bg-[#f39c12]';
    return 'bg-[#94a3b8]';
  };

  const getDiffColor = (diff: number) => {
    if (diff > 0) return 'text-[#27ae60]';
    if (diff < 0) return 'text-[#e74c3c]';
    return 'text-[#94a3b8]';
  };

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-full sm:max-w-2xl bg-[#11161C] border-l border-[#1F2A35] overflow-y-auto">
        <SheetHeader className="border-b border-[#1F2A35] pb-4">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-white">Compare Prospects</SheetTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="text-[#94a3b8] hover:text-white"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
          <SheetDescription className="text-[#94a3b8] text-sm">
            Compare up to 5 prospects side by side
          </SheetDescription>
        </SheetHeader>

        {/* Top - Names/Position/Overall */}
        <div className="mt-6 space-y-3">
          <h4 className="text-[#94a3b8] text-sm">Selected Prospects</h4>
          <div className="grid grid-cols-1 gap-3">
            {prospects.map((prospect, index) => (
              <div
                key={prospect.prospect_id}
                className={`bg-[#0B0F14] border rounded-lg p-4 ${
                  index === 0 ? 'border-[#d4af37]' : 'border-[#1F2A35]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {index === 0 && (
                      <Badge className="bg-[#d4af37]/20 text-[#d4af37] border border-[#d4af37]/30">
                        Baseline
                      </Badge>
                    )}
                    <ClickablePlayerName player={prospect} className="text-white">
                      {prospect.name}
                    </ClickablePlayerName>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8]">
                      {prospect.position}
                    </Badge>
                    <div className="text-white">{prospect.overall} OVR</div>
                  </div>
                </div>
                <div className="text-[#94a3b8] text-sm">{prospect.college}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Middle - Percentile Bars */}
        <div className="mt-6 space-y-4">
          <h4 className="text-[#94a3b8] text-sm">Attribute Comparison</h4>
          {attributes.map(({ key, label }) => (
            <div key={key} className="space-y-2">
              <div className="text-white text-sm">{label}</div>
              <div className="space-y-1.5">
                {prospects.map((prospect) => {
                  const value = prospect[key as keyof DraftProspect] as number;
                  const percentage = (value / 99) * 100;
                  
                  return (
                    <div key={prospect.prospect_id} className="flex items-center gap-3">
                      <div className="w-32 text-[#94a3b8] text-xs truncate">
                        {prospect.name.split(' ')[0]}
                      </div>
                      <div className="flex-1 h-6 bg-[#1F2A35] rounded-full overflow-hidden relative">
                        <div
                          className={`h-full ${getColor(value)} transition-all duration-300`}
                          style={{ width: `${percentage}%` }}
                        />
                        <div className="absolute inset-0 flex items-center justify-center text-white text-xs">
                          {value}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Bottom - Diff Table vs Baseline */}
        <div className="mt-6 mb-6">
          <h4 className="text-[#94a3b8] text-sm mb-3">Difference vs Baseline ({baseline.name})</h4>
          <div className="bg-[#0B0F14] border border-[#1F2A35] rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-[#1F2A35]">
                <tr>
                  <th className="px-4 py-3 text-left text-[#94a3b8] text-xs font-semibold">Prospect</th>
                  {attributes.map(({ key, label }) => (
                    <th key={key} className="px-4 py-3 text-center text-[#94a3b8] text-xs font-semibold">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {prospects.slice(1).map((prospect) => (
                  <tr key={prospect.prospect_id} className="border-t border-[#1F2A35]">
                    <td className="px-4 py-3">
                      <div className="text-white text-sm">{prospect.name}</div>
                      <div className="text-[#94a3b8] text-xs">{prospect.position}</div>
                    </td>
                    {attributes.map(({ key }) => {
                      const baseValue = baseline[key as keyof DraftProspect] as number;
                      const prospectValue = prospect[key as keyof DraftProspect] as number;
                      const diff = prospectValue - baseValue;
                      
                      return (
                        <td key={key} className="px-4 py-3 text-center">
                          <div className={`text-sm font-semibold ${getDiffColor(diff)}`}>
                            {diff > 0 ? '+' : ''}{diff.toFixed(1)}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
