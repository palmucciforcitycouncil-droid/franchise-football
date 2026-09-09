import { useState } from 'react';
import { Dialog, DialogContent } from '../ui/dialog';
import { Button } from '../ui/button';
import { Slider } from '../ui/slider';
import { X, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface ContractNegotiationModalProps {
  isOpen: boolean;
  onClose: () => void;
  playerName: string;
  playerPosition: string;
  playerOvr: number;
  currentSalary?: string;
  currentYears?: number;
}

export function ContractNegotiationModal({
  isOpen,
  onClose,
  playerName,
  playerPosition,
  playerOvr,
  currentSalary,
  currentYears,
}: ContractNegotiationModalProps) {
  const [offerYears, setOfferYears] = useState(3);
  const [offerSalary, setOfferSalary] = useState(5.0);

  // Calculate market value based on OVR
  const marketValue = Math.round((playerOvr / 10) * 2) / 2;
  const totalValue = offerYears * offerSalary;

  // Calculate player happiness based on offer vs market
  const getPlayerReaction = () => {
    const difference = offerSalary - marketValue;
    const percentDiff = (difference / marketValue) * 100;

    if (percentDiff > 20) return { text: 'Very Interested', color: 'text-green-400', icon: TrendingUp };
    if (percentDiff > 5) return { text: 'Interested', color: 'text-blue-400', icon: TrendingUp };
    if (percentDiff > -5) return { text: 'Neutral', color: 'text-[#94a3b8]', icon: DollarSign };
    if (percentDiff > -20) return { text: 'Hesitant', color: 'text-yellow-400', icon: TrendingDown };
    return { text: 'Not Interested', color: 'text-red-400', icon: TrendingDown };
  };

  const reaction = getPlayerReaction();
  const ReactionIcon = reaction.icon;

  const handleMakeOffer = () => {
    toast.success(`Contract offer sent to ${playerName}: ${offerYears} years, $${offerSalary.toFixed(1)}M/yr`);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-lg p-0 gap-0" aria-describedby={undefined}>
        {/* Header */}
        <div className="p-6 pb-4 border-b border-[#2d4a6f]">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-white mb-1">Contract Negotiation</h2>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-[#d4af37]">{playerName}</span>
                <span className="text-[#94a3b8]">·</span>
                <span className="text-[#94a3b8]">{playerPosition}</span>
                <span className="text-[#94a3b8]">·</span>
                <span className="text-[#94a3b8]">OVR {playerOvr}</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-[#94a3b8] hover:text-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Current Contract Info */}
          {currentSalary && (
            <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
              <h4 className="text-white text-sm mb-3">Current Contract</h4>
              <div className="flex items-center justify-between text-sm">
                <span className="text-[#94a3b8]">Salary</span>
                <span className="text-white">{currentSalary}</span>
              </div>
              {currentYears !== undefined && (
                <div className="flex items-center justify-between text-sm mt-2">
                  <span className="text-[#94a3b8]">Years Remaining</span>
                  <span className="text-white">{currentYears}</span>
                </div>
              )}
            </div>
          )}

          {/* Market Value */}
          <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
            <div className="flex items-center justify-between">
              <span className="text-[#94a3b8] text-sm">Market Value</span>
              <span className="text-[#d4af37]">${marketValue.toFixed(1)}M/yr</span>
            </div>
          </div>

          {/* Contract Offer */}
          <div className="space-y-4">
            <h4 className="text-white text-sm">Your Offer</h4>
            
            {/* Years Slider */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-[#94a3b8] text-sm">Contract Length</label>
                <span className="text-white">{offerYears} years</span>
              </div>
              <Slider
                value={[offerYears]}
                onValueChange={(value) => setOfferYears(value[0])}
                min={1}
                max={6}
                step={1}
                className="w-full"
              />
            </div>

            {/* Salary Slider */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-[#94a3b8] text-sm">Annual Salary</label>
                <span className="text-white">${offerSalary.toFixed(1)}M</span>
              </div>
              <Slider
                value={[offerSalary]}
                onValueChange={(value) => setOfferSalary(value[0])}
                min={0.5}
                max={25}
                step={0.5}
                className="w-full"
              />
            </div>
          </div>

          {/* Total Value */}
          <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[#94a3b8] text-sm">Total Contract Value</span>
              <span className="text-[#d4af37]">${totalValue.toFixed(1)}M</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[#94a3b8] text-sm">Player Reaction</span>
              <div className={`flex items-center gap-1.5 ${reaction.color}`}>
                <ReactionIcon className="h-4 w-4" />
                <span className="text-sm">{reaction.text}</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={onClose}
              className="flex-1 bg-transparent border-[#2d4a6f] text-[#94a3b8] hover:bg-[#2d4a6f]/30 hover:text-white"
            >
              Cancel
            </Button>
            <Button
              onClick={handleMakeOffer}
              className="flex-1 bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              Make Offer
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
