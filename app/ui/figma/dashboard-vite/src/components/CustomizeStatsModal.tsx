// components/CustomizeStatsModal.tsx
import React, { useState, useMemo } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Checkbox } from './ui/checkbox';
import { X, GripVertical, Search } from 'lucide-react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';

interface StatItem {
  id: string;
  name: string;
  description: string;
  category: string;
  subcategory?: string;
}

interface CustomizeStatsModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: 'team' | 'player' | 'coach';
  selectedStats: string[];
  onStatsChange: (stats: string[]) => void;
}

export function CustomizeStatsModal({
  isOpen,
  onClose,
  activeTab,
  selectedStats,
  onStatsChange
}: CustomizeStatsModalProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('qb-passing');
  const [localSelectedStats, setLocalSelectedStats] = useState<string[]>(selectedStats);

  // Mock data for different tabs
  const statsData = useMemo(() => {
    if (activeTab === 'player') {
      return {
        categories: [
          {
            id: 'core-identity',
            name: 'Core Identity & Participation',
            subcategories: [
              { id: 'qb-passing', name: 'QB — passing' },
              { id: 'qb-rushing', name: 'QB — rushing/scramble' },
              { id: 'rb-rushing', name: 'RB — rushing' },
              { id: 'wr-receiving', name: 'WR — receiving' },
              { id: 'te-receiving', name: 'TE — receiving' },
              { id: 'ol-blocking', name: 'OL — blocking' },
            ]
          },
          {
            id: 'defense',
            name: 'Defense',
            subcategories: [
              { id: 'coverage', name: 'Coverage (DB/LB)' },
              { id: 'pass-rush', name: 'Pass Rush (DL/LB)' },
              { id: 'run-defense', name: 'Run Defense (DL/LB)' },
            ]
          },
          {
            id: 'special-teams',
            name: 'Special Teams',
            subcategories: [
              { id: 'kicking', name: 'Kicking (K)' },
              { id: 'punting', name: 'Punting (P)' },
              { id: 'returns', name: 'Returns (KR/PR)' },
            ]
          },
          {
            id: 'advanced',
            name: 'Advanced Metrics',
            subcategories: [
              { id: 'situational', name: 'Situational' },
              { id: 'red-zone', name: 'Red Zone' },
              { id: 'third-down', name: 'Third Down' },
            ]
          },
          {
            id: 'team-context',
            name: 'Team Context',
            subcategories: [
              { id: 'snap-counts', name: 'Snap Counts' },
              { id: 'usage-rates', name: 'Usage Rates' },
            ]
          }
        ],
        stats: [
          // QB Passing Stats
          { id: 'qb_pass_att', name: 'qb_pass_att', description: 'Pass Attempts', category: 'qb-passing' },
          { id: 'qb_pass_cmp', name: 'qb_pass_cmp', description: 'Completions', category: 'qb-passing' },
          { id: 'qb_pass_yds', name: 'qb_pass_yds', description: 'Pass Yards', category: 'qb-passing' },
          { id: 'qb_pass_td', name: 'qb_pass_td', description: 'Pass TDs', category: 'qb-passing' },
          { id: 'qb_pass_int', name: 'qb_pass_int', description: 'Interceptions', category: 'qb-passing' },
          { id: 'qb_sacks_taken', name: 'qb_sacks_taken', description: 'Sacks Taken', category: 'qb-passing' },
          { id: 'qb_cmp_pct', name: 'qb_cmp_pct', description: 'Completion Percentage', category: 'qb-passing' },
          { id: 'qb_pass_rtg', name: 'qb_pass_rtg', description: 'Passer Rating', category: 'qb-passing' },
          { id: 'qb_yds_att', name: 'qb_yds_att', description: 'Yards per Attempt', category: 'qb-passing' },
          { id: 'qb_td_pct', name: 'qb_td_pct', description: 'TD Percentage', category: 'qb-passing' },
          { id: 'qb_int_pct', name: 'qb_int_pct', description: 'INT Percentage', category: 'qb-passing' },
          
          // QB Rushing Stats
          { id: 'qb_rush_att', name: 'qb_rush_att', description: 'Rush Attempts', category: 'qb-rushing' },
          { id: 'qb_rush_yds', name: 'qb_rush_yds', description: 'Rush Yards', category: 'qb-rushing' },
          { id: 'qb_rush_td', name: 'qb_rush_td', description: 'Rush TDs', category: 'qb-rushing' },
          
          // RB Rushing Stats
          { id: 'rb_rush_att', name: 'rb_rush_att', description: 'Rush Attempts', category: 'rb-rushing' },
          { id: 'rb_rush_yds', name: 'rb_rush_yds', description: 'Rush Yards', category: 'rb-rushing' },
          { id: 'rb_rush_td', name: 'rb_rush_td', description: 'Rush TDs', category: 'rb-rushing' },
          { id: 'rb_yds_rush', name: 'rb_yds_rush', description: 'Yards per Rush', category: 'rb-rushing' },
          
          // WR Receiving Stats
          { id: 'wr_rec', name: 'wr_rec', description: 'Receptions', category: 'wr-receiving' },
          { id: 'wr_rec_yds', name: 'wr_rec_yds', description: 'Receiving Yards', category: 'wr-receiving' },
          { id: 'wr_rec_td', name: 'wr_rec_td', description: 'Receiving TDs', category: 'wr-receiving' },
          { id: 'wr_yds_rec', name: 'wr_yds_rec', description: 'Yards per Reception', category: 'wr-receiving' },
          
          // Defense Stats
          { id: 'def_tackles', name: 'def_tackles', description: 'Tackles', category: 'coverage' },
          { id: 'def_sacks', name: 'def_sacks', description: 'Sacks', category: 'pass-rush' },
          { id: 'def_ints', name: 'def_ints', description: 'Interceptions', category: 'coverage' },
          { id: 'def_pbu', name: 'def_pbu', description: 'Pass Breakups', category: 'coverage' },
          
          // Core Identity Stats
          { id: 'player_name', name: 'player_name', description: 'Player Name', category: 'core-identity' },
          { id: 'team', name: 'team', description: 'Team', category: 'core-identity' },
          { id: 'position', name: 'position', description: 'Position', category: 'core-identity' },
          { id: 'overall', name: 'overall', description: 'Overall Rating', category: 'core-identity' },
        ]
      };
    } else if (activeTab === 'team') {
      return {
        categories: [
          {
            id: 'identity-record',
            name: 'Identity & Record',
            subcategories: [
              { id: 'basic-info', name: 'Basic Info' },
              { id: 'win-loss', name: 'Win/Loss Record' },
              { id: 'division-standing', name: 'Division Standing' },
            ]
          },
          {
            id: 'team-offense',
            name: 'Team Offense',
            subcategories: [
              { id: 'passing-offense', name: 'Passing Offense' },
              { id: 'rushing-offense', name: 'Rushing Offense' },
              { id: 'scoring-offense', name: 'Scoring Offense' },
              { id: 'efficiency-metrics', name: 'Efficiency Metrics' },
            ]
          },
          {
            id: 'team-defense',
            name: 'Team Defense',
            subcategories: [
              { id: 'pass-defense', name: 'Pass Defense' },
              { id: 'run-defense', name: 'Run Defense' },
              { id: 'scoring-defense', name: 'Scoring Defense' },
              { id: 'turnover-defense', name: 'Turnover Defense' },
            ]
          }
        ],
        stats: [
          { id: 'team_name', name: 'team_name', description: 'Team Name', category: 'basic-info' },
          { id: 'wins', name: 'wins', description: 'Wins', category: 'win-loss' },
          { id: 'losses', name: 'losses', description: 'Losses', category: 'win-loss' },
          { id: 'win_pct', name: 'win_pct', description: 'Win Percentage', category: 'win-loss' },
          { id: 'team_pass_yds', name: 'team_pass_yds', description: 'Team Pass Yards', category: 'passing-offense' },
          { id: 'team_rush_yds', name: 'team_rush_yds', description: 'Team Rush Yards', category: 'rushing-offense' },
          { id: 'team_points', name: 'team_points', description: 'Team Points', category: 'scoring-offense' },
        ]
      };
    } else {
      return {
        categories: [
          {
            id: 'coach-identity',
            name: 'Identity & Record',
            subcategories: [
              { id: 'basic-info', name: 'Basic Info' },
              { id: 'career-record', name: 'Career Record' },
              { id: 'current-season', name: 'Current Season' },
            ]
          },
          {
            id: 'coaching-performance',
            name: 'Coaching Performance',
            subcategories: [
              { id: 'win-percentage', name: 'Win Percentage' },
              { id: 'playoff-record', name: 'Playoff Record' },
              { id: 'championship-record', name: 'Championship Record' },
            ]
          }
        ],
        stats: [
          { id: 'coach_name', name: 'coach_name', description: 'Coach Name', category: 'basic-info' },
          { id: 'coach_role', name: 'coach_role', description: 'Role', category: 'basic-info' },
          { id: 'coach_wins', name: 'coach_wins', description: 'Career Wins', category: 'career-record' },
          { id: 'coach_losses', name: 'coach_losses', description: 'Career Losses', category: 'career-record' },
          { id: 'coach_win_pct', name: 'coach_win_pct', description: 'Win Percentage', category: 'win-percentage' },
        ]
      };
    }
  }, [activeTab]);

  const filteredStats = useMemo(() => {
    if (!searchTerm) return statsData.stats;
    
    return statsData.stats.filter(stat => 
      stat.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      stat.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      statsData.categories.some(cat => 
        cat.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        cat.subcategories?.some(sub => 
          sub.name.toLowerCase().includes(searchTerm.toLowerCase())
        )
      )
    );
  }, [statsData, searchTerm]);

  const currentCategoryStats = useMemo(() => {
    return filteredStats.filter(stat => stat.category === selectedCategory);
  }, [filteredStats, selectedCategory]);

  const selectedStatsData = useMemo(() => {
    return localSelectedStats.map(statId => 
      statsData.stats.find(stat => stat.id === statId)
    ).filter(Boolean) as StatItem[];
  }, [localSelectedStats, statsData.stats]);

  const handleStatToggle = (statId: string) => {
    setLocalSelectedStats(prev => 
      prev.includes(statId) 
        ? prev.filter(id => id !== statId)
        : [...prev, statId]
    );
  };

  const handleDragEnd = (result: any) => {
    if (!result.destination) return;
    
    const items = Array.from(localSelectedStats);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);
    
    setLocalSelectedStats(items);
  };

  const handleApply = () => {
    onStatsChange(localSelectedStats);
    onClose();
  };

  const handleCancel = () => {
    setLocalSelectedStats(selectedStats);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-11/12 max-w-7xl h-5/6 flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">Customize Stats</h2>
          <Button variant="ghost" size="sm" onClick={handleCancel}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Column A: Stat Categories */}
          <div className="w-1/3 border-r bg-gray-50 p-4 overflow-y-auto">
            <div className="mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Search all player stats..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              {statsData.categories.map(category => (
                <div key={category.id}>
                  <div className="font-medium text-gray-700 mb-2">{category.name}</div>
                  <div className="space-y-1 ml-2">
                    {category.subcategories?.map(subcategory => (
                      <button
                        key={subcategory.id}
                        onClick={() => setSelectedCategory(subcategory.id)}
                        className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                          selectedCategory === subcategory.id
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        {subcategory.name}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Column B: Stat List */}
          <div className="w-1/3 border-r p-4 overflow-y-auto">
            <div className="mb-4">
              <h3 className="font-medium text-gray-900">
                {statsData.categories
                  .flatMap(cat => cat.subcategories || [])
                  .find(sub => sub.id === selectedCategory)?.name || 'Select a category'}
              </h3>
            </div>
            
            <div className="space-y-3">
              {/* Group stats by type if applicable */}
              {currentCategoryStats.length > 0 && (
                <>
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-gray-600">Base Stats:</h4>
                    {currentCategoryStats.filter(stat => !stat.name.includes('_pct') && !stat.name.includes('_rtg')).map(stat => (
                      <div key={stat.id} className="flex items-center space-x-3">
                        <Checkbox
                          checked={localSelectedStats.includes(stat.id)}
                          onCheckedChange={() => handleStatToggle(stat.id)}
                        />
                        <div className="flex-1">
                          <div className="font-mono text-sm text-gray-900">{stat.name}</div>
                          <div className="text-xs text-gray-500">{stat.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {currentCategoryStats.some(stat => stat.name.includes('_pct') || stat.name.includes('_rtg')) && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-gray-600">Derived Stats:</h4>
                      {currentCategoryStats.filter(stat => stat.name.includes('_pct') || stat.name.includes('_rtg')).map(stat => (
                        <div key={stat.id} className="flex items-center space-x-3">
                          <Checkbox
                            checked={localSelectedStats.includes(stat.id)}
                            onCheckedChange={() => handleStatToggle(stat.id)}
                          />
                          <div className="flex-1">
                            <div className="font-mono text-sm text-gray-900">{stat.name}</div>
                            <div className="text-xs text-gray-500">{stat.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Column C: Selected Stats & Reorder */}
          <div className="w-1/3 p-4 overflow-y-auto">
            <div className="mb-4">
              <h3 className="font-medium text-gray-900">Selected Stats</h3>
              <p className="text-sm text-gray-500">Drag and drop to reorder columns in the main table.</p>
            </div>
            
            <DragDropContext onDragEnd={handleDragEnd}>
              <Droppable droppableId="selected-stats">
                {(provided) => (
                  <div
                    {...provided.droppableProps}
                    ref={provided.innerRef}
                    className="space-y-2"
                  >
                    {selectedStatsData.map((stat, index) => (
                      <Draggable key={stat.id} draggableId={stat.id} index={index}>
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            className={`flex items-center space-x-3 p-2 rounded border ${
                              snapshot.isDragging ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-200'
                            }`}
                          >
                            <div {...provided.dragHandleProps} className="text-gray-400">
                              <GripVertical className="w-4 h-4" />
                            </div>
                            <div className="flex-1">
                              <div className="font-mono text-sm text-gray-900">{stat.name}</div>
                              <div className="text-xs text-gray-500">{stat.description}</div>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleStatToggle(stat.id)}
                              className="text-gray-400 hover:text-red-500"
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </DragDropContext>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button onClick={handleApply}>
            Apply
          </Button>
        </div>
      </div>
    </div>
  );
}
