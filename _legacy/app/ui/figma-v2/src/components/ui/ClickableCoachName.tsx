import { useGlobalModal } from '../../lib/GlobalModalContext';

interface ClickableCoachNameProps {
  coach?: any;
  coachName?: string;
  className?: string;
  children?: React.ReactNode;
}

export function ClickableCoachName({ coach, coachName, className = '', children }: ClickableCoachNameProps) {
  const { openCoachModal } = useGlobalModal();

  // If we only have a name string, create a minimal coach object
  const coachData = coach || (coachName ? { 
    name: coachName, 
    title: 'Coach',
    specialty: 'Unknown',
    age: 0, 
    experience: 0,
    overallRating: 3.0,
    reputation: 50,
    background: 'Unknown',
    attitude: 'Unknown',
    style: 'Unknown'
  } : null);

  if (!coachData) {
    return <span className={className}>{children || 'Unknown Coach'}</span>;
  }

  return (
    <span
      onClick={(e) => {
        e.stopPropagation();
        openCoachModal(coachData);
      }}
      className={`cursor-pointer hover:text-[#d4af37] transition-colors ${className}`}
    >
      {children || coachData.name}
    </span>
  );
}
