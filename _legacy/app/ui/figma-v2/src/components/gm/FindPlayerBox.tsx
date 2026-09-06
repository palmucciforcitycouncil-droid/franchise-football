import { useState } from 'react';
import { Search, Filter, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { ScrollArea } from '../ui/scroll-area';
import { 
  SearchablePlayer,
  SearchFilters,
  searchPlayers,
  getAllTeams,
  getAllPositions
} from '../../lib/mockPlayerSearchApi';
import { toast } from 'sonner@2.0.3';

export function FindPlayerBox() {
  const [searchResults, setSearchResults] = useState<SearchablePlayer[]>([]);
  const [searching, setSearching] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<SearchablePlayer | null>(null);
  const [playerModalOpen, setPlayerModalOpen] = useState(false);
  
  // Basic filters
  const [nameQuery, setNameQuery] = useState('');
  const [positionFilter, setPositionFilter] = useState<string>('all');
  const [teamFilter, setTeamFilter] = useState<string>('all');
  
  // Advanced filters
  const [ageMin, setAgeMin] = useState('');
  const [ageMax, setAgeMax] = useState('');
  const [overallMin, setOverallMin] = useState('');
  const [overallMax, setOverallMax] = useState('');
  const [potentialMin, setPotentialMin] = useState('');
  const [potentialMax, setPotentialMax] = useState('');
  const [speedMin, setSpeedMin] = useState('');
  const [speedMax, setSpeedMax] = useState('');
  const [strengthMin, setStrengthMin] = useState('');
  const [strengthMax, setStrengthMax] = useState('');
  const [agilityMin, setAgilityMin] = useState('');
  const [agilityMax, setAgilityMax] = useState('');
  const [throwPowerMin, setThrowPowerMin] = useState('');
  const [throwPowerMax, setThrowPowerMax] = useState('');
  const [throwAccuracyMin, setThrowAccuracyMin] = useState('');
  const [throwAccuracyMax, setThrowAccuracyMax] = useState('');
  const [catchingMin, setCatchingMin] = useState('');
  const [catchingMax, setCatchingMax] = useState('');
  const [tackleMin, setTackleMin] = useState('');
  const [tackleMax, setTackleMax] = useState('');
  const [awarenessMin, setAwarenessMin] = useState('');
  const [awarenessMax, setAwarenessMax] = useState('');
  
  const allTeams = getAllTeams();
  const allPositions = getAllPositions();

  const handleSearch = async () => {
    setSearching(true);
    
    const filters: SearchFilters = {
      name: nameQuery,
      position: positionFilter,
      team: teamFilter,
      ageMin: ageMin ? parseInt(ageMin) : undefined,
      ageMax: ageMax ? parseInt(ageMax) : undefined,
      overallMin: overallMin ? parseInt(overallMin) : undefined,
      overallMax: overallMax ? parseInt(overallMax) : undefined,
      potentialMin: potentialMin ? parseInt(potentialMin) : undefined,
      potentialMax: potentialMax ? parseInt(potentialMax) : undefined,
      speedMin: speedMin ? parseInt(speedMin) : undefined,
      speedMax: speedMax ? parseInt(speedMax) : undefined,
      strengthMin: strengthMin ? parseInt(strengthMin) : undefined,
      strengthMax: strengthMax ? parseInt(strengthMax) : undefined,
      agilityMin: agilityMin ? parseInt(agilityMin) : undefined,
      agilityMax: agilityMax ? parseInt(agilityMax) : undefined,
      throwPowerMin: throwPowerMin ? parseInt(throwPowerMin) : undefined,
      throwPowerMax: throwPowerMax ? parseInt(throwPowerMax) : undefined,
      throwAccuracyMin: throwAccuracyMin ? parseInt(throwAccuracyMin) : undefined,
      throwAccuracyMax: throwAccuracyMax ? parseInt(throwAccuracyMax) : undefined,
      catchingMin: catchingMin ? parseInt(catchingMin) : undefined,
      catchingMax: catchingMax ? parseInt(catchingMax) : undefined,
      tackleMin: tackleMin ? parseInt(tackleMin) : undefined,
      tackleMax: tackleMax ? parseInt(tackleMax) : undefined,
      awarenessMin: awarenessMin ? parseInt(awarenessMin) : undefined,
      awarenessMax: awarenessMax ? parseInt(awarenessMax) : undefined,
    };
    
    try {
      const results = await searchPlayers(filters);
      setSearchResults(results);
      toast.success(`Found ${results.length} player${results.length !== 1 ? 's' : ''}`);
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleClearFilters = () => {
    setNameQuery('');
    setPositionFilter('all');
    setTeamFilter('all');
    setAgeMin('');
    setAgeMax('');
    setOverallMin('');
    setOverallMax('');
    setPotentialMin('');
    setPotentialMax('');
    setSpeedMin('');
    setSpeedMax('');
    setStrengthMin('');
    setStrengthMax('');
    setAgilityMin('');
    setAgilityMax('');
    setThrowPowerMin('');
    setThrowPowerMax('');
    setThrowAccuracyMin('');
    setThrowAccuracyMax('');
    setCatchingMin('');
    setCatchingMax('');
    setTackleMin('');
    setTackleMax('');
    setAwarenessMin('');
    setAwarenessMax('');
    setSearchResults([]);
  };

  const handlePlayerClick = (player: SearchablePlayer) => {
    setSelectedPlayer(player);
    setPlayerModalOpen(true);
  };

  const hasActiveFilters = 
    nameQuery || 
    positionFilter !== 'all' || 
    teamFilter !== 'all' ||
    ageMin || ageMax ||
    overallMin || overallMax ||
    potentialMin || potentialMax ||
    speedMin || speedMax ||
    strengthMin || strengthMax ||
    agilityMin || agilityMax ||
    throwPowerMin || throwPowerMax ||
    throwAccuracyMin || throwAccuracyMax ||
    catchingMin || catchingMax ||
    tackleMin || tackleMax ||
    awarenessMin || awarenessMax;

  return (
    <>
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
        <div className="p-4 border-b border-[#2d4a6f]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Search className="h-5 w-5 text-[#d4af37]" />
              <h3 className="text-white">Find Player</h3>
            </div>
            {hasActiveFilters && (
              <Button
                size="sm"
                variant="ghost"
                onClick={handleClearFilters}
                className="text-[#94a3b8] hover:text-white h-8"
              >
                <X className="h-4 w-4 mr-1" />
                Clear
              </Button>
            )}
          </div>

          {/* Quick Search */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#94a3b8]" />
              <Input
                type="text"
                placeholder="Search by name..."
                value={nameQuery}
                onChange={(e) => setNameQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="pl-10 bg-[#0a1929] border-[#2d4a6f] text-white placeholder:text-[#94a3b8] h-9"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Select value={positionFilter} onValueChange={setPositionFilter}>
                <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                  <SelectItem value="all">All Positions</SelectItem>
                  {allPositions.map(pos => (
                    <SelectItem key={pos} value={pos}>{pos}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={teamFilter} onValueChange={setTeamFilter}>
                <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                  <SelectItem value="all">All Teams</SelectItem>
                  {allTeams.map(team => (
                    <SelectItem key={team} value={team}>{team}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Advanced Filters Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="w-full justify-between text-[#94a3b8] hover:text-white h-8"
            >
              <span className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                Advanced Filters
              </span>
              {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>

            {/* Advanced Filters */}
            {showFilters && (
              <div className="space-y-3 pt-2 border-t border-[#2d4a6f]">
                {/* Age Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Age Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={ageMin}
                      onChange={(e) => setAgeMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="20"
                      max="40"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={ageMax}
                      onChange={(e) => setAgeMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="20"
                      max="40"
                    />
                  </div>
                </div>

                {/* Overall Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Overall Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={overallMin}
                      onChange={(e) => setOverallMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={overallMax}
                      onChange={(e) => setOverallMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Potential Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Potential Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={potentialMin}
                      onChange={(e) => setPotentialMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={potentialMax}
                      onChange={(e) => setPotentialMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Speed Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Speed Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={speedMin}
                      onChange={(e) => setSpeedMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={speedMax}
                      onChange={(e) => setSpeedMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Strength Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Strength Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={strengthMin}
                      onChange={(e) => setStrengthMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={strengthMax}
                      onChange={(e) => setStrengthMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Agility Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Agility Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={agilityMin}
                      onChange={(e) => setAgilityMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={agilityMax}
                      onChange={(e) => setAgilityMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Throw Power Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Throw Power Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={throwPowerMin}
                      onChange={(e) => setThrowPowerMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={throwPowerMax}
                      onChange={(e) => setThrowPowerMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Throw Accuracy Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Throw Accuracy Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={throwAccuracyMin}
                      onChange={(e) => setThrowAccuracyMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={throwAccuracyMax}
                      onChange={(e) => setThrowAccuracyMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Catching Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Catching Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={catchingMin}
                      onChange={(e) => setCatchingMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={catchingMax}
                      onChange={(e) => setCatchingMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Tackle Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Tackle Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={tackleMin}
                      onChange={(e) => setTackleMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={tackleMax}
                      onChange={(e) => setTackleMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>

                {/* Awareness Range */}
                <div>
                  <Label className="text-xs text-[#94a3b8] mb-1">Awareness Range</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={awarenessMin}
                      onChange={(e) => setAwarenessMin(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={awarenessMax}
                      onChange={(e) => setAwarenessMax(e.target.value)}
                      className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-sm"
                      min="40"
                      max="99"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          <Button
            onClick={handleSearch}
            disabled={searching}
            className="w-full mt-3 bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] h-9"
          >
            {searching ? 'Searching...' : 'Search Players'}
          </Button>
        </div>

        {/* Results */}
        {searchResults.length > 0 && (
          <div className="p-4">
            <div className="text-xs text-[#94a3b8] mb-2">
              {searchResults.length} player{searchResults.length !== 1 ? 's' : ''} found
            </div>
            <ScrollArea className="h-[280px]">
              <div className="space-y-2 pr-4">
                {searchResults.map(player => (
                  <div
                    key={player.id}
                    onClick={() => handlePlayerClick(player)}
                    className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] hover:border-[#d4af37]/50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-white text-sm">{player.name}</span>
                        <span className="text-xs text-[#94a3b8]">#{player.number}</span>
                      </div>
                      <div className="text-sm text-[#d4af37]">OVR {player.overall}</div>
                    </div>
                    <div className="flex items-center justify-between text-xs text-[#94a3b8]">
                      <span>{player.position} · {player.team} · Age {player.age}</span>
                      <span>POT {player.potential}</span>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>

      {/* Player Detail Modal */}
      <Dialog open={playerModalOpen} onOpenChange={setPlayerModalOpen}>
        <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-white">Player Details</DialogTitle>
          </DialogHeader>

          {selectedPlayer && (
            <div className="space-y-4">
              {/* Header */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-xl text-white">{selectedPlayer.name}</div>
                    <div className="text-sm text-[#94a3b8]">
                      #{selectedPlayer.number} · {selectedPlayer.position} · {selectedPlayer.team}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl text-[#d4af37]">OVR {selectedPlayer.overall}</div>
                    <div className="text-sm text-[#94a3b8]">POT {selectedPlayer.potential}</div>
                  </div>
                </div>
                <div className="pt-2 border-t border-[#2d4a6f] grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-[#94a3b8]">Age:</span>
                    <span className="text-white ml-2">{selectedPlayer.age}</span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">Contract:</span>
                    <span className="text-white ml-2">{selectedPlayer.contract}</span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">Health:</span>
                    <span className="text-white ml-2">{selectedPlayer.health}</span>
                  </div>
                </div>
              </div>

              {/* Attributes */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f]">
                  <h4 className="text-sm text-[#d4af37] mb-2">Physical Attributes</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Speed:</span>
                      <span className="text-white">{selectedPlayer.speed}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Strength:</span>
                      <span className="text-white">{selectedPlayer.strength}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Agility:</span>
                      <span className="text-white">{selectedPlayer.agility}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Stamina:</span>
                      <span className="text-white">{selectedPlayer.stamina}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f]">
                  <h4 className="text-sm text-[#d4af37] mb-2">Skill Attributes</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Throw Power:</span>
                      <span className="text-white">{selectedPlayer.throwPower}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Throw Accuracy:</span>
                      <span className="text-white">{selectedPlayer.throwAccuracy}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Catching:</span>
                      <span className="text-white">{selectedPlayer.catching}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Tackle:</span>
                      <span className="text-white">{selectedPlayer.tackle}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Awareness:</span>
                      <span className="text-white">{selectedPlayer.awareness}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Other Stats */}
              <div className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f]">
                <h4 className="text-sm text-[#d4af37] mb-2">Other Info</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Injury:</span>
                    <span className="text-white">{selectedPlayer.injury}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Morale:</span>
                    <span className="text-white">{selectedPlayer.morale}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Depth:</span>
                    <span className="text-white">{selectedPlayer.depth}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <Button
                  className="flex-1 bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
                  onClick={() => {
                    toast.info(`Initiated trade for ${selectedPlayer.name}`);
                    setPlayerModalOpen(false);
                  }}
                >
                  Initiate Trade
                </Button>
                <Button
                  variant="outline"
                  className="flex-1 bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
                  onClick={() => setPlayerModalOpen(false)}
                >
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
