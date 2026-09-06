import { useState, useEffect } from 'react';
import { Trophy, Star, Search, Users } from 'lucide-react';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { ClickablePlayerName } from './ui/ClickablePlayerName';
import { ClickableCoachName } from './ui/ClickableCoachName';
import { 
  HOFMember, 
  HOFCandidate, 
  getCurrentInductees, 
  getEligibleCandidates, 
  getHOFMembers 
} from '../lib/mockHOFApi';

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

function HOFMemberCard({ member }: { member: HOFMember }) {
  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] overflow-hidden">
      {/* Header */}
      <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-white mb-1">
              {member.type === 'player' ? (
                <ClickablePlayerName playerName={member.name} />
              ) : (
                <ClickableCoachName coachName={member.name} />
              )}
            </h3>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-[#d4af37]">
                {member.type === 'player' ? member.position : 'Coach'}
              </span>
              <span className="text-[#94a3b8]">•</span>
              <span className="text-[#94a3b8]">{member.teamsPrimary}</span>
            </div>
          </div>
          <Trophy className="h-5 w-5 text-[#d4af37]" />
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Years Info */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <div className="text-[#94a3b8]">Years Active</div>
            <div className="text-white">{member.yearsActive}</div>
          </div>
          <div>
            <div className="text-[#94a3b8]">Inducted</div>
            <div className="text-[#d4af37]">{member.inductionYear}</div>
          </div>
        </div>

        {/* Achievements */}
        <div>
          <div className="text-xs text-[#94a3b8] mb-2">Achievements</div>
          <div className="space-y-1">
            {member.achievements.slice(0, 4).map((achievement, idx) => (
              <div key={idx} className="text-xs text-white flex items-start gap-2">
                <span className="text-[#d4af37] mt-0.5">•</span>
                <span className="flex-1">{achievement}</span>
              </div>
            ))}
            {member.achievements.length > 4 && (
              <div className="text-xs text-[#94a3b8] italic">
                +{member.achievements.length - 4} more...
              </div>
            )}
          </div>
        </div>

        {/* Stats */}
        {member.type === 'player' ? (
          <div className="space-y-2">
            <div className="text-xs text-[#94a3b8] border-t border-[#2d4a6f] pt-3">
              Career Statistics
            </div>
            
            {member.passing && (
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Pass Yds:</span>
                  <span className="text-white">{member.passing.yards.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Pass TDs:</span>
                  <span className="text-white">{member.passing.touchdowns}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">INTs:</span>
                  <span className="text-white">{member.passing.interceptions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">QB Rating:</span>
                  <span className="text-[#d4af37]">{member.passing.qbRating.toFixed(1)}</span>
                </div>
              </div>
            )}

            {member.rushing && !member.passing && (
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Rush Yds:</span>
                  <span className="text-white">{member.rushing.yards.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Rush TDs:</span>
                  <span className="text-white">{member.rushing.touchdowns}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Attempts:</span>
                  <span className="text-white">{member.rushing.attempts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Average:</span>
                  <span className="text-white">{member.rushing.average.toFixed(1)}</span>
                </div>
              </div>
            )}

            {member.receiving && (
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Rec Yds:</span>
                  <span className="text-white">{member.receiving.yards.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Rec TDs:</span>
                  <span className="text-white">{member.receiving.touchdowns}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Receptions:</span>
                  <span className="text-white">{member.receiving.receptions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Average:</span>
                  <span className="text-white">{member.receiving.average.toFixed(1)}</span>
                </div>
              </div>
            )}

            {member.defense && (
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Tackles:</span>
                  <span className="text-white">{member.defense.tackles.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Sacks:</span>
                  <span className="text-white">{member.defense.sacks}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">INTs:</span>
                  <span className="text-white">{member.defense.interceptions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Def TDs:</span>
                  <span className="text-white">{member.defense.touchdowns}</span>
                </div>
              </div>
            )}

            {member.kicking && (
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">FG Made:</span>
                  <span className="text-white">{member.kicking.fgMade}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">FG%:</span>
                  <span className="text-[#d4af37]">{member.kicking.fgPct.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8]">Total Pts:</span>
                  <span className="text-white">{member.kicking.points.toLocaleString()}</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Coach stats */
          <div className="space-y-2">
            <div className="text-xs text-[#94a3b8] border-t border-[#2d4a6f] pt-3">
              Coaching Record
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-[#94a3b8]">Wins:</span>
                <span className="text-white">{member.coaching!.wins}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94a3b8]">Losses:</span>
                <span className="text-white">{member.coaching!.losses}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94a3b8]">Win %:</span>
                <span className="text-[#d4af37]">{member.coaching!.winPct.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94a3b8]">Titles:</span>
                <span className="text-white">{member.coaching!.championships}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function HOFPage() {
  const [inductees, setInductees] = useState<HOFMember[]>([]);
  const [candidates, setCandidates] = useState<HOFCandidate[]>([]);
  const [hofMembers, setHOFMembers] = useState<HOFMember[]>([]);
  const [filteredMembers, setFilteredMembers] = useState<HOFMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'player' | 'coach'>('all');
  const [positionFilter, setPositionFilter] = useState<string>('all');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [hofMembers, searchQuery, typeFilter, positionFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [inducteesData, candidatesData, membersData] = await Promise.all([
        getCurrentInductees(),
        getEligibleCandidates(),
        getHOFMembers(),
      ]);
      setInductees(inducteesData);
      setCandidates(candidatesData);
      setHOFMembers(membersData);
    } catch (error) {
      console.error('Failed to load HOF data:', error);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...hofMembers];

    // Type filter
    if (typeFilter !== 'all') {
      filtered = filtered.filter(member => member.type === typeFilter);
    }

    // Position filter (for players only)
    if (positionFilter !== 'all') {
      filtered = filtered.filter(member => member.position === positionFilter);
    }

    // Search filter
    if (searchQuery) {
      const lowerQuery = searchQuery.toLowerCase();
      filtered = filtered.filter(member =>
        member.name.toLowerCase().includes(lowerQuery) ||
        member.teamsPrimary.toLowerCase().includes(lowerQuery) ||
        (member.position && member.position.toLowerCase().includes(lowerQuery))
      );
    }

    setFilteredMembers(filtered);
  };

  // Get unique positions from HOF members
  const positions = Array.from(
    new Set(hofMembers.filter(m => m.type === 'player' && m.position).map(m => m.position!))
  ).sort();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-[#94a3b8]">Loading Hall of Fame...</div>
      </div>
    );
  }

  return (
    <div className="max-w-[1920px] mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <Trophy className="h-8 w-8 text-[#d4af37]" />
          <h2 className="text-white">Hall of Fame</h2>
        </div>
        <p className="text-[#94a3b8]">
          Honoring the greatest players and coaches in league history
        </p>
      </div>

      {/* Current Year Inductees */}
      <div className="bg-[#1a2332] rounded-lg border border-[#d4af37]">
        <div className="bg-gradient-to-r from-[#d4af37]/20 to-transparent p-4 border-b border-[#d4af37]">
          <div className="flex items-center gap-2">
            <Star className="h-5 w-5 text-[#d4af37]" />
            <h3 className="text-white">Class of 2028 Inductees</h3>
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {inductees.map(inductee => (
              <div
                key={inductee.id}
                className="bg-[#0a1929] p-4 rounded border border-[#d4af37]/50"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="text-white mb-1">{inductee.name}</h4>
                    <div className="text-sm text-[#d4af37]">
                      {inductee.type === 'player' ? inductee.position : 'Head Coach'} • {inductee.teamsPrimary}
                    </div>
                    <div className="text-xs text-[#94a3b8] mt-1">{inductee.yearsActive}</div>
                  </div>
                  <Trophy className="h-6 w-6 text-[#d4af37]" />
                </div>
                <div className="space-y-1">
                  {inductee.achievements.slice(0, 3).map((achievement, idx) => (
                    <div key={idx} className="text-xs text-white flex items-start gap-2">
                      <span className="text-[#d4af37]">•</span>
                      <span>{achievement}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Eligible Candidates */}
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
        <div className="p-4 border-b border-[#2d4a6f]">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-[#d4af37]" />
            <h3 className="text-white">Eligible Candidates</h3>
          </div>
        </div>
        <div className="p-4">
          <div className="space-y-2">
            {candidates.map(candidate => (
              <div
                key={candidate.id}
                className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] hover:border-[#d4af37]/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-white">{candidate.name}</span>
                      <span className="text-xs text-[#94a3b8]">
                        {candidate.type === 'player' ? candidate.position : 'Coach'} • {candidate.teamsPrimary}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
                      <span>{candidate.yearsActive}</span>
                      <span>•</span>
                      <span>Eligible: {candidate.eligibleYear}</span>
                      {candidate.votingPct && (
                        <>
                          <span>•</span>
                          <span className={candidate.votingPct >= 75 ? 'text-[#4ade80]' : 'text-[#94a3b8]'}>
                            {candidate.votingPct}% votes
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  {candidate.votingPct && candidate.votingPct >= 75 && (
                    <div className="px-2 py-1 bg-[#4ade80]/10 border border-[#4ade80]/30 rounded text-xs text-[#4ade80]">
                      Strong Candidate
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Hall of Fame Members */}
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
        <div className="p-4 border-b border-[#2d4a6f] space-y-4">
          <div className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-[#d4af37]" />
            <h3 className="text-white">Hall of Fame Members</h3>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#94a3b8]" />
              <Input
                type="text"
                placeholder="Search HOF members..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-[#0a1929] border-[#2d4a6f] text-white placeholder:text-[#94a3b8]"
              />
            </div>

            {/* Type Filter */}
            <Select value={typeFilter} onValueChange={(value: any) => setTypeFilter(value)}>
              <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="player">Players</SelectItem>
                <SelectItem value="coach">Coaches</SelectItem>
              </SelectContent>
            </Select>

            {/* Position Filter */}
            <Select 
              value={positionFilter} 
              onValueChange={setPositionFilter}
              disabled={typeFilter === 'coach'}
            >
              <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white disabled:opacity-50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                <SelectItem value="all">All Positions</SelectItem>
                {positions.map(pos => (
                  <SelectItem key={pos} value={pos}>{pos}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Results Count */}
          <div className="text-sm text-[#94a3b8]">
            Showing {filteredMembers.length} of {hofMembers.length} members
          </div>
        </div>

        {/* Members Grid */}
        <div className="p-4">
          {filteredMembers.length === 0 ? (
            <div className="text-center py-12 text-[#94a3b8]">
              No Hall of Fame members found matching your filters
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredMembers.map(member => (
                <HOFMemberCard key={member.id} member={member} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
