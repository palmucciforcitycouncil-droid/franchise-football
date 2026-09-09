import { useState, useEffect } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Button } from './ui/button';
import { Sparkles } from 'lucide-react';
import { WarningsBar } from './WarningsBar';
import { WarningsModal } from './WarningsModal';

interface Player {
  name: string;
  num: number;
  pos: string;
  ovr: number;
  dep: string;
  age?: number;
  [key: string]: any;
}

interface PositionQuota {
  current: number;
  min: number;
}

interface DepthChartCardsProps {
  players: Player[];
  positionQuotas: Record<string, PositionQuota>;
  depthChartSlots: Record<string, number>;
  onOpenAutoFill: () => void;
  warnings?: string[];
  isAutoFilled?: boolean;
}

const POSITION_LABELS: Record<string, string> = {
  QB: 'QB',
  RB: 'RB',
  WR: 'WR',
  TE: 'TE',
  C: 'C',
  G: 'G',
  T: 'T',
  DE: 'DE',
  DT: 'DT',
  LB: 'LB',
  CB: 'CB',
  S: 'S',
  K: 'K',
  P: 'P',
  KR: 'KR',
  PR: 'PR',
};

// Organize positions for grid layout
const OFFENSE_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT'];

const DEFENSE_POSITIONS = ['LDE', 'DT', 'RDE', 'OLB', 'MLB', 'CB', 'FS', 'SS'];

const SPECIAL_TEAMS_POSITIONS = ['K', 'P', 'KR', 'PR'];

interface PositionColumnProps {
  position: string;
  slots: number;
  players: Player[];
  selectedPlayers: (Player | null)[];
  onSelect: (position: string, slot: number, player: Player | null) => void;
}

