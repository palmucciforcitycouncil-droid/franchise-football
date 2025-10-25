// components/ui/checkbox.tsx
import React from 'react';
import { Check } from 'lucide-react';
import { cn } from './utils';

interface CheckboxProps {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  className?: string;
}

export function Checkbox({ checked = false, onCheckedChange, className }: CheckboxProps) {
  return (
    <button
      type="button"
      className={cn(
        'flex h-4 w-4 items-center justify-center rounded border border-gray-300 transition-colors',
        checked ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white hover:bg-gray-50',
        className
      )}
      onClick={() => onCheckedChange?.(!checked)}
    >
      {checked && <Check className="h-3 w-3" />}
    </button>
  );
}