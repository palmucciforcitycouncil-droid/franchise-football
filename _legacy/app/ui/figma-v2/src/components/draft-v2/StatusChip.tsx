interface StatusChipProps {
  variant: 'simulating' | 'on-clock';
  pickNumber?: number;
}

export function StatusChip({ variant, pickNumber }: StatusChipProps) {
  if (variant === 'simulating') {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[#1e3a5f]/50 border border-[#2d4a6f] rounded-lg">
        <div className="relative">
          <div className="w-2 h-2 bg-[#d4af37] rounded-full animate-pulse" />
          <div className="absolute inset-0 w-2 h-2 bg-[#d4af37] rounded-full animate-ping" />
        </div>
        <span className="text-[#94a3b8] text-sm">Simulating… updates every 10s</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-[#d4af37]/20 border border-[#d4af37] rounded-lg">
      <div className="w-2 h-2 bg-[#d4af37] rounded-full" />
      <span className="text-[#d4af37] text-sm">
        You're on the clock · Pick #{pickNumber}
      </span>
    </div>
  );
}
