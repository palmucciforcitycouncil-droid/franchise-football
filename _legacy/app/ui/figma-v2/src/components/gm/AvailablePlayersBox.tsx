import { useState, useEffect } from 'react';
import { Users, Search } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { 
  AvailablePlayer,
  getAvailablePlayers,
  getAvailableTeams,
  getAvailablePositions
} from '../../lib/mockTradeBlockApi';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';
import { toast } from 'sonner@2.0.3';

export function AvailablePlayersBox() {
  const [availablePlayers, setAvailablePlayers] = useState<AvailablePlayer[]>([]);
  const [filteredPlayers, setFilteredPlayers] = useState<AvailablePlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [positionFilter, setPositionFilter] = useState<string>('all');
  const [teamFilter, setTeamFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<'all' | 'prospect' | 'veteran'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const availableTeams = getAvailableTeams();
  const availablePositions = getAvailablePositions();

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [availablePlayers, positionFilter, teamFilter, typeFilter, searchQuery]);

  const loadData = async () => {
    try {
      setLoading(true);
      const players = await getAvailablePlayers();
      setAvailablePlayers(players);
    } catch (error) {
      console.error('Failed to load available players:', error);
      toast.error('Failed to load available players');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...availablePlayers];

    if (positionFilter !== 'all') {
      filtered = filtered.filter(p => p.position === positionFilter);
    }

    if (teamFilter !== 'all') {
      filtered = filtered.filter(p => p.team === teamFilter);
    }

    if (typeFilter !== 'all') {
      filtered = filtered.filter(p => p.type === typeFilter);
    }

    if (searchQuery) {
      const lowerQuery = searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(lowerQuery) ||
        p.team.toLowerCase().includes(lowerQuery)
      );
    }

    setFilteredPlayers(filtered);
  };

  const getInterestBadgeColor = (interest: string) => {
    switch (interest) {
      case 'high': return 'bg-[#4ade80]/10 text-[#4ade80] border-[#4ade80]/30';
      case 'medium': return 'bg-[#fbbf24]/10 text-[#fbbf24] border-[#fbbf24]/30';
      case 'low': return 'bg-[#94a3b8]/10 text-[#94a3b8] border-[#94a3b8]/30';
      default: return 'bg-[#94a3b8]/10 text-[#94a3b8] border-[#94a3b8]/30';
    }
  };

  if (loading) {
    return (
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-6">
        <div className="text-center py-8 text-[#94a3b8]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center gap-2 mb-3">
          <Users className="h-5 w-5 text-[#d4af37]" />
          <h3 className="text-white">On The Block</h3>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <Select value={positionFilter} onValueChange={setPositionFilter}>
            <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
              <SelectItem value="all">All Positions</SelectItem>
              {availablePositions.map(pos => (
                <SelectItem key={pos} value={pos}>{pos}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={teamFilter} onValueChange={setTeamFilter}>
            <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
              <SelectItem value="all">All Teams</SelectItem>
              {availableTeams.map(team => (
                <SelectItem key={team} value={team}>{team}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={typeFilter} onValueChange={(value: any) => setTypeFilter(value)}>
            <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="prospect">Prospects</SelectItem>
              <SelectItem value="veteran">Veterans</SelectItem>
            </SelectContent>
          </Select>

          <div className="relative">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3 w-3 text-[#94a3b8]" />
            <Input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-7 bg-[#0a1929] border-[#2d4a6f] text-white placeholder:text-[#94a3b8] h-8 text-xs"
            />
          </div>
        </div>

        <div className="text-xs text-[#94a3b8]">
          {filteredPlayers.length} of {availablePlayers.length} players
        </div>
      </div>

      {/* Players List */}
      <div className="p-4">
        <div className="max-h-[400px] overflow-y-auto space-y-2">
          {filteredPlayers.map(player => (
            <div
              key={player.id}
              className="bg-[#0a1929] p-2 rounded border border-[#2d4a6f] hover:border-[#d4af37]/50 transition-colors"
            >
              <div className="flex items-start justify-between mb-1.5">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-white text-sm">
                      <ClickablePlayerName playerName={player.name} />
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-xs border ${getInterestBadgeColor(player.interest)}`}>
                      {player.interest}
                    </span>
                  </div>
                  <div className="text-xs text-[#94a3b8]">
                    {player.position} · {player.team} · Age {player.age}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-[#d4af37]">OVR {player.overall}</div>
                  <div className="text-xs text-[#94a3b8]">{player.type}</div>
                </div>
              </div>
              
              <div className="text-xs text-[#94a3b8] mb-1.5">
                Contract: {player.contract}
              </div>
              
              <div className="bg-[#1a2332] p-1.5 rounded mb-1.5">
                <div className="text-xs text-[#94a3b8] mb-0.5">Asking:</div>
                <div className="text-xs text-white">{player.askingPrice}</div>
              </div>

              <Button
                size="sm"
                className="w-full bg-transparent border border-[#d4af37] text-[#d4af37] hover:bg-[#d4af37]/10 h-7 text-xs"
                onClick={() => {
                  toast.info(`Opened trade negotiations for ${player.name}`);
                }}
              >
                Make Offer
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
