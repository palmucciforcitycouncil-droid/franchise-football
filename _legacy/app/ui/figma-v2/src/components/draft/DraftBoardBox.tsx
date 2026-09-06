/**
 * Draft Board Box Component
 * Shows team needs and watchlist players
 */

import { useState } from 'react';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { X, Plus, Star, TrendingUp, GripVertical, Clipboard } from 'lucide-react';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';

interface DraftBoardBoxProps {
  draftBoardPlayers: any[];
  onRemoveFromBoard?: (index: number) => void;
}

const ALL_POSITIONS = [
  { value: 'QB', label: 'Quarterback' },
  { value: 'RB', label: 'Running Back' },
  { value: 'WR', label: 'Wide Receiver' },
  { value: 'TE', label: 'Tight End' },
  { value: 'OL', label: 'Offensive Line' },
  { value: 'DL', label: 'Defensive Line' },
  { value: 'LB', label: 'Linebacker' },
  { value: 'CB', label: 'Cornerback' },
  { value: 'S', label: 'Safety' },
  { value: 'K', label: 'Kicker' },
  { value: 'P', label: 'Punter' },
];

export function DraftBoardBox({ draftBoardPlayers, onRemoveFromBoard }: DraftBoardBoxProps) {
  const [teamNeeds, setTeamNeeds] = useState<string[]>(['QB', 'RB', 'S']);
  const [selectedPosition, setSelectedPosition] = useState<string>('QB');
  const [showAddDropdown, setShowAddDropdown] = useState(false);

  const handleAddNeed = () => {
    if (selectedPosition && !teamNeeds.includes(selectedPosition)) {
      setTeamNeeds([...teamNeeds, selectedPosition]);
    }
    setShowAddDropdown(false);
  };

  const handleRemoveNeed = (position: string) => {
    setTeamNeeds(teamNeeds.filter(p => p !== position));
  };

  const getPositionColor = (pos: string) => {
    const colors: { [key: string]: string } = {
      QB: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      RB: 'bg-green-500/20 text-green-300 border-green-500/30',
      WR: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      TE: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
      OL: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      DL: 'bg-red-500/20 text-red-300 border-red-500/30',
      LB: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      CB: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
      S: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      K: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
      P: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
    };
    return colors[pos] || 'bg-[#2d4a6f]/20 text-[#94a3b8] border-[#2d4a6f]';
  };

  return (
    <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-[#d4af37]" />
          <h3 className="text-white">Draft Board</h3>
        </div>
      </div>

      {/* Team Needs Section */}
      <div className="mb-6 pb-6 border-b border-[#1F2A35]">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-[#94a3b8] text-sm">Team Needs</h4>
          {!showAddDropdown ? (
            <Button
              size="sm"
              onClick={() => setShowAddDropdown(true)}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] h-7 px-3"
            >
              <Plus className="w-3 h-3 mr-1" />
              Add
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <Select value={selectedPosition} onValueChange={setSelectedPosition}>
                <SelectTrigger className="w-[140px] h-7 bg-[#0a1929] border-[#2d4a6f] text-white text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a2332] border-[#2d4a6f]">
                  {ALL_POSITIONS.map((pos) => (
                    <SelectItem 
                      key={pos.value} 
                      value={pos.value}
                      className="text-white hover:bg-[#2d4a6f] text-xs"
                    >
                      {pos.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                onClick={handleAddNeed}
                className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] h-7 px-3"
              >
                Add
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowAddDropdown(false)}
                className="text-[#94a3b8] hover:text-white h-7 px-2"
              >
                <X className="w-3 h-3" />
              </Button>
            </div>
          )}
        </div>

        {teamNeeds.length === 0 ? (
          <div className="text-center py-6 text-[#94a3b8] text-sm">
            No team needs added yet. Click "Add" to get started.
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {teamNeeds.map((position, index) => (
              <Badge
                key={`${position}-${index}`}
                className={`px-3 py-1.5 border flex items-center gap-2 ${getPositionColor(position)}`}
              >
                {position}
                <button
                  onClick={() => handleRemoveNeed(position)}
                  className="hover:opacity-70 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Draft Board Players Section */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Clipboard className="w-4 h-4 text-[#d4af37]" />
          <h4 className="text-[#94a3b8] text-sm">Draft Board ({draftBoardPlayers.length})</h4>
        </div>

        {draftBoardPlayers.length === 0 ? (
          <div className="text-center py-8 text-[#94a3b8] text-sm">
            <Clipboard className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No players on draft board</p>
            <p className="text-xs mt-1">Click the clipboard icon next to players to add them</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {draftBoardPlayers.map((player, index) => (
              <div
                key={index}
                className="bg-[#0B0F14] border border-[#1F2A35] rounded-lg p-3 hover:bg-[#1a2332] transition-colors group"
              >
                <div className="flex items-start gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div className="flex items-center gap-1">
                      <GripVertical className="w-4 h-4 text-[#94a3b8]/50 cursor-move" />
                      <div className="w-6 h-6 rounded-full bg-[#d4af37] flex items-center justify-center text-xs text-[#0a1929]">
                        {index + 1}
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <ClickablePlayerName player={player} className="text-white text-sm block truncate">
                        {player.name}
                      </ClickablePlayerName>
                      <div className="text-[#94a3b8] text-xs">{player.ctr}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge
                      variant="outline"
                      className={`border ${getPositionColor(player.pos)}`}
                    >
                      {player.pos}
                    </Badge>
                    <button
                      onClick={() => onRemoveFromBoard?.(index)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-[#94a3b8] hover:text-red-400"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 text-xs ml-8">
                  <div className="flex items-center justify-between">
                    <span className="text-[#94a3b8]">OVR</span>
                    <span className={`px-1.5 py-0.5 rounded ${
                      player.ovr >= 90 ? 'bg-green-500/20 text-green-300' :
                      player.ovr >= 80 ? 'bg-blue-500/20 text-blue-300' :
                      player.ovr >= 70 ? 'bg-yellow-500/20 text-yellow-300' :
                      'bg-gray-500/20 text-gray-300'
                    }`}>
                      {player.ovr}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[#94a3b8]">POT</span>
                    <span className="text-white">{player.pot}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[#94a3b8]">Age</span>
                    <span className="text-white">{player.age}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
