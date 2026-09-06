import { useGlobalModal } from '../../lib/GlobalModalContext';

interface ClickablePlayerNameProps {
  player?: any;
  playerName?: string;
  className?: string;
  children?: React.ReactNode;
}

export function ClickablePlayerName({ player, playerName, className = '', children }: ClickablePlayerNameProps) {
  const { openPlayerModal } = useGlobalModal();

  // If we only have a name string, create a minimal player object
  const playerData = player || (playerName ? { name: playerName, pos: 'N/A', age: 0, ovr: 0 } : null);

  if (!playerData) {
    return <span className={className}>{children || 'Unknown Player'}</span>;
  }

  return (
    <span
      onClick={(e) => {
        e.stopPropagation();
        openPlayerModal(playerData);
      }}
      className={`cursor-pointer hover:text-[#d4af37] transition-colors ${className}`}
    >
      {children || playerData.name}
    </span>
  );
}
