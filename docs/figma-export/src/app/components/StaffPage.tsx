import { useState, useEffect } from 'react';
import { Star, Users, Plus, Search } from 'lucide-react';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner@2.0.3';
import { CoachGameplanSection } from './CoachGameplanSection';
import { ScoutingPanel } from './ScoutingPanel';
import { 
  Coach, 
  CoachingPosition,
  AvailableCoach, 
  CoachFocusArea,
  getCurrentStaff, 
  getAvailableCoaches,
  updateCoachFocus,
  fireCoach,
  resignCoach,
  hireCoach
} from '../lib/mockStaffApi';

const FOCUS_AREAS: CoachFocusArea[] = [
  'OF Gameplan',
  'DF Gameplan',
  'Training',
  'Development',
  'Scouting',
  'Special Teams Work',
  '2 Min Offense',
];

function StarRating({ rating }: { rating: number }) {
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 !== 0;

  return (
    <div className="flex items-center gap-1">
      {[...Array(5)].map((_, i) => (
        <Star
          key={i}
          className={`h-4 w-4 ${
            i < fullStars
              ? 'fill-[#d4af37] text-[#d4af37]'
              : i === fullStars && hasHalfStar
              ? 'fill-[#d4af37] text-[#d4af37] opacity-50'
              : 'text-[#2d4a6f]'
          }`}
        />
      ))}
    </div>
  );
}

