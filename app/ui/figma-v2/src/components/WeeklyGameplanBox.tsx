import { useState, useEffect } from 'react';
import { CoachGameplanSection } from './CoachGameplanSection';
import { getCurrentStaff, CoachingPosition } from '../lib/mockStaffApi';

export function WeeklyGameplanBox() {
  const [hcPosition, setHcPosition] = useState<CoachingPosition | null>(null);
  const [loading, setLoading] = useState(true);

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
      <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f]">
        <h3 className="text-white">Weekly Gameplan</h3>
      </div>
      <div className="p-4">
        {hcPosition?.coach ? (
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
  );
}