function PositionColumn({ position, slots, players, selectedPlayers, onSelect }: PositionColumnProps) {
  // Special handling for KR and PR - show all players ranked by returner rating
  const isReturner = position === 'KR' || position === 'PR';
  
  // Map position names to roster position codes
  const positionMap: Record<string, string[]> = {
    'LT': ['T'],
    'LG': ['G'],
    'C': ['C'],
    'RG': ['G'],
    'RT': ['T'],
    'LDE': ['DE'],
    'DT': ['DT'],
    'RDE': ['DE'],
    'OLB': ['LB'],
    'MLB': ['LB'],
    'FS': ['S'],
    'SS': ['S'],
  };
  
  let eligiblePlayers: Player[] = [];
  
  if (isReturner) {
    // Calculate returner rating: weighted average of SPD (40%), AGI (30%), CTH (20%), AWR (10%)
    const playersWithRating = players.map(p => ({
      ...p,
      returnerRating: Math.round(
        (p.spd * 0.4) + (p.agi * 0.3) + (p.cth * 0.2) + (p.awr * 0.1)
      )
    }));
    
    // Sort by returner rating and take top 10
    eligiblePlayers = playersWithRating
      .sort((a, b) => b.returnerRating - a.returnerRating)
      .slice(0, 10);
  } else {
    // Get eligible positions for this slot
    const eligiblePositions = positionMap[position] || [position];
    eligiblePlayers = players.filter(p => eligiblePositions.includes(p.pos));
  }
  
  return (
    <div className="space-y-3">
      <div className="text-[#d4af37] text-sm uppercase tracking-wider">
        {position}
      </div>
      <div className="space-y-2">
        {Array.from({ length: slots }).map((_, idx) => {
          const selectedPlayer = selectedPlayers[idx];
          const slotLabel = `${position}${idx + 1}`;
          
          return (
            <Select 
              key={idx}
              value={selectedPlayer?.name || 'none'} 
              onValueChange={(value) => {
                if (value === 'none') {
                  onSelect(position, idx, null);
                } else {
                  const player = players.find(p => p.name === value);
                  onSelect(position, idx, player || null);
                }
              }}
            >
              <SelectTrigger className="w-full bg-[#0a1929] border-[#2d4a6f] text-white h-9 text-xs hover:bg-[#0f1f35] transition-colors">
                <SelectValue placeholder="— Select —">
                  {selectedPlayer ? (
                    <div className="flex items-center gap-2 w-full">
                      <span className="text-[#94a3b8] text-xs">{slotLabel}</span>
                      <span className="text-white">•</span>
                      <span className="text-white flex-1">{selectedPlayer.name}</span>
                      <div className="px-1.5 py-0.5 bg-[#d4af37] text-[#0a1929] rounded text-xs flex-shrink-0">
                        {selectedPlayer.ovr}
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[#94a3b8] text-xs">{slotLabel}</span>
                      <span className="text-[#64748b]">— Select —</span>
                    </div>
                  )}
                </SelectValue>
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-h-[240px] w-[300px]">
                {eligiblePlayers
                  .sort((a, b) => {
                    if (isReturner) {
                      const aRating = Math.round((a.spd * 0.4) + (a.agi * 0.3) + (a.cth * 0.2) + (a.awr * 0.1));
                      const bRating = Math.round((b.spd * 0.4) + (b.agi * 0.3) + (b.cth * 0.2) + (b.awr * 0.1));
                      return bRating - aRating;
                    }
                    return b.ovr - a.ovr;
                  })
                  .slice(0, 10)
                  .map((player) => {
                    const displayRating = isReturner 
                      ? Math.round((player.spd * 0.4) + (player.agi * 0.3) + (player.cth * 0.2) + (player.awr * 0.1))
                      : player.ovr;
                    
                    return (
                      <SelectItem 
                        key={player.name} 
                        value={player.name}
                        className="text-white hover:bg-[#2d4a6f] focus:bg-[#2d4a6f] focus:text-white text-xs py-2"
                      >
                        <div className="flex items-center justify-between w-full gap-3">
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <span className="text-[#94a3b8] text-xs">#{player.num}</span>
                            <span className="truncate">{player.name}</span>
                            {isReturner && <span className="text-[#94a3b8] text-xs">({player.pos})</span>}
                          </div>
                          <div className="px-1.5 py-0.5 bg-[#d4af37] text-[#0a1929] rounded text-xs flex-shrink-0">
                            {displayRating}
                          </div>
                        </div>
                      </SelectItem>
                    );
                  })}
                <SelectItem value="none" className="text-[#94a3b8] hover:bg-[#2d4a6f] text-xs border-t border-[#2d4a6f] mt-1">
                  Clear slot
                </SelectItem>
              </SelectContent>
            </Select>
          );
        })}
      </div>
    </div>
  );
}

export function DepthChartCards({ players, positionQuotas, depthChartSlots, onOpenAutoFill, warnings = [], isAutoFilled = false }: DepthChartCardsProps) {
  // Initialize depth chart state - in a real app this would be persisted
  const [offenseDepth, setOffenseDepth] = useState<Record<string, (Player | null)[]>>({});
  const [defenseDepth, setDefenseDepth] = useState<Record<string, (Player | null)[]>>({});
  const [specialTeamsDepth, setSpecialTeamsDepth] = useState<Record<string, (Player | null)[]>>({});
  const [hasBeenAutoFilled, setHasBeenAutoFilled] = useState(false);
  
  // Warnings state
  const [showWarnings, setShowWarnings] = useState(false);
  const [warningsModalOpen, setWarningsModalOpen] = useState(false);
  
  // Show warnings when they exist
  useEffect(() => {
    if (warnings.length > 0) {
      setShowWarnings(true);
    }
  }, [warnings]);
  
  // Auto-fill depth chart with mock data when isAutoFilled changes
  useEffect(() => {
    if (isAutoFilled && !hasBeenAutoFilled) {
      setHasBeenAutoFilled(true);
      autoPopulateDepth();
    } else if (isAutoFilled && hasBeenAutoFilled) {
      // On subsequent auto-fills, only fill empty slots
      autoPopulateEmptySlots();
    }
  }, [isAutoFilled]);
  
  const autoPopulateDepth = () => {
    // Populate offense positions
    const newOffenseDepth: Record<string, (Player | null)[]> = {};
    OFFENSE_POSITIONS.forEach(pos => {
      const slots = depthChartSlots[pos];
      if (!slots) return;
      
      const positionMap: Record<string, string> = {
        'LT': 'T', 'LG': 'G', 'C': 'C', 'RG': 'G', 'RT': 'T',
      };
      const rosterPos = positionMap[pos] || pos;
      const eligiblePlayers = players.filter(p => p.pos === rosterPos).sort((a, b) => b.ovr - a.ovr);
      
      newOffenseDepth[pos] = Array.from({ length: slots }, (_, idx) => eligiblePlayers[idx] || null);
    });
    setOffenseDepth(newOffenseDepth);
    
    // Populate defense positions
    const newDefenseDepth: Record<string, (Player | null)[]> = {};
    DEFENSE_POSITIONS.forEach(pos => {
      const slots = depthChartSlots[pos];
      if (!slots) return;
      
      const positionMap: Record<string, string> = {
        'LDE': 'DE', 'RDE': 'DE', 'DT': 'DT',
        'OLB': 'LB', 'MLB': 'LB',
        'FS': 'S', 'SS': 'S',
      };
      const rosterPos = positionMap[pos] || pos;
      const eligiblePlayers = players.filter(p => p.pos === rosterPos).sort((a, b) => b.ovr - a.ovr);
      
      newDefenseDepth[pos] = Array.from({ length: slots }, (_, idx) => eligiblePlayers[idx] || null);
    });
    setDefenseDepth(newDefenseDepth);
    
    // Populate special teams
    const newSpecialTeamsDepth: Record<string, (Player | null)[]> = {};
    SPECIAL_TEAMS_POSITIONS.forEach(pos => {
      const slots = depthChartSlots[pos];
      if (!slots) return;
      
      if (pos === 'KR' || pos === 'PR') {
        // Use fastest players for returners
        const eligiblePlayers = players.sort((a, b) => (b.spd || 0) - (a.spd || 0));
        newSpecialTeamsDepth[pos] = Array.from({ length: slots }, (_, idx) => eligiblePlayers[idx] || null);
      } else {
        const eligiblePlayers = players.filter(p => p.pos === pos);
        newSpecialTeamsDepth[pos] = Array.from({ length: slots }, (_, idx) => eligiblePlayers[idx] || null);
      }
    });
    setSpecialTeamsDepth(newSpecialTeamsDepth);
  };
  
  const autoPopulateEmptySlots = () => {
    // Only fill slots that are currently empty (preserve user selections)
    const fillEmptySlots = (currentDepth: Record<string, (Player | null)[]>, positions: string[]) => {
      const newDepth = { ...currentDepth };
      
      positions.forEach(pos => {
        const slots = depthChartSlots[pos];
        if (!slots) return;
        
        const positionMap: Record<string, string> = {
          'LT': 'T', 'LG': 'G', 'C': 'C', 'RG': 'G', 'RT': 'T',
          'LDE': 'DE', 'RDE': 'DE', 'DT': 'DT',
          'OLB': 'LB', 'MLB': 'LB',
          'FS': 'S', 'SS': 'S',
        };
        const rosterPos = positionMap[pos] || pos;
        
        let eligiblePlayers: Player[];
        if (pos === 'KR' || pos === 'PR') {
          eligiblePlayers = players.sort((a, b) => (b.spd || 0) - (a.spd || 0));
        } else {
          eligiblePlayers = players.filter(p => p.pos === rosterPos).sort((a, b) => b.ovr - a.ovr);
        }
        
        const existingSlots = newDepth[pos] || [];
        const filledSlots = [...existingSlots];
        
        for (let i = 0; i < slots; i++) {
          if (!filledSlots[i]) {
            // Find first player not already assigned
            const usedPlayers = filledSlots.filter(Boolean).map(p => p!.name);
            const nextPlayer = eligiblePlayers.find(p => !usedPlayers.includes(p.name));
            filledSlots[i] = nextPlayer || null;
          }
        }
        
        newDepth[pos] = filledSlots;
      });
      
      return newDepth;
    };
    
    setOffenseDepth(prev => fillEmptySlots(prev, OFFENSE_POSITIONS));
    setDefenseDepth(prev => fillEmptySlots(prev, DEFENSE_POSITIONS));
    setSpecialTeamsDepth(prev => fillEmptySlots(prev, SPECIAL_TEAMS_POSITIONS));
  };

  const handleOffenseSelect = (position: string, slot: number, player: Player | null) => {
    setOffenseDepth(prev => {
      const posDepth = [...(prev[position] || [])];
      posDepth[slot] = player;
      return {
        ...prev,
        [position]: posDepth
      };
    });
  };

  const handleDefenseSelect = (position: string, slot: number, player: Player | null) => {
    setDefenseDepth(prev => {
      const posDepth = [...(prev[position] || [])];
      posDepth[slot] = player;
      return {
        ...prev,
        [position]: posDepth
      };
    });
  };

  const handleSpecialTeamsSelect = (position: string, slot: number, player: Player | null) => {
    setSpecialTeamsDepth(prev => {
      const posDepth = [...(prev[position] || [])];
      posDepth[slot] = player;
      return {
        ...prev,
        [position]: posDepth
      };
    });
  };

  // Check if depth chart is empty
  const hasAnyDepth = Object.keys(offenseDepth).length > 0 || 
                      Object.keys(defenseDepth).length > 0 || 
                      Object.keys(specialTeamsDepth).length > 0;

  return (
    <>
      <div className="space-y-6">
        {/* Offense Depth Chart */}
        <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] overflow-hidden">
          {/* Warnings Bar */}
          {showWarnings && warnings.length > 0 && (
            <WarningsBar
              warnings={warnings}
              onViewAll={() => setWarningsModalOpen(true)}
              onClear={() => setShowWarnings(false)}
            />
          )}
          
          <div className="p-4 border-b border-[#2d4a6f] flex items-center justify-between">
            <div>
              <h3 className="text-white">Offense Depth Chart</h3>
              <p className="text-[#94a3b8] text-xs mt-0.5">Set depth for offensive positions</p>
            </div>
            <Button
              onClick={onOpenAutoFill}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Auto-Fill Depth Chart
            </Button>
          </div>
          
          {/* Dropdown Grid - Always Visible */}
          <div className="p-6 overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {OFFENSE_POSITIONS.map((pos) => {
                const slots = depthChartSlots[pos];
                if (!slots) return null;
                
                return (
                  <PositionColumn
                    key={pos}
                    position={pos}
                    slots={slots}
                    players={players}
                    selectedPlayers={offenseDepth[pos] || []}
                    onSelect={handleOffenseSelect}
                  />
                );
              })}
            </div>
          </div>
        </div>

        {/* Defense Depth Chart */}
        <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
          <div className="p-4 border-b border-[#2d4a6f]">
            <h3 className="text-white">Defense Depth Chart</h3>
            <p className="text-[#94a3b8] text-xs mt-0.5">Set depth for defensive positions</p>
          </div>
          <div className="p-6 overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {DEFENSE_POSITIONS.map((pos) => {
                const slots = depthChartSlots[pos];
                if (!slots) return null;
                
                return (
                  <PositionColumn
                    key={pos}
                    position={pos}
                    slots={slots}
                    players={players}
                    selectedPlayers={defenseDepth[pos] || []}
                    onSelect={handleDefenseSelect}
                  />
                );
              })}
            </div>
            
            {/* Special Teams Section */}
            <div className="mt-8 pt-6 border-t border-[#2d4a6f]">
              <h4 className="text-white mb-4 text-sm uppercase tracking-wider">Special Teams</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {SPECIAL_TEAMS_POSITIONS.map((pos) => {
                  const slots = depthChartSlots[pos];
                  if (!slots) return null;
                  
                  return (
                    <PositionColumn
                      key={pos}
                      position={pos}
                      slots={slots}
                      players={players}
                      selectedPlayers={specialTeamsDepth[pos] || []}
                      onSelect={handleSpecialTeamsSelect}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Warnings Modal */}
      <WarningsModal
        open={warningsModalOpen}
        onClose={() => setWarningsModalOpen(false)}
        warnings={warnings}
      />
    </>
  );
}
