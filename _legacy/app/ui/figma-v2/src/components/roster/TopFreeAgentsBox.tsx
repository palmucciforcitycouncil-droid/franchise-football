import { useState, useEffect } from 'react';
import { Users, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '../ui/button';
import { SearchablePlayer, searchPlayers } from '../../lib/mockPlayerSearchApi';
import { toast } from 'sonner@2.0.3';

const POSITIONS = ['All', 'QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S'];

export function TopFreeAgentsBox() {
  const [freeAgents, setFreeAgents] = useState<SearchablePlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPositionIndex, setCurrentPositionIndex] = useState(0);

  useEffect(() => {
    loadFreeAgents();
  }, [currentPositionIndex]);

  const loadFreeAgents = async () => {
    setLoading(true);
    try {
      const position = POSITIONS[currentPositionIndex];
      // Mock: Search for top players and treat them as FAs
      const results = await searchPlayers({
        position: position === 'All' ? undefined : position,
        overallMin: 75, // Only show quality free agents
      });
      
      // Take top 5
      setFreeAgents(results.slice(0, 5));
    } catch (error) {
      console.error('Failed to load free agents:', error);
      toast.error('Failed to load free agents');
    } finally {
      setLoading(false);
    }
  };

  const handlePrevPosition = () => {
    setCurrentPositionIndex((prev) => (prev === 0 ? POSITIONS.length - 1 : prev - 1));
  };

  const handleNextPosition = () => {
    setCurrentPositionIndex((prev) => (prev === POSITIONS.length - 1 ? 0 : prev + 1));
  };

  const handlePlayerClick = (player: SearchablePlayer) => {
    toast.info(`Viewing ${player.name} (Free Agent)`);
  };

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-[#d4af37]" />
            <h3 className="text-white">Top Free Agents</h3>
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
        ) : freeAgents.length === 0 ? (
          <div className="text-center py-8 text-[#94a3b8] text-sm">No free agents available</div>
        ) : (
          <div className="space-y-2">
            {freeAgents.map((player, index) => (
              <div
                key={player.id}
                onClick={() => handlePlayerClick(player)}
                className="bg-[#0a1929] p-2 rounded border border-[#2d4a6f] hover:border-[#d4af37]/50 cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[#94a3b8] w-4">#{index + 1}</span>
                    <span className="text-sm text-white">{player.name}</span>
                  </div>
                  <span className="text-sm text-[#d4af37]">OVR {player.overall}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-[#94a3b8] ml-6">
                  <span>{player.position} · Age {player.age}</span>
                  <span>POT {player.potential}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
