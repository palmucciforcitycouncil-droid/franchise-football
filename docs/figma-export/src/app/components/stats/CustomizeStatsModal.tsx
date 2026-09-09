/**
 * Customize Stats Modal Component
 * Three-column modal for selecting and reordering stats
 */

import { useState, useMemo, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import { Search, GripVertical, X } from 'lucide-react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export type StatsType = 'player' | 'team' | 'coach';

export interface StatCategory {
  id: string;
  label: string;
  subcategories?: StatSubcategory[];
}

export interface StatSubcategory {
  id: string;
  label: string;
  stats: StatItem[];
}

export interface StatItem {
  id: string;
  variable: string;
  label: string;
  group?: string; // For grouping within subcategory (e.g., "Base", "Derived")
}

export interface SelectedStat extends StatItem {
  categoryLabel: string;
  subcategoryLabel: string;
}

interface CustomizeStatsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: StatsType;
  categories: StatCategory[];
  selectedStats: SelectedStat[];
  onApply: (stats: SelectedStat[]) => void;
}

function SortableStatItem({ stat, onRemove }: { stat: SelectedStat; onRemove: () => void }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: stat.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 p-2 bg-[#0a1929] border border-[#2d4a6f] rounded group hover:bg-[#2d4a6f]/30"
    >
      <div
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-[#94a3b8] hover:text-white"
      >
        <GripVertical className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-white truncate">{stat.variable}</div>
        <div className="text-xs text-[#94a3b8] truncate">{stat.label}</div>
      </div>
      <button
        onClick={onRemove}
        className="opacity-0 group-hover:opacity-100 text-[#94a3b8] hover:text-red-400 transition-opacity"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function CustomizeStatsModal({
  open,
  onOpenChange,
  type,
  categories,
  selectedStats,
  onApply,
}: CustomizeStatsModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>(
    categories[0]?.subcategories?.[0]?.id || categories[0]?.id || ''
  );
  
  // Helper function to deduplicate stats
  const deduplicateStats = (stats: SelectedStat[]): SelectedStat[] => {
    const seen = new Set<string>();
    return stats.filter(stat => {
      if (seen.has(stat.id)) {
        console.warn(`Duplicate stat ID detected and removed: ${stat.id}`);
        return false;
      }
      seen.add(stat.id);
      return true;
    });
  };

  const [localSelectedStats, setLocalSelectedStats] = useState<SelectedStat[]>([]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Reset local stats when modal opens
  useEffect(() => {
    if (open) {
      setLocalSelectedStats(deduplicateStats(selectedStats));
      setSearchQuery('');
    }
  }, [open]);

  // Find selected category/subcategory
  const selectedItem = useMemo(() => {
    for (const category of categories) {
      if (category.subcategories) {
        const subcategory = category.subcategories.find(sub => sub.id === selectedCategoryId);
        if (subcategory) {
          return { category, subcategory };
        }
      } else if (category.id === selectedCategoryId) {
        return { category, subcategory: null };
      }
    }
    return null;
  }, [categories, selectedCategoryId]);

  // Filter stats based on search
  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) return categories;

    const query = searchQuery.toLowerCase();
    return categories.map(cat => {
      if (cat.subcategories) {
        const filteredSubs = cat.subcategories
          .map(sub => ({
            ...sub,
            stats: sub.stats.filter(stat =>
              stat.variable.toLowerCase().includes(query) ||
              stat.label.toLowerCase().includes(query)
            ),
          }))
          .filter(sub => sub.stats.length > 0);
        
        if (filteredSubs.length > 0) {
          return { ...cat, subcategories: filteredSubs };
        }
      }
      return null;
    }).filter(Boolean) as StatCategory[];
  }, [categories, searchQuery]);

  const handleStatToggle = (stat: StatItem) => {
    setLocalSelectedStats(prev => {
      const isSelected = prev.some(s => s.id === stat.id);
      
      if (isSelected) {
        return prev.filter(s => s.id !== stat.id);
      } else {
        // Add the stat only if it doesn't already exist
        if (prev.some(s => s.id === stat.id)) {
          console.warn(`Attempted to add duplicate stat: ${stat.id}`);
          return prev;
        }
        const categoryLabel = selectedItem?.category.label || '';
        const subcategoryLabel = selectedItem?.subcategory?.label || '';
        return [...prev, { ...stat, categoryLabel, subcategoryLabel }];
      }
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id) {
      setLocalSelectedStats(items => {
        const oldIndex = items.findIndex(item => item.id === active.id);
        const newIndex = items.findIndex(item => item.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const handleApply = () => {
    // Apply deduplicated stats
    onApply(deduplicateStats(localSelectedStats));
    onOpenChange(false);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  // Group stats if they have a group property
  const groupedStats = useMemo(() => {
    if (!selectedItem?.subcategory) return null;
    
    const stats = selectedItem.subcategory.stats;
    const groups = new Map<string, StatItem[]>();
    
    stats.forEach(stat => {
      const group = stat.group || 'default';
      if (!groups.has(group)) {
        groups.set(group, []);
      }
      groups.get(group)!.push(stat);
    });
    
    return groups;
  }, [selectedItem]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!max-w-[95vw] w-[1600px] h-[85vh] max-h-[900px] bg-[#1a2332] border-[#2d4a6f] text-white p-0 flex flex-col gap-0">
        <DialogHeader className="p-6 border-b border-[#2d4a6f] shrink-0">
          <DialogTitle>Customize {type.charAt(0).toUpperCase() + type.slice(1)} Stats</DialogTitle>
          <DialogDescription className="text-[#94a3b8]">
            Select and reorder the statistics columns that will be displayed in your {type} stats table.
          </DialogDescription>
        </DialogHeader>

        {/* Three Column Layout */}
        <div className="flex-1 grid grid-cols-[280px_1fr_320px] gap-0 overflow-hidden min-h-0">
          {/* Column A: Categories */}
          <div className="border-r border-[#2d4a6f] flex flex-col">
            <div className="p-4 border-b border-[#2d4a6f]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#94a3b8]" />
                <Input
                  type="text"
                  placeholder={`Search all ${type} stats...`}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-[#0a1929] border-[#2d4a6f] text-white placeholder:text-[#94a3b8]"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {filteredCategories.map(category => (
                <div key={category.id} className="mb-2">
                  {category.subcategories ? (
                    <>
                      <div className="px-3 py-2 text-sm text-[#d4af37]">
                        {category.label}
                      </div>
                      {category.subcategories.map(sub => (
                        <button
                          key={sub.id}
                          onClick={() => setSelectedCategoryId(sub.id)}
                          className={`w-full text-left px-3 py-2 text-sm rounded transition-colors ${
                            selectedCategoryId === sub.id
                              ? 'bg-[#2d4a6f] text-white'
                              : 'text-[#94a3b8] hover:bg-[#0a1929] hover:text-white'
                          }`}
                        >
                          {sub.label}
                        </button>
                      ))}
                    </>
                  ) : (
                    <button
                      onClick={() => setSelectedCategoryId(category.id)}
                      className={`w-full text-left px-3 py-2 text-sm rounded transition-colors ${
                        selectedCategoryId === category.id
                          ? 'bg-[#2d4a6f] text-white'
                          : 'text-[#94a3b8] hover:bg-[#0a1929] hover:text-white'
                      }`}
                    >
                      {category.label}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Column B: Stat List */}
          <div className="flex flex-col border-r border-[#2d4a6f]">
            <div className="p-4 border-b border-[#2d4a6f]">
              <h3 className="text-white">
                {selectedItem?.subcategory?.label || selectedItem?.category.label || 'Select a category'}
              </h3>
              <p className="text-xs text-[#94a3b8] mt-1">
                {localSelectedStats.filter(s => 
                  selectedItem?.subcategory?.stats.some(stat => stat.id === s.id)
                ).length} selected
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {groupedStats ? (
                Array.from(groupedStats.entries()).map(([groupName, stats]) => (
                  <div key={groupName} className="mb-4">
                    {groupName !== 'default' && (
                      <div className="text-xs text-[#d4af37] mb-2 uppercase tracking-wide">
                        {groupName}
                      </div>
                    )}
                    <div className="space-y-2">
                      {stats.map(stat => (
                        <div
                          key={stat.id}
                          className="flex items-start gap-3 p-2 rounded hover:bg-[#0a1929] cursor-pointer"
                          onClick={() => handleStatToggle(stat)}
                        >
                          <Checkbox
                            checked={localSelectedStats.some(s => s.id === stat.id)}
                            onCheckedChange={() => handleStatToggle(stat)}
                            className="mt-0.5"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm text-white">{stat.variable}</div>
                            <div className="text-xs text-[#94a3b8]">{stat.label}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-[#94a3b8] py-8">
                  Select a category to view stats
                </div>
              )}
            </div>
          </div>

          {/* Column C: Selected Stats */}
          <div className="flex flex-col">
            <div className="p-4 border-b border-[#2d4a6f]">
              <h3 className="text-white">Selected Stats</h3>
              <p className="text-xs text-[#94a3b8] mt-1">
                Drag and drop to reorder columns
              </p>
              <div className="text-xs text-[#d4af37] mt-2">
                {localSelectedStats.length} column{localSelectedStats.length !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {localSelectedStats.length > 0 ? (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={localSelectedStats.map(s => s.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    <div className="space-y-2">
                      {localSelectedStats.map(stat => (
                        <SortableStatItem
                          key={stat.id}
                          stat={stat}
                          onRemove={() => setLocalSelectedStats(prev => prev.filter(s => s.id !== stat.id))}
                        />
                      ))}
                    </div>
                  </SortableContext>
                </DndContext>
              ) : (
                <div className="text-center text-[#94a3b8] py-8 text-sm">
                  No stats selected.<br />Check stats from the middle column.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[#2d4a6f] flex items-center justify-end gap-3 shrink-0">
          <Button
            variant="outline"
            onClick={handleCancel}
            className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]/30"
          >
            Cancel
          </Button>
          <Button
            onClick={handleApply}
            className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
          >
            Apply
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
