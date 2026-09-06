import React, { useState } from 'react';
import { ColDef } from './columnsAttributes';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import { Label } from '../ui/label';
import { Settings, RotateCcw, Lock, Unlock } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../ui/popover';

interface ColumnSettingsProps {
  view: 'attributes' | 'stats';
  columns: ColDef[];
  lockGroups: boolean;
  onResetColumns: () => void;
  onToggleLockGroups: (locked: boolean) => void;
  onReorderColumns: (newOrder: string[]) => void;
}

export function ColumnSettings({
  view,
  columns,
  lockGroups,
  onResetColumns,
  onToggleLockGroups,
  onReorderColumns
}: ColumnSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleReset = () => {
    onResetColumns();
    setIsOpen(false);
  };

  const groupedColumns = columns.reduce((acc, col, index) => {
    const group = col.group || 'Other';
    if (!acc[group]) {
      acc[group] = [];
    }
    acc[group].push({ ...col, originalIndex: index });
    return acc;
  }, {} as Record<string, (ColDef & { originalIndex: number })[]>);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0 text-[#94a3b8] hover:text-white hover:bg-[#2d4a6f]/30"
          title="Column settings"
        >
          <Settings className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 bg-[#1a2332] border-[#2d4a6f] text-white">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium">Column Settings</h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="h-7 px-2 text-xs text-[#94a3b8] hover:text-white"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Reset
            </Button>
          </div>

          {view === 'stats' && (
            <div className="flex items-center space-x-2">
              <Switch
                id="lock-groups"
                checked={lockGroups}
                onCheckedChange={onToggleLockGroups}
                className="data-[state=checked]:bg-[#d4af37]"
              />
              <Label htmlFor="lock-groups" className="text-xs text-[#94a3b8]">
                {lockGroups ? (
                  <>
                    <Lock className="h-3 w-3 inline mr-1" />
                    Lock Groups
                  </>
                ) : (
                  <>
                    <Unlock className="h-3 w-3 inline mr-1" />
                    Free Reorder
                  </>
                )}
              </Label>
            </div>
          )}

          <div className="space-y-2">
            <h5 className="text-xs font-medium text-[#94a3b8]">Current Order:</h5>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {Object.entries(groupedColumns).map(([group, groupColumns]) => (
                <div key={group} className="space-y-1">
                  {group !== 'Other' && group !== 'CORE' && (
                    <div className="text-xs font-medium text-[#d4af37] px-2 py-1 bg-[#2d4a6f]/20 rounded">
                      {group} Group
                    </div>
                  )}
                  {groupColumns.map((col, index) => (
                    <div
                      key={col.key}
                      className="flex items-center justify-between px-2 py-1 text-xs hover:bg-[#2d4a6f]/20 rounded"
                    >
                      <span className={col.fixed ? "text-[#d4af37]" : "text-white"}>
                        {col.label}
                        {col.fixed && " (Fixed)"}
                      </span>
                      <span className="text-[#94a3b8]">
                        {col.originalIndex + 1}
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>

          <div className="text-xs text-[#94a3b8] space-y-1">
            <p>• Drag column headers to reorder</p>
            <p>• Alt + Arrow keys for keyboard navigation</p>
            {view === 'stats' && (
              <p>• {lockGroups ? "Groups move together" : "Free column reordering"}</p>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