function VacantCard({ 
  position, 
  onHire 
}: { 
  position: CoachingPosition; 
  onHire: (positionId: string) => void;
}) {
  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] overflow-hidden">
      {/* Header */}
      <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
        <h3 className="text-[#94a3b8] mb-1">VACANT</h3>
        <p className="text-[#d4af37] text-sm">{position.title}</p>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="w-20 h-20 bg-[#2d4a6f]/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <Users className="h-10 w-10 text-[#94a3b8]" />
            </div>
            <p className="text-[#94a3b8] mb-4">This position is currently vacant</p>
            <Button
              onClick={() => onHire(position.positionId)}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              <Plus className="h-4 w-4 mr-2" />
              Hire Coach
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function CoachCard({ 
  position,
  onFocusChange, 
  onFire, 
  onResign,
  onCoachClick
}: { 
  position: CoachingPosition;
  onFocusChange: (coachId: string, focus: CoachFocusArea) => void;
  onFire: (coach: Coach) => void;
  onResign: (coach: Coach) => void;
  onCoachClick: (coach: Coach) => void;
}) {
  const coach = position.coach!;
  
  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] overflow-hidden">
      {/* Header */}
      <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
        <h3 
          className="text-white mb-1 cursor-pointer hover:text-[#d4af37] transition-colors"
          onClick={() => onCoachClick(coach)}
        >
          {coach.name}
        </h3>
        <p className="text-[#d4af37] text-sm">{coach.title}</p>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Basic Info */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-[#94a3b8]">📅</span>
            <span className="text-white">{coach.age} years old</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[#94a3b8]">💼</span>
            <span className="text-white">{coach.experience} years exp</span>
          </div>
          <div className="flex items-center gap-2 col-span-2">
            <span className="text-[#94a3b8]">💰</span>
            <span className="text-white">{coach.salary} per year</span>
          </div>
          <div className="flex items-center gap-2 col-span-2">
            <span className="text-[#94a3b8]">📄</span>
            <span className="text-white">{coach.yearsRemaining} year(s) remaining</span>
          </div>
        </div>

        {/* Overall Rating */}
        <div>
          <div className="text-xs text-[#94a3b8] mb-1">Overall Rating</div>
          <StarRating rating={coach.overallRating} />
        </div>

        {/* Reputation */}
        <div>
          <div className="text-xs text-[#94a3b8] mb-2">Reputation</div>
          <div className="w-full bg-[#0a1929] rounded-full h-2">
            <div
              className="bg-[#d4af37] h-2 rounded-full transition-all"
              style={{ width: `${coach.reputation}%` }}
            />
          </div>
        </div>

        {/* Attributes Grid */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-[#94a3b8]">Background</span>
            <span className="text-white">{coach.background}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#94a3b8]">Attitude</span>
            <span className="text-white">{coach.attitude}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#94a3b8]">Style</span>
            <span className="text-white">{coach.style}</span>
          </div>
          {coach.offense && (
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Offense</span>
              <span className="text-white">{coach.offense}</span>
            </div>
          )}
          {coach.defense && (
            <div className="flex justify-between">
              <span className="text-[#94a3b8]">Defense</span>
              <span className="text-white">{coach.defense}</span>
            </div>
          )}
        </div>

        {/* Focus Area Dropdown */}
        <div>
          <Label className="text-xs text-[#94a3b8] mb-2 block">Focus Area</Label>
          <Select 
            value={coach.focusArea} 
            onValueChange={(value) => onFocusChange(coach.id, value as CoachFocusArea)}
          >
            <SelectTrigger className="w-full bg-[#0a1929] border-[#2d4a6f] text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
              {FOCUS_AREAS.map((area) => (
                <SelectItem key={area} value={area} className="hover:bg-[#2d4a6f]">
                  {area}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Gameplan Settings - Only for HC */}
        {coach.title === 'Head Coach' && (
          <div className="pt-2 border-t border-[#2d4a6f]">
            <CoachGameplanSection
              type="HC"
              coachId={coach.id}
            />
          </div>
        )}

        {/* Action Buttons */}
        <div className="space-y-2 pt-2">
          <Button
            size="sm"
            onClick={() => onResign(coach)}
            className="w-full bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
          >
            Re-sign
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onFire(coach)}
            className="w-full bg-transparent border-red-500 text-red-400 hover:bg-red-500/10"
          >
            Fire Coach
          </Button>
        </div>
      </div>
    </div>
  );
}

// Get available positions for promotion based on current role
function getPromotionPositions(currentRole?: 'Head Coach' | 'Offensive Coordinator' | 'Defensive Coordinator' | 'Assistant Coach'): string[] {
  if (!currentRole) return []; // Free agents can apply to any vacant position
  
  switch (currentRole) {
    case 'Assistant Coach':
      return ['Offensive Coordinator', 'Defensive Coordinator', 'Head Coach'];
    case 'Offensive Coordinator':
    case 'Defensive Coordinator':
      return ['Head Coach'];
    case 'Head Coach':
      return []; // HCs can't be promoted further
    default:
      return [];
  }
}

export function StaffPage() {
  const [coachingPositions, setCoachingPositions] = useState<CoachingPosition[]>([]);
  const [availableCoaches, setAvailableCoaches] = useState<AvailableCoach[]>([]);
  const [loading, setLoading] = useState(true);
  const [fireDialogOpen, setFireDialogOpen] = useState(false);
  const [resignDialogOpen, setResignDialogOpen] = useState(false);
  const [hireDialogOpen, setHireDialogOpen] = useState(false);
  const [coachDetailOpen, setCoachDetailOpen] = useState(false);
  const [currentStaffDetailOpen, setCurrentStaffDetailOpen] = useState(false);
  const [selectedCoach, setSelectedCoach] = useState<Coach | null>(null);
  const [selectedAvailableCoach, setSelectedAvailableCoach] = useState<AvailableCoach | null>(null);
  const [selectedPositionId, setSelectedPositionId] = useState<string>('');
  const [contractYears, setContractYears] = useState('');
  const [contractTotal, setContractTotal] = useState('');
  const [coachFilter, setCoachFilter] = useState<'free-agents' | 'on-teams'>('free-agents');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [positions, available] = await Promise.all([
        getCurrentStaff(),
        getAvailableCoaches()
      ]);
      setCoachingPositions(positions);
      setAvailableCoaches(available);
    } catch (error) {
      console.error('Failed to load staff data:', error);
      toast.error('Failed to load staff data');
    } finally {
      setLoading(false);
    }
  };

  const handleFocusChange = async (coachId: string, focus: CoachFocusArea) => {
    try {
      await updateCoachFocus(coachId, focus);
      setCoachingPositions(prev => 
        prev.map(p => 
          p.coach?.id === coachId 
            ? { ...p, coach: { ...p.coach, focusArea: focus } }
            : p
        )
      );
      toast.success('Coach focus area updated');
    } catch (error) {
      toast.error('Failed to update focus area');
    }
  };

  const handleFireClick = (coach: Coach) => {
    setSelectedCoach(coach);
    setFireDialogOpen(true);
  };

  const handleFireConfirm = async () => {
    if (!selectedCoach) return;

    try {
      const result = await fireCoach(selectedCoach.id);
      if (result.success) {
        toast.success(result.message);
        await loadData();
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      toast.error('Failed to fire coach');
    } finally {
      setFireDialogOpen(false);
      setSelectedCoach(null);
    }
  };

  const handleResignClick = (coach: Coach) => {
    setSelectedCoach(coach);
    const currentSalary = parseFloat(coach.salary.replace('$', '').replace('M', ''));
    const suggestedTotal = currentSalary * 3;
    setContractYears('3');
    setContractTotal(suggestedTotal.toString());
    setResignDialogOpen(true);
  };

  const handleResignSubmit = async () => {
    if (!selectedCoach || !contractYears || !contractTotal) return;

    try {
      const result = await resignCoach(
        selectedCoach.id,
        parseInt(contractYears),
        parseFloat(contractTotal)
      );
      
      if (result.success) {
        toast.success(result.message);
        await loadData();
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      toast.error('Failed to re-sign coach');
    } finally {
      setResignDialogOpen(false);
      setSelectedCoach(null);
      setContractYears('');
      setContractTotal('');
    }
  };

  const handleCoachClick = (coach: AvailableCoach) => {
    setSelectedAvailableCoach(coach);
    setCoachDetailOpen(true);
  };

  const handleCurrentStaffClick = (coach: Coach) => {
    setSelectedCoach(coach);
    setCurrentStaffDetailOpen(true);
  };

  const handleSignClick = () => {
    if (!selectedAvailableCoach) return;
    
    setCoachDetailOpen(false);
    setContractYears(selectedAvailableCoach.desiredLength.toString());
    const total = parseFloat(selectedAvailableCoach.desiredSalary.replace('$', '').replace('M', '')) * selectedAvailableCoach.desiredLength;
    setContractTotal(total.toString());
    setHireDialogOpen(true);
  };

  const handleVacantHire = (positionId: string) => {
    setSelectedPositionId(positionId);
    setSelectedAvailableCoach(null);
    setContractYears('');
    setContractTotal('');
    setHireDialogOpen(true);
  };

  const handleHireSubmit = async () => {
    if (!selectedAvailableCoach || !contractYears || !contractTotal || !selectedPositionId) return;

    try {
      const result = await hireCoach(
        selectedAvailableCoach.id,
        selectedPositionId,
        parseInt(contractYears),
        parseFloat(contractTotal)
      );
      
      if (result.success) {
        toast.success(result.message);
        await loadData();
        setHireDialogOpen(false);
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      toast.error('Failed to hire coach');
    } finally {
      setSelectedAvailableCoach(null);
      setSelectedPositionId('');
      setContractYears('');
      setContractTotal('');
    }
  };

  // Filter coaches based on selected filter and search
  const filteredCoaches = availableCoaches.filter(coach => {
    const matchesFilter = coachFilter === 'free-agents' 
      ? !coach.currentTeam 
      : !!coach.currentTeam;
    
    const matchesSearch = searchQuery === '' || 
      coach.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      coach.specialty.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (coach.currentTeam && coach.currentTeam.toLowerCase().includes(searchQuery.toLowerCase()));
    
    return matchesFilter && matchesSearch;
  });

  // Get available promotion positions for the selected coach
  const availablePromotionPositions = selectedAvailableCoach
    ? getPromotionPositions(selectedAvailableCoach.currentRole)
    : [];

  // Get vacant positions that match available promotions or all if free agent
  const vacantPositionsForHire = selectedAvailableCoach
    ? coachingPositions.filter(p => {
        if (p.coach) return false; // Not vacant
        if (!selectedAvailableCoach.currentTeam) return true; // Free agent can fill any position
        return availablePromotionPositions.includes(p.title); // Must be a promotion
      })
    : coachingPositions.filter(p => !p.coach);

  if (loading) {
    return (
      <div className="max-w-[1920px] mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-[500px] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // Separate HC from other positions
  const hcPosition = coachingPositions.find(p => p.title === 'Head Coach');
  const otherPositions = coachingPositions.filter(p => p.title !== 'Head Coach');

  return (
    <div className="max-w-[1920px] mx-auto space-y-6">
      {/* First Row: HC (2 cols) + Scouting (1 col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* HC Box - Spans 2 columns */}
        {hcPosition && (
          <>
            {/* HC Stats & Focus - Column 1 */}
            <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] overflow-hidden">
              {hcPosition.coach ? (
                <>
                  {/* Header */}
                  <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
                    <h3 
                      className="text-white mb-1 cursor-pointer hover:text-[#d4af37] transition-colors"
                      onClick={() => handleCurrentStaffClick(hcPosition.coach!)}
                    >
                      {hcPosition.coach.name}
                    </h3>
                    <p className="text-[#d4af37] text-sm">{hcPosition.coach.title}</p>
                  </div>

                  {/* Content */}
                  <div className="p-4 space-y-4">
                    {/* Basic Info */}
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-[#94a3b8]">📅</span>
                        <span className="text-white">{hcPosition.coach.age} years old</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[#94a3b8]">💼</span>
                        <span className="text-white">{hcPosition.coach.experience} years exp</span>
                      </div>
                      <div className="flex items-center gap-2 col-span-2">
                        <span className="text-[#94a3b8]">💰</span>
                        <span className="text-white">{hcPosition.coach.salary} per year</span>
                      </div>
                      <div className="flex items-center gap-2 col-span-2">
                        <span className="text-[#94a3b8]">📄</span>
                        <span className="text-white">{hcPosition.coach.yearsRemaining} year(s) remaining</span>
                      </div>
                    </div>

                    {/* Overall Rating */}
                    <div>
                      <div className="text-xs text-[#94a3b8] mb-1">Overall Rating</div>
                      <StarRating rating={hcPosition.coach.overallRating} />
                    </div>

                    {/* Reputation */}
                    <div>
                      <div className="text-xs text-[#94a3b8] mb-2">Reputation</div>
                      <div className="w-full bg-[#0a1929] rounded-full h-2">
                        <div
                          className="bg-[#d4af37] h-2 rounded-full transition-all"
                          style={{ width: `${hcPosition.coach.reputation}%` }}
                        />
                      </div>
                    </div>

                    {/* Attributes Grid */}
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-[#94a3b8]">Background</span>
                        <span className="text-white">{hcPosition.coach.background}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#94a3b8]">Attitude</span>
                        <span className="text-white">{hcPosition.coach.attitude}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#94a3b8]">Style</span>
                        <span className="text-white">{hcPosition.coach.style}</span>
                      </div>
                      {hcPosition.coach.offense && (
                        <div className="flex justify-between">
                          <span className="text-[#94a3b8]">Offense</span>
                          <span className="text-white">{hcPosition.coach.offense}</span>
                        </div>
                      )}
                      {hcPosition.coach.defense && (
                        <div className="flex justify-between">
                          <span className="text-[#94a3b8]">Defense</span>
                          <span className="text-white">{hcPosition.coach.defense}</span>
                        </div>
                      )}
                    </div>

                    {/* Focus Area Dropdown */}
                    <div>
                      <Label className="text-xs text-[#94a3b8] mb-2 block">Focus Area</Label>
                      <Select 
                        value={hcPosition.coach.focusArea} 
                        onValueChange={(value) => handleFocusChange(hcPosition.coach!.id, value as CoachFocusArea)}
                      >
                        <SelectTrigger className="w-full bg-[#0a1929] border-[#2d4a6f] text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                          {FOCUS_AREAS.map((area) => (
                            <SelectItem key={area} value={area} className="hover:bg-[#2d4a6f]">
                              {area}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Action Buttons */}
                    <div className="space-y-2 pt-2">
                      <Button
                        size="sm"
                        onClick={() => handleResignClick(hcPosition.coach!)}
                        className="w-full bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
                      >
                        Re-sign
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleFireClick(hcPosition.coach!)}
                        className="w-full bg-transparent border-red-500 text-red-400 hover:bg-red-500/10"
                      >
                        Fire Coach
                      </Button>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
                    <h3 className="text-[#94a3b8] mb-1">VACANT</h3>
                    <p className="text-[#d4af37] text-sm">{hcPosition.title}</p>
                  </div>
                  <div className="p-4">
                    <div className="flex items-center justify-center py-12">
                      <div className="text-center">
                        <div className="w-20 h-20 bg-[#2d4a6f]/30 rounded-full flex items-center justify-center mx-auto mb-4">
                          <Users className="h-10 w-10 text-[#94a3b8]" />
                        </div>
                        <p className="text-[#94a3b8] mb-4">This position is currently vacant</p>
                        <Button
                          onClick={() => handleVacantHire(hcPosition.positionId)}
                          className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Hire Coach
                        </Button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* HC Gameplan - Column 2 */}
            <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] overflow-hidden">
              <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
                <h3 className="text-white">Weekly Gameplan</h3>
              </div>
              <div className="p-4">
                {hcPosition.coach ? (
                  <CoachGameplanSection
                    type="HC"
                    coachId={hcPosition.coach.id}
                  />
                ) : (
                  <div className="text-center py-12 text-[#94a3b8]">
                    Hire a Head Coach to configure gameplan settings
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Scouting Panel - Column 3 */}
        <div>
          <ScoutingPanel />
        </div>
      </div>

      {/* Second Row: OC, DC, AC, AC (4 columns) */}
      <div>
        <h3 className="text-white mb-4">Assistant Coaches</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {otherPositions.map((position) => (
            position.coach ? (
              <CoachCard 
                key={position.positionId} 
                position={position}
                onFocusChange={handleFocusChange}
                onFire={handleFireClick}
                onResign={handleResignClick}
                onCoachClick={handleCurrentStaffClick}
              />
            ) : (
              <VacantCard
                key={position.positionId}
                position={position}
                onHire={handleVacantHire}
              />
            )
          ))}
        </div>
      </div>

      {/* Find Coaches Box */}
      <div>
        <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
          {/* Header */}
          <div className="p-4 border-b border-[#2d4a6f]">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-[#d4af37]" />
                <h3 className="text-white">Find Coaches</h3>
              </div>
              <Select value={coachFilter} onValueChange={(value: any) => setCoachFilter(value)}>
                <SelectTrigger className="w-[180px] bg-[#0a1929] border-[#2d4a6f] text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                  <SelectItem value="free-agents" className="hover:bg-[#2d4a6f]">
                    Free Agents
                  </SelectItem>
                  <SelectItem value="on-teams" className="hover:bg-[#2d4a6f]">
                    On Teams
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Search Bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#94a3b8]" />
              <Input
                type="text"
                placeholder="Search coaches..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-[#0a1929] border-[#2d4a6f] text-white placeholder:text-[#94a3b8]"
              />
            </div>
          </div>

          {/* Coaches List */}
          <div className="p-4">
            {filteredCoaches.length === 0 ? (
              <div className="text-center py-8 text-[#94a3b8]">
                No coaches found
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {filteredCoaches.map((coach) => (
                  <div
                    key={coach.id}
                    onClick={() => handleCoachClick(coach)}
                    className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] hover:border-[#d4af37] cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-white">{coach.name}</span>
                          {coach.currentTeam && (
                            <span className="px-2 py-0.5 bg-[#2d4a6f] text-[#d4af37] rounded text-xs">
                              {coach.currentTeam}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <span className="text-[#94a3b8]">{coach.specialty}</span>
                          {coach.currentRole && (
                            <span className="text-[#94a3b8]">• {coach.currentRole}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <StarRating rating={coach.overallRating} />
                        <div className="text-right">
                          <div className="text-white text-sm">{coach.desiredSalary}/yr</div>
                          <div className="text-[#94a3b8] text-xs">{coach.desiredLength} years</div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Coach Detail Dialog */}
      <Dialog open={coachDetailOpen} onOpenChange={setCoachDetailOpen}>
        <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-md" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle className="text-white">Coach Details</DialogTitle>
          </DialogHeader>

          {selectedAvailableCoach && (
            <div className="space-y-4 py-4">
              {/* Header Info */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-white">{selectedAvailableCoach.name}</h3>
                      {selectedAvailableCoach.currentTeam && (
                        <span className="px-2 py-0.5 bg-[#2d4a6f] text-[#d4af37] rounded text-xs">
                          {selectedAvailableCoach.currentTeam}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-[#d4af37] mb-2">{selectedAvailableCoach.specialty}</div>
                    {selectedAvailableCoach.currentRole && (
                      <div className="text-sm text-[#94a3b8]">Current: {selectedAvailableCoach.currentRole}</div>
                    )}
                  </div>
                  <StarRating rating={selectedAvailableCoach.overallRating} />
                </div>

                {/* Contract Desires */}
                <div className="pt-3 border-t border-[#2d4a6f] grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-[#94a3b8]">Desired Salary</div>
                    <div className="text-white">{selectedAvailableCoach.desiredSalary}/yr</div>
                  </div>
                  <div>
                    <div className="text-[#94a3b8]">Contract Length</div>
                    <div className="text-white">{selectedAvailableCoach.desiredLength} years</div>
                  </div>
                </div>
              </div>

              {/* Stats & Info */}
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-[#94a3b8]">Age</div>
                    <div className="text-white">{selectedAvailableCoach.age}</div>
                  </div>
                  <div>
                    <div className="text-[#94a3b8]">Experience</div>
                    <div className="text-white">{selectedAvailableCoach.experience} years</div>
                  </div>
                  <div>
                    <div className="text-[#94a3b8]">Background</div>
                    <div className="text-white">{selectedAvailableCoach.background}</div>
                  </div>
                  <div>
                    <div className="text-[#94a3b8]">Attitude</div>
                    <div className="text-white">{selectedAvailableCoach.attitude}</div>
                  </div>
                  <div>
                    <div className="text-[#94a3b8]">Style</div>
                    <div className="text-white">{selectedAvailableCoach.style}</div>
                  </div>
                  <div>
                    <div className="text-[#94a3b8]">Reputation</div>
                    <div className="text-white">{selectedAvailableCoach.reputation}</div>
                  </div>
                </div>

                {/* Schemes */}
                {(selectedAvailableCoach.offense || selectedAvailableCoach.defense) && (
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {selectedAvailableCoach.offense && (
                      <div>
                        <div className="text-[#94a3b8]">Offense</div>
                        <div className="text-white">{selectedAvailableCoach.offense}</div>
                      </div>
                    )}
                    {selectedAvailableCoach.defense && (
                      <div>
                        <div className="text-[#94a3b8]">Defense</div>
                        <div className="text-white">{selectedAvailableCoach.defense}</div>
                      </div>
                    )}
                  </div>
                )}

                {/* Reputation Bar */}
                <div>
                  <div className="text-xs text-[#94a3b8] mb-2">Reputation</div>
                  <div className="w-full bg-[#0a1929] rounded-full h-2">
                    <div
                      className="bg-[#d4af37] h-2 rounded-full transition-all"
                      style={{ width: `${selectedAvailableCoach.reputation}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Promotion Notice */}
              {selectedAvailableCoach.currentTeam && availablePromotionPositions.length > 0 && (
                <div className="bg-[#d4af37]/10 border border-[#d4af37]/30 rounded p-3">
                  <div className="text-sm text-[#d4af37]">
                    Can be signed to: {availablePromotionPositions.join(', ')}
                  </div>
                </div>
              )}

              {selectedAvailableCoach.currentTeam && availablePromotionPositions.length === 0 && (
                <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
                  <div className="text-sm text-red-400">
                    No promotion opportunities available for this coach
                  </div>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCoachDetailOpen(false)}
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
            >
              Close
            </Button>
            {selectedAvailableCoach && (
              (!selectedAvailableCoach.currentTeam || availablePromotionPositions.length > 0) && (
                <Button
                  onClick={handleSignClick}
                  disabled={vacantPositionsForHire.length === 0}
                  className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] disabled:opacity-50"
                >
                  Make Offer
                </Button>
              )
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Current Staff Coach Detail Dialog */}
      <Dialog open={currentStaffDetailOpen} onOpenChange={setCurrentStaffDetailOpen}>
        <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-2xl" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle className="text-white">Coach Profile</DialogTitle>
          </DialogHeader>

          {selectedCoach && (
            <div className="space-y-4 py-4">
              {/* Header Info */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="text-white mb-1">{selectedCoach.name}</h3>
                    <div className="text-sm text-[#d4af37] mb-2">{selectedCoach.title}</div>
                  </div>
                  <StarRating rating={selectedCoach.overallRating} />
                </div>

                {/* Contract Info */}
                <div className="pt-3 border-t border-[#2d4a6f] grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <div className="text-[#94a3b8]">Salary</div>
                    <div className="text-white">{selectedCoach.salary}/yr</div>
                  </div>
                  <div>
                    <div className="text-[#94a3b8]">Years Left</div>
                    <div className="text-white">{selectedCoach.yearsRemaining} year(s)</div>
                  </div>
                  <div>
                    <div className="text-[#94a3b8]">Focus Area</div>
                    <div className="text-white">{selectedCoach.focusArea}</div>
                  </div>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-4">
                {/* Basic Info */}
                <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                  <h4 className="text-white mb-3 text-sm">Basic Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Age</span>
                      <span className="text-white">{selectedCoach.age} years</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Experience</span>
                      <span className="text-white">{selectedCoach.experience} years</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Background</span>
                      <span className="text-white">{selectedCoach.background}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Attitude</span>
                      <span className="text-white">{selectedCoach.attitude}</span>
                    </div>
                  </div>
                </div>

                {/* Coaching Style */}
                <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                  <h4 className="text-white mb-3 text-sm">Coaching Style</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Style</span>
                      <span className="text-white">{selectedCoach.style}</span>
                    </div>
                    {selectedCoach.offense && (
                      <div className="flex justify-between">
                        <span className="text-[#94a3b8]">Offense</span>
                        <span className="text-white">{selectedCoach.offense}</span>
                      </div>
                    )}
                    {selectedCoach.defense && (
                      <div className="flex justify-between">
                        <span className="text-[#94a3b8]">Defense</span>
                        <span className="text-white">{selectedCoach.defense}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Reputation */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-white text-sm">Reputation</h4>
                  <span className="text-[#d4af37] text-sm">{selectedCoach.reputation}%</span>
                </div>
                <div className="w-full bg-[#1a2332] rounded-full h-3">
                  <div
                    className="bg-[#d4af37] h-3 rounded-full transition-all"
                    style={{ width: `${selectedCoach.reputation}%` }}
                  />
                </div>
              </div>

              {/* Career Highlights (Mock Data) */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <h4 className="text-white mb-3 text-sm">Career Highlights</h4>
                <div className="grid grid-cols-3 gap-3 text-center text-sm">
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 10) + 1}
                    </div>
                    <div className="text-[#94a3b8] text-xs">Championships</div>
                  </div>
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 50) + 30}
                    </div>
                    <div className="text-[#94a3b8] text-xs">Win %</div>
                  </div>
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 5) + 1}
                    </div>
                    <div className="text-[#94a3b8] text-xs">COY Awards</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCurrentStaffDetailOpen(false)}
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Fire Confirmation Dialog */}
      <AlertDialog open={fireDialogOpen} onOpenChange={setFireDialogOpen}>
        <AlertDialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Fire Coach</AlertDialogTitle>
            <AlertDialogDescription className="text-[#94a3b8]">
              Are you sure you want to fire {selectedCoach?.name}? This action cannot be undone.
              You will still be responsible for paying the remaining {selectedCoach?.yearsRemaining} year(s) of their contract.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleFireConfirm}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Fire Coach
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Re-sign Dialog */}
      <Dialog open={resignDialogOpen} onOpenChange={setResignDialogOpen}>
        <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Re-sign Coach</DialogTitle>
            <DialogDescription className="text-[#94a3b8]">
              Offer a new contract to {selectedCoach?.name}
            </DialogDescription>
          </DialogHeader>

          {selectedCoach && (
            <div className="space-y-4 py-4">
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-white">{selectedCoach.name}</div>
                    <div className="text-sm text-[#94a3b8]">{selectedCoach.title}</div>
                  </div>
                  <StarRating rating={selectedCoach.overallRating} />
                </div>
                <div className="pt-2 border-t border-[#2d4a6f] text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Current Salary:</span>
                    <span className="text-white">{selectedCoach.salary}/yr</span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <Label htmlFor="years" className="text-white">Contract Length (years)</Label>
                  <Input
                    id="years"
                    type="number"
                    value={contractYears}
                    onChange={(e) => setContractYears(e.target.value)}
                    className="bg-[#0a1929] border-[#2d4a6f] text-white mt-1"
                    min="1"
                    max="10"
                  />
                </div>
                <div>
                  <Label htmlFor="total" className="text-white">Total Value ($M)</Label>
                  <Input
                    id="total"
                    type="number"
                    value={contractTotal}
                    onChange={(e) => setContractTotal(e.target.value)}
                    className="bg-[#0a1929] border-[#2d4a6f] text-white mt-1"
                    step="0.1"
                  />
                </div>
                {contractYears && contractTotal && (
                  <div className="bg-[#2d4a6f]/30 p-3 rounded">
                    <div className="text-sm text-[#94a3b8]">Average Per Year</div>
                    <div className="text-xl text-white">
                      ${(parseFloat(contractTotal) / parseInt(contractYears)).toFixed(1)}M
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setResignDialogOpen(false)}
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
            >
              Cancel
            </Button>
            <Button
              onClick={handleResignSubmit}
              disabled={!contractYears || !contractTotal}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              Submit Offer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hire Dialog */}
      <Dialog open={hireDialogOpen} onOpenChange={setHireDialogOpen}>
        <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">
              {selectedAvailableCoach?.currentTeam ? 'Sign Coach (Promotion)' : 'Hire Coach'}
            </DialogTitle>
            <DialogDescription className="text-[#94a3b8]">
              {selectedAvailableCoach 
                ? `Make an offer to ${selectedAvailableCoach.name}`
                : 'Select a coach from the available coaches list'}
            </DialogDescription>
          </DialogHeader>

          {selectedAvailableCoach ? (
            <div className="space-y-4 py-4">
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-white">{selectedAvailableCoach.name}</div>
                    <div className="text-sm text-[#94a3b8]">{selectedAvailableCoach.specialty}</div>
                  </div>
                  <StarRating rating={selectedAvailableCoach.overallRating} />
                </div>
                <div className="pt-2 border-t border-[#2d4a6f] text-sm">
                  <div className="flex justify-between mb-1">
                    <span className="text-[#94a3b8]">Desired Salary:</span>
                    <span className="text-[#d4af37]">{selectedAvailableCoach.desiredSalary}/yr</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Desired Length:</span>
                    <span className="text-[#d4af37]">{selectedAvailableCoach.desiredLength} years</span>
                  </div>
                </div>
              </div>

              {/* Position Selection */}
              <div>
                <Label className="text-white mb-2 block">
                  {selectedAvailableCoach.currentTeam ? 'Promotion Position' : 'Select Position'}
                </Label>
                <Select value={selectedPositionId} onValueChange={setSelectedPositionId}>
                  <SelectTrigger className="w-full bg-[#0a1929] border-[#2d4a6f] text-white">
                    <SelectValue placeholder="Choose a position..." />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                    {vacantPositionsForHire.map((position) => (
                      <SelectItem key={position.positionId} value={position.positionId}>
                        {position.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedAvailableCoach.currentTeam && (
                  <p className="text-xs text-[#94a3b8] mt-1">
                    Only promotion positions are available
                  </p>
                )}
              </div>

              <div className="space-y-3">
                <div>
                  <Label htmlFor="hire-years" className="text-white">Contract Length (years)</Label>
                  <Input
                    id="hire-years"
                    type="number"
                    value={contractYears}
                    onChange={(e) => setContractYears(e.target.value)}
                    className="bg-[#0a1929] border-[#2d4a6f] text-white mt-1"
                    min="1"
                    max="10"
                  />
                </div>
                <div>
                  <Label htmlFor="hire-total" className="text-white">Total Value ($M)</Label>
                  <Input
                    id="hire-total"
                    type="number"
                    value={contractTotal}
                    onChange={(e) => setContractTotal(e.target.value)}
                    className="bg-[#0a1929] border-[#2d4a6f] text-white mt-1"
                    step="0.1"
                  />
                </div>
                {contractYears && contractTotal && (
                  <div className="bg-[#2d4a6f]/30 p-3 rounded">
                    <div className="text-sm text-[#94a3b8]">Average Per Year</div>
                    <div className="text-xl text-white">
                      ${(parseFloat(contractTotal) / parseInt(contractYears)).toFixed(1)}M
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-[#94a3b8]">
              Select a coach from the available coaches section to make an offer.
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setHireDialogOpen(false);
                setSelectedAvailableCoach(null);
                setSelectedPositionId('');
              }}
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
            >
              Cancel
            </Button>
            <Button
              onClick={handleHireSubmit}
              disabled={!contractYears || !contractTotal || !selectedPositionId || !selectedAvailableCoach}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              Make Offer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
