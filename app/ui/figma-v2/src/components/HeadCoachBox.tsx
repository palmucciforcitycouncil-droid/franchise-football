import { useState, useEffect } from 'react';
import { Star, Users } from 'lucide-react';
import { useGlobalModal } from '../lib/GlobalModalContext';
import { getCurrentStaff, CoachingPosition } from '../lib/mockStaffApi';

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

export function HeadCoachBox() {
  const [hcPosition, setHcPosition] = useState<CoachingPosition | null>(null);
  const [loading, setLoading] = useState(true);
  const { openCoachModal } = useGlobalModal();

  useEffect(() => {
    loadHeadCoach();
  }, []);

  const loadHeadCoach = async () => {
    try {
      setLoading(true);
      const positions = await getCurrentStaff();
      const hc = positions.find(p => p.title === 'Head Coach');
      setHcPosition(hc || null);
    } catch (error) {
      console.error('Failed to load head coach:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-[400px] animate-pulse" />
    );
  }

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] overflow-hidden">
      {hcPosition?.coach ? (
        <>
          {/* Header */}
          <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
            <h3 
              className="text-white mb-1 cursor-pointer hover:text-[#d4af37] transition-colors"
              onClick={() => openCoachModal(hcPosition.coach!)}
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

            {/* Focus Area Display (read-only on dashboard) */}
            <div>
              <div className="text-xs text-[#94a3b8] mb-2">Focus Area</div>
              <div className="bg-[#0a1929] border border-[#2d4a6f] rounded px-3 py-2 text-white text-sm">
                {hcPosition.coach.focusArea}
              </div>
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
            <h3 className="text-[#94a3b8] mb-1">VACANT</h3>
            <p className="text-[#d4af37] text-sm">Head Coach</p>
          </div>
          <div className="p-4">
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="w-20 h-20 bg-[#2d4a6f]/30 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Users className="h-10 w-10 text-[#94a3b8]" />
                </div>
                <p className="text-[#94a3b8]">No head coach assigned</p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
