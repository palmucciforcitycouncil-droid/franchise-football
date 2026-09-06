interface RoundTabsProps {
  activeRound: number;
  onRoundChange: (round: number) => void;
}

export function RoundTabs({ activeRound, onRoundChange }: RoundTabsProps) {
  const rounds = [1, 2, 3, 4, 5, 6, 7];

  return (
    <div className="flex items-center gap-1 bg-[#0B0F14] rounded-lg p-1 border border-[#1F2A35]">
      {rounds.map((round) => (
        <button
          key={round}
          onClick={() => onRoundChange(round)}
          className={`
            px-4 py-1.5 rounded text-sm transition-all
            ${activeRound === round
              ? 'bg-[#1e3a5f] text-white border-2 border-[#d4af37]'
              : 'text-[#94a3b8] hover:text-white hover:bg-[#1a2332]'
            }
          `}
        >
          {round}
        </button>
      ))}
    </div>
  );
}
