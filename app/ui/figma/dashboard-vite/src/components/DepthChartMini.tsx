// Depth Chart Mini View per GDD v3.2 §9.2.2.1 Layout C1

import React, { useState } from 'react';
import { Button } from './ui/button';
import { ChevronUp, ChevronDown, AlertTriangle } from 'lucide-react';
import { DepthSlot, PlayerRow } from '../types/roster';
import { autoFillDepthChart, validateDepthChart } from '../utils/depthChart';

interface DepthChartMiniProps {
  players: PlayerRow[];
  depthChart: DepthSlot[];
  onDepthChartChange: (newDepthChart: DepthSlot[]) => void;
  onPlayerClick: (playerId: string) => void;
}

export function DepthChartMini({ 
  players, 
  depthChart, 
  onDepthChartChange, 
  onPlayerClick 
}: DepthChartMiniProps) {
  const [showPreview, setShowPreview] = useState(false);
  const [previewChanges, setPreviewChanges] = useState<any[]>([]);

  const handleAutoFill = () => {
    const result = autoFillDepthChart(players, depthChart);
    setPreviewChanges(result.changes);
    setShowPreview(true);
  };

  const handleApplyChanges = () => {
    const result = autoFillDepthChart(players, depthChart);
    onDepthChartChange(result.depthChart);
    setShowPreview(false);
    setPreviewChanges([]);
  };

  const handleCancelPreview = () => {
    setShowPreview(false);
    setPreviewChanges([]);
  };

  const getPlayerById = (playerId: string) => {
    return players.find(p => p.player_id === playerId);
  };

  const getPlayerAtPosition = (unit: string, pos: string, slot: number) => {
    const slotData = depthChart.find(s => 
      s.unit === unit && s.pos === pos && s.slot === slot
    );
    return slotData ? getPlayerById(slotData.player_id) : null;
  };

  const promotePlayer = (unit: string, pos: string, slot: number) => {
    if (slot <= 1) return;
    
    const newDepthChart = [...depthChart];
    const currentSlot = newDepthChart.findIndex(s => 
      s.unit === unit && s.pos === pos && s.slot === slot
    );
    const prevSlot = newDepthChart.findIndex(s => 
      s.unit === unit && s.pos === pos && s.slot === slot - 1
    );

    if (currentSlot !== -1 && prevSlot !== -1) {
      // Swap the players
      const temp = newDepthChart[currentSlot].player_id;
      newDepthChart[currentSlot].player_id = newDepthChart[prevSlot].player_id;
      newDepthChart[prevSlot].player_id = temp;
      
      onDepthChartChange(newDepthChart);
    }
  };

  const demotePlayer = (unit: string, pos: string, slot: number) => {
    const newDepthChart = [...depthChart];
    const currentSlot = newDepthChart.findIndex(s => 
      s.unit === unit && s.pos === pos && s.slot === slot
    );
    const nextSlot = newDepthChart.findIndex(s => 
      s.unit === unit && s.pos === pos && s.slot === slot + 1
    );

    if (currentSlot !== -1 && nextSlot !== -1) {
      // Swap the players
      const temp = newDepthChart[currentSlot].player_id;
      newDepthChart[currentSlot].player_id = newDepthChart[nextSlot].player_id;
      newDepthChart[nextSlot].player_id = temp;
      
      onDepthChartChange(newDepthChart);
    }
  };

  const warnings = validateDepthChart(depthChart, players);

  const PositionGroup = ({ 
    title, 
    unit, 
    positions 
  }: { 
    title: string; 
    unit: string; 
    positions: string[] 
  }) => (
    <div className="space-y-3">
      <h4 className="text-white font-medium text-sm">{title}</h4>
      {positions.map(pos => {
        const player1 = getPlayerAtPosition(unit, pos, 1);
        const player2 = getPlayerAtPosition(unit, pos, 2);
        const player3 = getPlayerAtPosition(unit, pos, 3);
        
        return (
          <div key={pos} className="space-y-1">
            <div className="text-[#94a3b8] text-xs font-medium">{pos}</div>
            <div className="space-y-1">
              {/* Starter */}
              <div className="flex items-center justify-between p-2 bg-[#0a1929] rounded border border-[#2d4a6f]">
                <div className="flex items-center gap-2">
                  <span className="text-[#d4af37] text-xs font-bold">1</span>
                  {player1 ? (
                    <button
                      onClick={() => onPlayerClick(player1.player_id)}
                      className="text-white text-sm hover:text-[#d4af37] transition-colors"
                    >
                      {player1.name}
                    </button>
                  ) : (
                    <span className="text-[#94a3b8] text-sm">Empty</span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {player1 && (
                    <span className="text-[#d4af37] text-xs">{player1.ovr}</span>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0 text-[#94a3b8] hover:text-white"
                    onClick={() => demotePlayer(unit, pos, 1)}
                    disabled={!player2}
                  >
                    <ChevronDown className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              {/* Backup 1 */}
              {player2 && (
                <div className="flex items-center justify-between p-2 bg-[#0a1929] rounded border border-[#2d4a6f]">
                  <div className="flex items-center gap-2">
                    <span className="text-[#94a3b8] text-xs font-bold">2</span>
                    <button
                      onClick={() => onPlayerClick(player2.player_id)}
                      className="text-white text-sm hover:text-[#d4af37] transition-colors"
                    >
                      {player2.name}
                    </button>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-[#d4af37] text-xs">{player2.ovr}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 text-[#94a3b8] hover:text-white"
                      onClick={() => promotePlayer(unit, pos, 2)}
                    >
                      <ChevronUp className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 text-[#94a3b8] hover:text-white"
                      onClick={() => demotePlayer(unit, pos, 2)}
                      disabled={!player3}
                    >
                      <ChevronDown className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              )}

              {/* Backup 2 */}
              {player3 && (
                <div className="flex items-center justify-between p-2 bg-[#0a1929] rounded border border-[#2d4a6f]">
                  <div className="flex items-center gap-2">
                    <span className="text-[#94a3b8] text-xs font-bold">3</span>
                    <button
                      onClick={() => onPlayerClick(player3.player_id)}
                      className="text-white text-sm hover:text-[#d4af37] transition-colors"
                    >
                      {player3.name}
                    </button>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-[#d4af37] text-xs">{player3.ovr}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 text-[#94a3b8] hover:text-white"
                      onClick={() => promotePlayer(unit, pos, 3)}
                    >
                      <ChevronUp className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between">
          <h3 className="text-white">Depth Chart</h3>
          <Button
            onClick={handleAutoFill}
            className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
          >
            Auto-Depth Assign
          </Button>
        </div>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="p-4 border-b border-[#2d4a6f]">
          <div className="flex items-center gap-2 text-amber-400 text-sm">
            <AlertTriangle className="h-4 w-4" />
            <span>Needs Attention:</span>
          </div>
          <div className="mt-2 space-y-1">
            {warnings.map((warning, index) => (
              <div key={index} className="text-[#94a3b8] text-xs">
                {warning}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Preview Changes */}
      {showPreview && previewChanges.length > 0 && (
        <div className="p-4 border-b border-[#2d4a6f] bg-[#0a1929]">
          <div className="text-white text-sm font-medium mb-2">Preview Changes:</div>
          <div className="space-y-1 mb-3">
            {previewChanges.map((change, index) => (
              <div key={index} className="text-[#94a3b8] text-xs">
                {change.position} {change.slot}: {change.oldPlayer ? `${change.oldPlayer} → ` : ''}{change.newPlayer}
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleApplyChanges}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              Apply Changes
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleCancelPreview}
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Depth Chart Content */}
      <div className="p-4">
        <div className="grid grid-cols-3 gap-6">
          {/* Offense */}
          <PositionGroup
            title="Offense"
            unit="OFF"
            positions={['QB', 'RB', 'WR', 'TE', 'C', 'LG', 'RG', 'LT', 'RT']}
          />

          {/* Defense */}
          <PositionGroup
            title="Defense"
            unit="DEF"
            positions={['DE', 'DT', 'MLB', 'OLB', 'CB', 'FS', 'SS']}
          />

          {/* Special Teams */}
          <PositionGroup
            title="Special Teams"
            unit="ST"
            positions={['K', 'P', 'KR', 'PR', 'LS']}
          />
        </div>
      </div>
    </div>
  );
}
