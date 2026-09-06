/**
 * Stat Column Chooser - Football Mogul Style
 * Simple clickable list with preset buttons
 */

import { useState, useMemo, useEffect } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Search, X } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';

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

interface StatColumnChooserProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: StatsType;
  categories: StatCategory[];
  selectedStats: SelectedStat[];
  onApply: (stats: SelectedStat[]) => void;
}

interface PresetGroup {
  id: string;
  label: string;
  statIds: string[];
}

export function StatColumnChooser({
  open,
  onOpenChange,
  type,
  categories,
  selectedStats,
  onApply,
}: StatColumnChooserProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [localSelectedIds, setLocalSelectedIds] = useState<Set<string>>(
    new Set(selectedStats.map(s => s.id))
  );

  // Update local selection when selectedStats prop changes
  useEffect(() => {
    setLocalSelectedIds(new Set(selectedStats.map(s => s.id)));
  }, [selectedStats, open]);

  // Flatten all stats with their category info
  const allStatsFlat = useMemo(() => {
    const stats: Array<StatItem & { categoryLabel: string; subcategoryLabel: string }> = [];
    
    categories.forEach(cat => {
      if (cat.subcategories) {
        cat.subcategories.forEach(sub => {
          sub.stats.forEach(stat => {
            stats.push({
              ...stat,
              categoryLabel: cat.label,
              subcategoryLabel: sub.label,
            });
          });
        });
      }
    });
    
    return stats;
  }, [categories]);

  // Filter stats based on search
  const filteredStats = useMemo(() => {
    if (!searchQuery.trim()) return allStatsFlat;
    
    const query = searchQuery.toLowerCase();
    return allStatsFlat.filter(stat =>
      stat.variable.toLowerCase().includes(query) ||
      stat.label.toLowerCase().includes(query) ||
      stat.categoryLabel.toLowerCase().includes(query) ||
      stat.subcategoryLabel.toLowerCase().includes(query)
    );
  }, [allStatsFlat, searchQuery]);

  // Define preset groups based on type
  const presetGroups: PresetGroup[] = useMemo(() => {
    // Get all stat IDs for the "All" preset
    const allStatIds = allStatsFlat.map(stat => stat.id);
    
    if (type === 'player') {
      return [
        {
          id: 'default',
          label: 'Default Stats',
          statIds: ['player_name', 'player_pos', 'player_team', 'player_age', 'games_played'],
        },
        {
          id: 'qb_stats',
          label: 'Quarterback Stats',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'pass_att', 'pass_cmp', 'qb_cmp_pct', 'pass_yds', 'pass_td', 'pass_int', 'qb_rating'],
        },
        {
          id: 'skill_stats',
          label: 'Skill Position Stats',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'rb_rush_att', 'rb_rush_yds', 'rb_rush_td', 'targets', 'receptions', 'rec_yds', 'rec_td'],
        },
        {
          id: 'rushing',
          label: 'Rushing Stats',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'rb_rush_att', 'rb_rush_yds', 'rb_yds_per_rush', 'rb_rush_td'],
        },
        {
          id: 'receiving',
          label: 'Receiving Stats',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'targets', 'receptions', 'rec_yds', 'rec_td', 'catch_pct'],
        },
        {
          id: 'defensive',
          label: 'Defensive Stats',
          statIds: ['player_name', 'player_pos', 'player_team', 'games_played', 'tackles_combined', 'sacks', 'interceptions', 'pass_breakups'],
        },
        {
          id: 'all',
          label: 'All Stats',
          statIds: allStatIds,
        },
      ];
    } else if (type === 'team') {
      return [
        {
          id: 'default',
          label: 'Team Overview',
          statIds: ['team_name', 'conference', 'division', 'wins', 'losses', 'win_pct'],
        },
        {
          id: 'full_record',
          label: 'Full Record',
          statIds: ['team_name', 'wins', 'losses', 'ties', 'win_pct', 'points_for', 'points_against', 'point_diff'],
        },
        {
          id: 'offensive',
          label: 'Offensive Stats',
          statIds: ['team_name', 'wins', 'losses', 'points_for', 'off_yds', 'off_yds_per_play', 'team_pass_yds', 'team_rush_yds'],
        },
        {
          id: 'defensive',
          label: 'Defensive Stats',
          statIds: ['team_name', 'wins', 'losses', 'def_points_allowed', 'def_yds_allowed', 'def_yds_per_play', 'team_sacks', 'def_turnovers_forced'],
        },
        {
          id: 'complete',
          label: 'Complete Team Stats',
          statIds: ['team_name', 'wins', 'losses', 'points_for', 'points_against', 'off_yds', 'def_yds_allowed', 'team_pass_yds', 'team_rush_yds', 'team_sacks', 'off_turnovers', 'def_turnovers_forced'],
        },
        {
          id: 'all',
          label: 'All Stats',
          statIds: allStatIds,
        },
      ];
    } else {
      return [
        {
          id: 'default',
          label: 'Coach Overview',
          statIds: ['coach_name', 'coach_role', 'coach_team', 'coach_age', 'coach_exp'],
        },
        {
          id: 'hc_record',
          label: 'Head Coach Record',
          statIds: ['coach_name', 'coach_role', 'coach_team', 'coach_age', 'hc_wins', 'hc_losses', 'hc_win_pct', 'playoff_app'],
        },
        {
          id: 'hc_complete',
          label: 'Complete HC Stats',
          statIds: ['coach_name', 'coach_team', 'coach_age', 'hc_wins', 'hc_losses', 'hc_win_pct', 'playoff_app', 'playoff_wins', 'super_bowls'],
        },
        {
          id: 'performance',
          label: 'Performance Metrics',
          statIds: ['coach_name', 'coach_role', 'coach_team', 'avg_points_scored', 'avg_points_allowed', 'turnover_diff', 'avg_yards_per_game'],
        },
        {
          id: 'all',
          label: 'All Stats',
          statIds: allStatIds,
        },
      ];
    }
  }, [type, allStatsFlat]);

  const handleStatToggle = (stat: StatItem & { categoryLabel: string; subcategoryLabel: string }) => {
    setLocalSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stat.id)) {
        newSet.delete(stat.id);
      } else {
        newSet.add(stat.id);
      }
      return newSet;
    });
  };

  const handlePresetClick = (preset: PresetGroup) => {
    setLocalSelectedIds(new Set(preset.statIds));
  };

  const handleClearAll = () => {
    setLocalSelectedIds(new Set());
  };

  const handleDone = () => {
    // Convert selected IDs back to SelectedStat objects
    const selectedStatsArray: SelectedStat[] = [];
    
    allStatsFlat.forEach(stat => {
      if (localSelectedIds.has(stat.id)) {
        selectedStatsArray.push({
          id: stat.id,
          variable: stat.variable,
          label: stat.label,
          group: stat.group,
          categoryLabel: stat.categoryLabel,
          subcategoryLabel: stat.subcategoryLabel,
        });
      }
    });
    
    onApply(selectedStatsArray);
    onOpenChange(false);
  };

  const handleCancel = () => {
    setLocalSelectedIds(new Set(selectedStats.map(s => s.id)));
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!max-w-[900px] !max-h-[85vh] bg-[#1a2332] border-[#2d4a6f] text-white p-0 flex flex-col">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-[#2d4a6f] flex-shrink-0">
          <DialogTitle className="text-white">
            Stat Column Chooser - {type.charAt(0).toUpperCase() + type.slice(1)}
          </DialogTitle>
          <DialogDescription className="text-[#94a3b8]">
            Click stats in the list to toggle each one on and off
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-[1fr_280px] flex-1 min-h-0 overflow-hidden">
          {/* Left: Stats List */}
          <div className="flex flex-col border-r border-[#2d4a6f] min-h-0">
            {/* Search */}
            <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#94a3b8]" />
                <Input
                  type="text"
                  placeholder={`Search ${type} stats...`}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-[#0a1929] border-[#2d4a6f] text-white placeholder:text-[#94a3b8]"
                />
              </div>
              <div className="text-xs text-[#94a3b8] mt-2">
                {localSelectedIds.size} stat{localSelectedIds.size !== 1 ? 's' : ''} selected
              </div>
            </div>

            {/* Stats List */}
            <div className="flex-1 overflow-y-auto min-h-0">
              <div className="p-2">
                {filteredStats.map((stat, index) => {
                  const isSelected = localSelectedIds.has(stat.id);
                  return (
                    <button
                      key={stat.id}
                      onClick={() => handleStatToggle(stat)}
                      className={`w-full text-left px-3 py-2 text-sm rounded transition-colors ${
                        isSelected
                          ? 'bg-[#2d4a6f] text-white'
                          : 'text-[#94a3b8] hover:bg-[#0a1929] hover:text-white'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 w-40">
                          <span className={isSelected ? 'text-white' : 'text-[#94a3b8]'}>
                            {stat.variable}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className={isSelected ? 'text-white' : 'text-[#94a3b8]'}>
                            {stat.label}
                          </span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right: Preset Groups */}
          <div className="flex flex-col min-h-0">
            <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
              <h4 className="text-sm text-white mb-1">Quick Presets</h4>
              <p className="text-xs text-[#94a3b8]">
                Click for pre-defined stat groups
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 min-h-0">
              <div className="space-y-2 pb-4">
                {presetGroups.map(preset => (
                  <Button
                    key={preset.id}
                    onClick={() => handlePresetClick(preset)}
                    variant="outline"
                    size="sm"
                    className="w-full justify-start bg-[#0a1929] border-[#2d4a6f] text-white hover:bg-[#2d4a6f] hover:border-[#d4af37]"
                  >
                    {preset.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="p-4 border-t border-[#2d4a6f] flex-shrink-0">
              <Button
                onClick={handleClearAll}
                variant="outline"
                size="sm"
                className="w-full bg-[#0a1929] border-[#2d4a6f] text-red-400 hover:bg-red-400/10 hover:border-red-400"
              >
                <X className="h-4 w-4 mr-2" />
                Clear All Selected Stats
              </Button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#2d4a6f] flex items-center justify-between flex-shrink-0">
          <div className="text-xs text-[#94a3b8]">
            💡 Tip: Click any stat to toggle it on/off
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={handleCancel}
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]/30"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDone}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              Done
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
