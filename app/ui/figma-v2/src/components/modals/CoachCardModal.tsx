import { useState } from 'react';
import { Dialog, DialogContent } from '../ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Button } from '../ui/button';
import { Star, X, HandshakeIcon, UserX } from 'lucide-react';
import { useGlobalModal } from '../../lib/GlobalModalContext';
import { ContractNegotiationModal } from './ContractNegotiationModal';
import { toast } from 'sonner@2.0.3';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';

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

export function CoachCardModal() {
  const { selectedCoach, isCoachModalOpen, closeCoachModal } = useGlobalModal();
  const [activeTab, setActiveTab] = useState('overview');
  const [isNegotiationOpen, setIsNegotiationOpen] = useState(false);
  const [isReleaseDialogOpen, setIsReleaseDialogOpen] = useState(false);

  if (!selectedCoach) return null;

  // Mock: Assume coach is on user's team if they have a currentTeam
  const isOnUserTeam = selectedCoach.currentTeam && selectedCoach.currentTeam !== 'Free Agent';

  const getRatingColor = (rating: number) => {
    if (rating >= 4.5) return 'text-[#d4af37]';
    if (rating >= 4.0) return 'text-green-400';
    if (rating >= 3.5) return 'text-blue-400';
    if (rating >= 3.0) return 'text-white';
    return 'text-[#94a3b8]';
  };

  const handleNegotiate = () => {
    setIsNegotiationOpen(true);
  };

  const handleRelease = () => {
    setIsReleaseDialogOpen(true);
  };

  const confirmRelease = () => {
    toast.success(`${selectedCoach.name} has been released from the team`);
    setIsReleaseDialogOpen(false);
    closeCoachModal();
  };

  return (
    <Dialog open={isCoachModalOpen} onOpenChange={closeCoachModal}>
      <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-2xl p-0 gap-0" aria-describedby={undefined}>
        {/* Header Section */}
        <div className="p-6 pb-3 border-b border-[#2d4a6f]">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h2 className="text-white text-xl mb-1">{selectedCoach.name}</h2>
              <div className="flex items-center gap-3 text-sm">
                <span className="text-[#d4af37]">{selectedCoach.title || selectedCoach.specialty}</span>
                {selectedCoach.currentTeam && (
                  <>
                    <span className="text-[#94a3b8]">{selectedCoach.currentTeam}</span>
                    {selectedCoach.currentRole && (
                      <span className="text-[#94a3b8]">{selectedCoach.currentRole}</span>
                    )}
                  </>
                )}
                <span className={getRatingColor(selectedCoach.overallRating)}>
                  <StarRating rating={selectedCoach.overallRating} />
                </span>
              </div>
            </div>
            <button
              onClick={closeCoachModal}
              className="text-[#94a3b8] hover:text-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full bg-[#0a1929] p-1 h-auto">
              <TabsTrigger value="overview" className="flex-1 data-[state=active]:bg-[#2d4a6f]">
                Overview
              </TabsTrigger>
              <TabsTrigger value="ratings" className="flex-1 data-[state=active]:bg-[#2d4a6f]">
                Ratings
              </TabsTrigger>
              <TabsTrigger value="contract" className="flex-1 data-[state=active]:bg-[#2d4a6f]">
                Contract
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Scrollable Content */}
        <div className="overflow-y-auto max-h-[60vh] p-6">
          <Tabs value={activeTab}>
            {/* Overview Tab */}
            <TabsContent value="overview" className="mt-0 space-y-4">
              {/* Key Stats */}
              <div className="grid grid-cols-4 gap-3">
                <div className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] text-center">
                  <div className="text-[#94a3b8] text-xs mb-1">Age</div>
                  <div className="text-xl text-white">{selectedCoach.age}</div>
                </div>
                <div className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] text-center">
                  <div className="text-[#94a3b8] text-xs mb-1">Exp</div>
                  <div className="text-xl text-white">{selectedCoach.experience}</div>
                </div>
                <div className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] text-center">
                  <div className="text-[#94a3b8] text-xs mb-1">Rep</div>
                  <div className="text-xl text-[#d4af37]">{selectedCoach.reputation}</div>
                </div>
                <div className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] text-center">
                  <div className="text-[#94a3b8] text-xs mb-1">Rating</div>
                  <div className={`text-xl ${getRatingColor(selectedCoach.overallRating)}`}>
                    {selectedCoach.overallRating.toFixed(1)}
                  </div>
                </div>
              </div>

              {/* Coaching Profile */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <h4 className="text-white mb-3 text-sm">Coaching Profile</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Background</span>
                    <span className="text-white">{selectedCoach.background}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Attitude</span>
                    <span className="text-white">{selectedCoach.attitude}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Style</span>
                    <span className="text-white">{selectedCoach.style}</span>
                  </div>
                  {selectedCoach.focusArea && (
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Focus</span>
                      <span className="text-white">{selectedCoach.focusArea}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Career Stats (Mock) */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <h4 className="text-white mb-3 text-sm">Career Highlights</h4>
                <div className="grid grid-cols-3 gap-3 text-center text-sm">
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 10) + 1}
                    </div>
                    <div className="text-[#94a3b8] text-xs">Championships</div>
                  </div>
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 50) + 30}
                    </div>
                    <div className="text-[#94a3b8] text-xs">Win %</div>
                  </div>
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 5) + 1}
                    </div>
                    <div className="text-[#94a3b8] text-xs">COY Awards</div>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* Ratings Tab */}
            <TabsContent value="ratings" className="mt-0 space-y-4">
              {/* Schemes */}
              {(selectedCoach.offense || selectedCoach.defense) && (
                <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                  <h4 className="text-white mb-3 text-sm">Schemes</h4>
                  <div className="space-y-3 text-sm">
                    {selectedCoach.offense && (
                      <div className="flex justify-between py-1">
                        <span className="text-[#94a3b8]">Offensive Scheme</span>
                        <span className="text-white">{selectedCoach.offense}</span>
                      </div>
                    )}
                    {selectedCoach.defense && (
                      <div className="flex justify-between py-1">
                        <span className="text-[#94a3b8]">Defensive Scheme</span>
                        <span className="text-white">{selectedCoach.defense}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Reputation Bar */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-white text-sm">Reputation</h4>
                  <span className="text-[#d4af37] text-sm">{selectedCoach.reputation}%</span>
                </div>
                <div className="w-full bg-[#1a2332] rounded-full h-3">
                  <div
                    className="bg-[#d4af37] h-3 rounded-full transition-all"
                    style={{ width: `${selectedCoach.reputation}%` }}
                  />
                </div>
              </div>

              {/* Attributes */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <h4 className="text-white mb-3 text-sm">Coaching Attributes</h4>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  <div className="flex justify-between py-1">
                    <span className="text-[#94a3b8]">Overall Rating</span>
                    <span className={getRatingColor(selectedCoach.overallRating)}>
                      {selectedCoach.overallRating.toFixed(1)} ⭐
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[#94a3b8]">Experience</span>
                    <span className="text-white">{selectedCoach.experience} yrs</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[#94a3b8]">Reputation</span>
                    <span className="text-white">{selectedCoach.reputation}%</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[#94a3b8]">Background</span>
                    <span className="text-white">{selectedCoach.background}</span>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* Contract Tab */}
            <TabsContent value="contract" className="mt-0 space-y-4">
              {selectedCoach.salary ? (
                <>
                  <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                    <h4 className="text-white mb-3 text-sm">Contract Details</h4>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between py-2 border-b border-[#2d4a6f]">
                        <span className="text-[#94a3b8]">Salary</span>
                        <span className="text-white">{selectedCoach.salary}/yr</span>
                      </div>
                      {selectedCoach.yearsRemaining !== undefined && (
                        <div className="flex justify-between py-2 border-b border-[#2d4a6f]">
                          <span className="text-[#94a3b8]">Years Remaining</span>
                          <span className="text-white">{selectedCoach.yearsRemaining} year(s)</span>
                        </div>
                      )}
                      {selectedCoach.focusArea && (
                        <div className="flex justify-between py-2">
                          <span className="text-[#94a3b8]">Focus Area</span>
                          <span className="text-white">{selectedCoach.focusArea}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-3">
                    <Button
                      onClick={handleNegotiate}
                      className="flex-1 bg-transparent border border-[#d4af37] text-[#d4af37] hover:bg-[#d4af37]/10"
                    >
                      <HandshakeIcon className="h-4 w-4 mr-2" />
                      Negotiate
                    </Button>
                    {isOnUserTeam && (
                      <Button
                        onClick={handleRelease}
                        variant="outline"
                        className="flex-1 bg-transparent border-red-500/50 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                      >
                        <UserX className="h-4 w-4 mr-2" />
                        Release
                      </Button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div className="bg-[#0a1929] p-8 rounded border border-[#2d4a6f] text-center">
                    <p className="text-[#94a3b8]">No contract information available</p>
                  </div>
                  
                  {/* Show negotiate button for free agents */}
                  <Button
                    onClick={handleNegotiate}
                    className="w-full bg-transparent border border-[#d4af37] text-[#d4af37] hover:bg-[#d4af37]/10"
                  >
                    <HandshakeIcon className="h-4 w-4 mr-2" />
                    Negotiate Contract
                  </Button>
                </>
              )}
            </TabsContent>
          </Tabs>
        </div>

        {/* Contract Negotiation Modal */}
        <ContractNegotiationModal
          isOpen={isNegotiationOpen}
          onClose={() => setIsNegotiationOpen(false)}
          playerName={selectedCoach.name}
          playerPosition={selectedCoach.title || selectedCoach.specialty || 'Coach'}
          playerOvr={Math.round(selectedCoach.overallRating * 20)} // Convert 5-star to 100-scale
          currentSalary={selectedCoach.salary}
          currentYears={selectedCoach.yearsRemaining}
        />

        {/* Release Confirmation Dialog */}
        <AlertDialog open={isReleaseDialogOpen} onOpenChange={setIsReleaseDialogOpen}>
          <AlertDialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
            <AlertDialogHeader>
              <AlertDialogTitle>Release {selectedCoach.name}?</AlertDialogTitle>
              <AlertDialogDescription className="text-[#94a3b8]">
                Are you sure you want to release this coach? This action cannot be undone.
                {selectedCoach.salary && (
                  <span className="block mt-2">
                    Remaining contract: {selectedCoach.salary}/yr for {selectedCoach.yearsRemaining || 0} year(s)
                  </span>
                )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="bg-transparent border-[#2d4a6f] text-[#94a3b8] hover:bg-[#2d4a6f]/30 hover:text-white">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={confirmRelease}
                className="bg-red-500 hover:bg-red-600 text-white"
              >
                Release Coach
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </DialogContent>
    </Dialog>
  );
}
