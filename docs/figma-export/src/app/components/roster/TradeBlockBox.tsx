import { useState, useEffect } from 'react';
import { TrendingUp, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { AvailablePlayer, getAvailablePlayers } from '../../lib/mockTradeBlockApi';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';
import { toast } from 'sonner@2.0.3';

const POSITIONS = ['All', 'QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S'];

export function TradeBlockBox() {
  const [availablePlayers, setAvailablePlayers] = useState<AvailablePlayer[]>([]);
  const [filteredPlayers, setFilteredPlayers] = useState<AvailablePlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPositionIndex, setCurrentPositionIndex] = useState(0);

  useEffect(() => {
    loadPlayers();
  }, []);

  useEffect(() => {
    filterPlayers();
  }, [currentPositionIndex, availablePlayers]);

  const loadPlayers = async () => {
    setLoading(true);
    try {
      const players = await getAvailablePlayers();
      setAvailablePlayers(players);
    } catch (error) {
      console.error('Failed to load trade block:', error);
      toast.error('Failed to load trade block');
    } finally {
      setLoading(false);
    }
  };

  const filterPlayers = () => {
    const position = POSITIONS[currentPositionIndex];
    if (position === 'All') {
      setFilteredPlayers(availablePlayers.slice(0, 5));
    } else {
      const filtered = availablePlayers.filter(p => p.position === position);
      setFilteredPlayers(filtered.slice(0, 5));
    }
  };

  const handlePrevPosition = () => {
    setCurrentPositionIndex((prev) => (prev === 0 ? POSITIONS.length - 1 : prev - 1));
  };

  const handleNextPosition = () => {
    setCurrentPositionIndex((prev) => (prev === POSITIONS.length - 1 ? 0 : prev + 1));
  };

  const handlePlayerClick = (player: AvailablePlayer) => {
    toast.info(`Viewing ${player.name} on trade block`);
  };

  const getInterestBadgeColor = (interest: string) => {
    switch (interest) {
      case 'high': return 'bg-[#4ade80]/10 text-[#4ade80]';
      case 'medium': return 'bg-[#fbbf24]/10 text-[#fbbf24]';
      case 'low': return 'bg-[#94a3b8]/10 text-[#94a3b8]';
      default: return 'bg-[#94a3b8]/10 text-[#94a3b8]';
    }
  };

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-[#d4af37]" />
            <h3 className="text-white">Trade Block</h3>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={handlePrevPosition}
              className="h-7 w-7 p-0 text-[#94a3b8] hover:text-white"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-[50px] text-center">
              <span className="text-sm text-[#d4af37]">{POSITIONS[currentPositionIndex]}</span>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleNextPosition}
              className="h-7 w-7 p-0 text-[#94a3b8] hover:text-white"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="p-4">
        {loading ? (
          <div className="text-center py-8 text-[#94a3b8] text-sm">Loading...</div>
        ) : filteredPlayers.length === 0 ? (
          <div className="text-center py-8 text-[#94a3b8] text-sm">No players available</div>
        ) : (
          <ScrollArea className="h-[280px]">
            <div className="space-y-2 pr-4">
              {filteredPlayers.map((player) => (
                <div
                  key={player.id}
                  onClick={() => handlePlayerClick(player)}
                  className="bg-[#0a1929] p-2 rounded border border-[#2d4a6f] hover:border-[#d4af37]/50 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-white">
                        <ClickablePlayerName playerName={player.name} />
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${getInterestBadgeColor(player.interest)}`}>
                        {player.interest}
                      </span>
                    </div>
                    <span className="text-sm text-[#d4af37]">OVR {player.overall}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-[#94a3b8]">
                    <span>{player.position} · {player.team} · Age {player.age}</span>
                    <span className="text-xs">{player.type}</span>
                  </div>
                  <div className="mt-1 text-xs text-[#94a3b8]">
                    Asking: {player.askingPrice}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}
