/**
 * Playoff/Badge Component
 * Version: Playoffs v1 (frozen)
 * Status: Design locked - do not modify without version bump
 */

import { cn } from '../ui/utils';

interface PlayoffBadgeProps {
  variant: 'AFC' | 'NFC' | 'WC' | 'DIV' | 'CONF' | 'SB' | 'neutral';
  size?: 'sm' | 'md';
  children: React.ReactNode;
  className?: string;
}

export function PlayoffBadge({ variant, size = 'md', children, className }: PlayoffBadgeProps) {
  const baseStyles = 'inline-flex items-center justify-center rounded-md font-semibold transition-colors';
  
  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };
  
  const variantStyles = {
    AFC: 'bg-[#dc2626]/20 text-[#ef4444] border border-[#dc2626]/30',
    NFC: 'bg-[#1e40af]/20 text-[#60a5fa] border border-[#1e40af]/30',
    WC: 'bg-[#1F2A35]/80 text-[#94a3b8] border border-[#2d4a6f]',
    DIV: 'bg-[#1F2A35]/80 text-[#94a3b8] border border-[#2d4a6f]',
    CONF: 'bg-[#1F2A35]/80 text-[#94a3b8] border border-[#2d4a6f]',
    SB: 'bg-[#1F2A35]/80 text-[#94a3b8] border border-[#2d4a6f]',
    neutral: 'bg-[#1F2A35]/80 text-[#94a3b8] border border-[#2d4a6f]',
  };
  
  return (
    <span className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)}>
      {children}
    </span>
  );
}
