import { useState } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { AlertTriangle, ChevronLeft, ChevronRight, X } from 'lucide-react';

interface WarningsBarProps {
  warnings: string[];
  onViewAll: () => void;
  onClear: () => void;
}

export function WarningsBar({ warnings, onViewAll, onClear }: WarningsBarProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev === 0 ? warnings.length - 1 : prev - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev === warnings.length - 1 ? 0 : prev + 1));
  };

  return (
    <div className="sticky top-0 z-20 bg-gradient-to-r from-amber-900/30 to-red-900/30 border-b border-amber-700/50 px-4 py-2.5 flex items-center justify-between gap-4 rounded-t-lg">
      {/* Left: Badge and Warning Message */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0" />
        <Badge className="bg-amber-600 hover:bg-amber-600 text-white border-0 flex-shrink-0">
          Warnings ({warnings.length})
        </Badge>
        
        {/* Warning Message with Navigation */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <button
            onClick={handlePrevious}
            className="flex-shrink-0 text-amber-300 hover:text-amber-100 transition-colors disabled:opacity-30"
            disabled={warnings.length <= 1}
            aria-label="Previous warning"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          
          <div className="flex-1 min-w-0 text-amber-100 text-sm truncate">
            {warnings[currentIndex]}
          </div>
          
          <button
            onClick={handleNext}
            className="flex-shrink-0 text-amber-300 hover:text-amber-100 transition-colors disabled:opacity-30"
            disabled={warnings.length <= 1}
            aria-label="Next warning"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          variant="outline"
          size="sm"
          onClick={onViewAll}
          className="bg-transparent border-amber-500 text-amber-300 hover:bg-amber-900/30 hover:text-amber-100 h-7 text-xs"
        >
          View All
        </Button>
        <button
          onClick={onClear}
          className="text-amber-300 hover:text-amber-100 transition-colors"
          aria-label="Clear warnings"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
