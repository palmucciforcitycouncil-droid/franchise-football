/**
 * Inline Stat Customizer Component - Enhanced
 * Collapsible panel with presets, quick actions, and multi-select
 */

import { useState, useMemo, useEffect } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import { Search, GripVertical, X, ChevronDown, ChevronRight, Sparkles, Zap, List, LayoutList } from 'lucide-react';
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
  group?: string;
}

export interface SelectedStat extends StatItem {
  categoryLabel: string;
  subcategoryLabel: string;
}

interface InlineStatCustomizerProps {
  type: StatsType;
  categories: StatCategory[];
  selectedStats: SelectedStat[];
  onApply: (stats: SelectedStat[]) => void;
  isOpen: boolean;
  onToggle: () => void;
}

// Preset Templates
interface PresetTemplate {
  id: string;
  label: string;
  icon: any;
  description: string;
  statIds: string[];
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

export function InlineStatCustomizer({
  type,
  categories,
  selectedStats,
  onApply,
  isOpen,
  onToggle,
}: InlineStatCustomizerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>(
    categories[0]?.subcategories?.[0]?.id || categories[0]?.id || ''
  );
  const [localSelectedStats, setLocalSelectedStats] = useState<SelectedStat[]>(selectedStats);
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Update local stats when selectedStats prop changes
  useEffect(() => {
    setLocalSelectedStats(selectedStats);
  }, [selectedStats]);

  // Define presets based on type
  const presets: PresetTemplate[] = useMemo(() => {
    if (type === 'player') {
      return [
        {
          id: 'essential',
          label: 'Essential',
          icon: Zap,
          description: 'Core identity + key stats',
          statIds: ['player_name', 'player_pos', 'player_team', 'player_age', 'games_played', 'pass_yds', 'rb_rush_yds', 'rec_yds', 'tackles_combined'],
        },
        {
          id: 'passing',
          label: 'QB Stats',
          icon: List,
          description: 'Complete passing statistics',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'pass_att', 'pass_cmp', 'qb_cmp_pct', 'pass_yds', 'pass_td', 'pass_int'],
        },
        {
          id: 'rushing',
          label: 'RB Stats',
          icon: List,
          description: 'Complete rushing statistics',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'rb_rush_att', 'rb_rush_yds', 'rb_rush_td', 'receptions', 'rec_yds', 'rec_td'],
        },
        {
          id: 'receiving',
          label: 'WR/TE Stats',
          icon: List,
          description: 'Complete receiving statistics',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'targets', 'receptions', 'rec_yds', 'rec_td'],
        },
        {
          id: 'defense',
          label: 'Defense Stats',
          icon: List,
          description: 'Complete defensive statistics',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'tackles_combined', 'sacks', 'interceptions'],
        },
      ];
    } else if (type === 'team') {
      return [
        {
          id: 'essential',
          label: 'Essential',
          icon: Zap,
          description: 'Core team info + record',
          statIds: ['team_name', 'conference', 'division', 'wins', 'losses', 'points_for', 'points_against'],
        },
        {
          id: 'full',
          label: 'Full Stats',
          icon: LayoutList,
          description: 'All team statistics',
          statIds: ['team_name', 'conference', 'division', 'wins', 'losses', 'ties', 'points_for', 'points_against', 'off_yds', 'team_pass_yds', 'team_rush_yds'],
        },
      ];
    } else {
      return [
        {
          id: 'essential',
          label: 'Essential',
          icon: Zap,
          description: 'Core coach info',
          statIds: ['coach_name', 'coach_role', 'coach_team', 'coach_age'],
        },
        {
          id: 'full',
          label: 'Full Stats',
          icon: LayoutList,
          description: 'All coach statistics',
          statIds: ['coach_name', 'coach_role', 'coach_team', 'coach_age', 'hc_wins', 'hc_losses', 'playoff_app'],
        },
      ];
    }
  }, [type]);

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

  // Get all stats from current subcategory
  const currentSubcategoryStats = useMemo(() => {
    return selectedItem?.subcategory?.stats || [];
  }, [selectedItem]);

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

  // Get all stat items from all categories for preset application
  const allStats = useMemo(() => {
    const stats: StatItem[] = [];
    categories.forEach(cat => {
      if (cat.subcategories) {
        cat.subcategories.forEach(sub => {
          sub.stats.forEach(stat => {
            stats.push(stat);
          });
        });
      }
    });
    return stats;
  }, [categories]);

  const handleStatToggle = (stat: StatItem, event?: React.MouseEvent) => {
    const currentStats = currentSubcategoryStats;
    const currentIndex = currentStats.findIndex(s => s.id === stat.id);

    // Multi-select with Shift+Click
    if (event?.shiftKey && lastSelectedIndex !== null && currentIndex !== -1) {
      const start = Math.min(lastSelectedIndex, currentIndex);
      const end = Math.max(lastSelectedIndex, currentIndex);
      const statsToToggle = currentStats.slice(start, end + 1);
      
      const categoryLabel = selectedItem?.category.label || '';
      const subcategoryLabel = selectedItem?.subcategory?.label || '';
      
      setLocalSelectedStats(prev => {
        const newStats = [...prev];
        statsToToggle.forEach(s => {
          if (!newStats.some(existing => existing.id === s.id)) {
            newStats.push({ ...s, categoryLabel, subcategoryLabel });
          }
        });
        return newStats;
      });
    } 
    // Multi-select with Cmd/Ctrl+Click or regular click
    else {
      setLocalSelectedStats(prev => {
        const isSelected = prev.some(s => s.id === stat.id);
        
        if (isSelected) {
          return prev.filter(s => s.id !== stat.id);
        } else {
          if (prev.some(s => s.id === stat.id)) {
            return prev;
          }
          const categoryLabel = selectedItem?.category.label || '';
          const subcategoryLabel = selectedItem?.subcategory?.label || '';
          return [...prev, { ...stat, categoryLabel, subcategoryLabel }];
        }
      });
    }

    if (currentIndex !== -1) {
      setLastSelectedIndex(currentIndex);
    }
  };

  const handleSelectAll = () => {
    if (!selectedItem?.subcategory) return;
    
    const categoryLabel = selectedItem.category.label;
    const subcategoryLabel = selectedItem.subcategory.label;
    
    setLocalSelectedStats(prev => {
      const newStats = [...prev];
      selectedItem.subcategory.stats.forEach(stat => {
        if (!newStats.some(s => s.id === stat.id)) {
          newStats.push({ ...stat, categoryLabel, subcategoryLabel });
        }
      });
      return newStats;
    });
  };

  const handleClearAll = () => {
    if (!selectedItem?.subcategory) return;
    
    const subcategoryStatIds = selectedItem.subcategory.stats.map(s => s.id);
    setLocalSelectedStats(prev => prev.filter(s => !subcategoryStatIds.includes(s.id)));
  };

  const handlePreset = (preset: PresetTemplate) => {
    const presetStats: SelectedStat[] = [];
    
    preset.statIds.forEach(statId => {
      const stat = allStats.find(s => s.id === statId);
      if (stat) {
        // Find category and subcategory for this stat
        let categoryLabel = '';
        let subcategoryLabel = '';
        
        for (const cat of categories) {
          if (cat.subcategories) {
            for (const sub of cat.subcategories) {
              if (sub.stats.some(s => s.id === statId)) {
                categoryLabel = cat.label;
                subcategoryLabel = sub.label;
                break;
              }
            }
          }
          if (categoryLabel) break;
        }
        
        presetStats.push({ ...stat, categoryLabel, subcategoryLabel });
      }
    });
    
    setLocalSelectedStats(presetStats);
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
    onApply(localSelectedStats);
    onToggle();
  };

  const handleCancel = () => {
    setLocalSelectedStats(selectedStats);
    onToggle();
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

  // Count selected in current category
  const selectedInCategory = useMemo(() => {
    if (!selectedItem?.subcategory) return 0;
    return localSelectedStats.filter(s => 
      selectedItem.subcategory!.stats.some(stat => stat.id === s.id)
    ).length;
  }, [localSelectedStats, selectedItem]);

  if (!isOpen) return null;

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] mb-6">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex items-center justify-between">
        <div>
          <h3 className="text-white">Customize {type.charAt(0).toUpperCase() + type.slice(1)} Stats</h3>
          <p className="text-xs text-[#94a3b8] mt-1">
            Use presets, select/deselect stats, and drag to reorder columns
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggle}
          className="text-[#94a3b8] hover:text-white"
        >
          <ChevronDown className="h-5 w-5" />
        </Button>
      </div>

      {/* Preset Templates Bar */}
      <div className="p-4 border-b border-[#2d4a6f] bg-[#0a1929]">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="h-4 w-4 text-[#d4af37]" />
          <span className="text-sm text-white">Quick Presets</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {presets.map(preset => {
            const Icon = preset.icon;
            return (
              <Button
                key={preset.id}
                onClick={() => handlePreset(preset)}
                variant="outline"
                size="sm"
                className="bg-[#1a2332] border-[#2d4a6f] text-white hover:bg-[#2d4a6f] hover:border-[#d4af37]"
                title={preset.description}
              >
                <Icon className="h-3.5 w-3.5 mr-1.5" />
                {preset.label}
              </Button>
            );
          })}
          <Button
            onClick={() => setLocalSelectedStats([])}
            variant="outline"
            size="sm"
            className="bg-[#1a2332] border-[#2d4a6f] text-red-400 hover:bg-red-400/10 hover:border-red-400"
          >
            <X className="h-3.5 w-3.5 mr-1.5" />
            Clear All Stats
          </Button>
        </div>
        <p className="text-xs text-[#94a3b8] mt-2">
          💡 Tip: Hold <kbd className="px-1 py-0.5 bg-[#2d4a6f] rounded text-[10px]">Shift</kbd> to select multiple stats in a row, or <kbd className="px-1 py-0.5 bg-[#2d4a6f] rounded text-[10px]">Ctrl/Cmd</kbd> for individual selections
        </p>
      </div>

      {/* Three Column Layout */}
      <div className="grid grid-cols-[280px_1fr_320px] gap-0 h-[500px]">
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
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-white">
                {selectedItem?.subcategory?.label || selectedItem?.category.label || 'Select a category'}
              </h4>
              <div className="flex gap-2">
                <Button
                  onClick={handleSelectAll}
                  size="sm"
                  variant="outline"
                  className="bg-[#0a1929] border-[#2d4a6f] text-white hover:bg-[#2d4a6f] text-xs"
                  disabled={!selectedItem?.subcategory}
                >
                  Select All
                </Button>
                <Button
                  onClick={handleClearAll}
                  size="sm"
                  variant="outline"
                  className="bg-[#0a1929] border-[#2d4a6f] text-white hover:bg-red-400/10 text-xs"
                  disabled={!selectedItem?.subcategory || selectedInCategory === 0}
                >
                  Clear All
                </Button>
              </div>
            </div>
            <p className="text-xs text-[#94a3b8]">
              {selectedInCategory} of {currentSubcategoryStats.length} selected
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
                        onClick={(e) => handleStatToggle(stat, e)}
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
            <h4 className="text-white">Selected Stats</h4>
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
      <div className="p-4 border-t border-[#2d4a6f] flex items-center justify-end gap-3">
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
          Apply Changes
        </Button>
      </div>
    </div>
  );
}
